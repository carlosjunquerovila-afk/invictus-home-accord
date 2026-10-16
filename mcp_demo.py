#!/usr/bin/env python3
"""Run the MCP server as a child process and demonstrate four tools over real HTTP.
Synthetic household data, no LLM, Alexa or appliances. No credential is printed.
"""
import argparse
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
from types import SimpleNamespace

from test_mcp import Client, TASK


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Optional local JSON transcript path')
    args = parser.parse_args()
    events = []
    with tempfile.TemporaryDirectory(prefix='home-accord-mcp-demo-') as directory:
        token = secrets.token_urlsafe(32)
        command = [sys.executable, str(Path(__file__).with_name('mcp_server.py')), '--port', '0',
                   '--state', str(Path(directory) / 'state.json'), '--demo-consent']
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env={**os.environ, 'HOME_ACCORD_MCP_TOKEN': token})
        try:
            ready = Queue()
            threading.Thread(target=lambda: ready.put(process.stdout.readline()), daemon=True).start()
            try:
                line = ready.get(timeout=5)
            except Empty:
                raise RuntimeError('Local MCP server did not start within five seconds') from None
            match = re.fullmatch(r'Home Accord MCP listening on http://127\.0\.0\.1:([0-9]+)/mcp\n', line)
            if not match:
                raise RuntimeError('Unexpected local MCP startup response')
            client = Client(SimpleNamespace(server_port=int(match[1]), token=token))
            events.append({'step': 'initialize', 'result': client.initialize()})
            events.append({'step': 'tools/list', 'result': client.request('tools/list')[2]['result']})

            def call(name, arguments, expected_error=False):
                result = client.call(name, arguments)
                events.append({'step': name, 'arguments': arguments, 'result': result})
                if result['isError'] is not expected_error:
                    raise RuntimeError(f'Unexpected result from {name}')
                return result['structuredContent'].get('data')

            before = call('accord_state', {})
            plan = call('accord_propose', {'requests': [TASK]})
            call('accord_transition', {'action': 'commit', 'id': plan['id'], 'confirmed': True}, True)
            for resident in ('Alice', 'Bob'):
                call('accord_consent', {'plan_id': plan['id'], 'resident': resident,
                    'approved': True, 'simulation_acknowledged': True})
            receipt = call('accord_transition', {'action': 'commit', 'id': plan['id'], 'confirmed': True})
            committed = call('accord_state', {})
            if len(committed['tasks']) != len(before['tasks']) + 1:
                raise RuntimeError('Committed agenda not observed')
            call('accord_transition', {'action': 'undo', 'id': receipt['id'], 'confirmed': True})
            restored = call('accord_state', {})
            if restored['tasks'] != before['tasks']:
                raise RuntimeError('Undo did not restore original agenda')
            client.exchange(method='DELETE')
        finally:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=3)
            process.stdout.close(); process.stderr.close()
    report = {'transport': 'real loopback Streamable HTTP to a child process',
              'protocol': '2025-11-25', 'simulation': True, 'external_agent_exercised': False,
              'alexa_or_device_execution': False, 'result': 'PASS', 'events': events}
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key != 'events'}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
