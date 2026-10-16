#!/usr/bin/env python3
"""Interactive JSON-lines MCP transport. It does not call or simulate a model.

A live external agent/operator chooses each command after observing the preceding
response. --commands replays a previously chosen command log, not new inference.
Only Python's standard library is used; no credentials are saved or printed.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
from queue import Queue, Empty
import re
import secrets
import subprocess
import sys
import tempfile
import threading

PROTOCOL = '2025-11-25'


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--commands', type=Path)
    parser.add_argument('--operator-label', default='local operator; identity not verified')
    args = parser.parse_args()
    source = args.source.resolve()
    report = {
        'started_at': now(), 'protocol': PROTOCOL,
        'interaction_mode': 'recorded-command replay' if args.commands else 'interactive decisions after observed responses',
        'operator_label': args.operator_label,
        'transport': 'Python standard-library HTTP client to separate loopback MCP server process',
        'synthetic_household': True, 'simulated_consent_explicitly_enabled': True,
        'resident_identity_authenticated': False, 'alexa_integrated': False,
        'physical_devices_controlled': False, 'native_mcp_host_or_connector': False,
        'independent_protocol_certification': False,
        'source_sha256': {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
                          for name in ('app.py', 'mcp_server.py')},
        'events': []
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def emit(value):
        print(json.dumps(value, ensure_ascii=False), flush=True)

    with tempfile.TemporaryDirectory(prefix='home-accord-agent-') as temp:
        token = secrets.token_urlsafe(32)
        process = subprocess.Popen(
            [sys.executable, str(source / 'mcp_server.py'), '--port', '0',
             '--state', str(Path(temp) / 'state.json'), '--demo-consent'],
            env={**os.environ, 'HOME_ACCORD_MCP_TOKEN': token},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        session = None
        request_id = 0
        replay_values = {}
        try:
            queue = Queue()
            threading.Thread(target=lambda: queue.put(process.stdout.readline()), daemon=True).start()
            try:
                startup = queue.get(timeout=5)
            except Empty:
                raise RuntimeError('Server startup timed out') from None
            match = re.fullmatch(r'Home Accord MCP listening on http://127\.0\.0\.1:([0-9]+)/mcp\n', startup)
            if not match:
                raise RuntimeError('Unexpected server startup response')
            port = int(match[1])

            def exchange(body=None, method='POST'):
                headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json',
                           'Accept': 'application/json, text/event-stream'}
                if session:
                    headers.update({'Mcp-Session-Id': session, 'MCP-Protocol-Version': PROTOCOL})
                with closing(http.client.HTTPConnection('127.0.0.1', port, timeout=5)) as connection:
                    connection.request(method, '/mcp', body=json.dumps(body).encode() if body else None, headers=headers)
                    response = connection.getresponse()
                    raw = response.read()
                    return response.status, dict(response.getheaders()), json.loads(raw) if raw else None

            def request(method, params):
                nonlocal request_id
                request_id += 1
                body = {'jsonrpc': '2.0', 'id': request_id, 'method': method, 'params': params}
                status, headers, response = exchange(body)
                return body, status, headers, response

            body, status, headers, response = request('initialize', {
                'protocolVersion': PROTOCOL, 'capabilities': {},
                'clientInfo': {'name': 'home-accord-interactive-agent-transport', 'version': '1.0'}
            })
            if status != 200 or 'result' not in response:
                raise RuntimeError('Initialization failed')
            session = headers['Mcp-Session-Id']
            ready, _, _ = exchange({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
            if ready != 202:
                raise RuntimeError('Initialized notification failed')
            report['events'].append({'at': now(), 'step': 'initialize', 'http_status': status,
                                     'request': body, 'response': response, 'initialized_notification_status': ready})
            save()
            emit({'ready': True, 'initialization': response['result'], 'instructions': 'Send one JSON line: {method,params,decision}; {finish:true,summary:...} to end. No automatic scenario is executed.'})

            stream = args.commands.open(encoding='utf-8') if args.commands else sys.stdin
            try:
                for raw in stream:
                    if not raw.strip():
                        continue
                    command = json.loads(raw)
                    if command.get('finish'):
                        report['operator_conclusion'] = command.get('summary', '')
                        break
                    if set(command) != {'method', 'params', 'decision'}:
                        raise ValueError('Command needs exactly method, params and decision')
                    def resolve(value):
                        if isinstance(value, dict):
                            return {key: resolve(item) for key, item in value.items()}
                        if isinstance(value, list):
                            return [resolve(item) for item in value]
                        if isinstance(value, str) and value in ('$plan_id', '$receipt_id'):
                            if value not in replay_values:
                                raise ValueError('Replay reference not available yet')
                            return replay_values[value]
                        return value
                    command['params'] = resolve(command['params'])
                    body, status, _, response = request(command['method'], command['params'])
                    event = {'at': now(), 'decision_before_call': command['decision'],
                             'request': body, 'http_status': status, 'response': response}
                    report['events'].append(event)
                    if command['method'] == 'tools/call' and response and 'result' in response:
                        outcome = response['result']
                        data = outcome.get('structuredContent', {}).get('data', {})
                        if not outcome.get('isError'):
                            if command['params']['name'] == 'accord_propose':
                                replay_values['$plan_id'] = data['id']
                            elif command['params']['name'] == 'accord_transition' and command['params']['arguments']['action'] == 'commit':
                                replay_values['$receipt_id'] = data['id']
                    save()
                    emit(event)
            finally:
                if args.commands:
                    stream.close()
            closed, _, _ = exchange(method='DELETE')
            report.update({'ended_at': now(), 'session_delete_status': closed, 'completed': True})
            save()
            emit({'completed': True, 'transcript': str(args.output), 'tool_and_protocol_exchanges': len(report['events'])})
        finally:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
            process.stdout.close()
            process.stderr.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
