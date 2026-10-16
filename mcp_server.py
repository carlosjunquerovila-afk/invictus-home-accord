#!/usr/bin/env python3
"""Local Home Accord MCP 2025-11-25 Streamable HTTP tools.

The transport is real; resident consent, schedules and receipts remain simulated.
No Alexa, model, cloud, payment or appliance calls. Python standard library only.
"""
import argparse
from collections import deque
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import threading
import time

from app import Accord, AccordError, APPLIANCES, RESIDENTS

PROTOCOL = '2025-11-25'
MAX_BODY = 65_536
MAX_SESSIONS = 32
SESSION_SECONDS = 3600
MAX_REQUESTS = 4096
MAX_CALLS_PER_MINUTE = 120
MAX_PLANS = 64


def object_schema(properties, required=None):
    return {'type': 'object', 'properties': properties,
            'required': list(properties) if required is None else required,
            'additionalProperties': False}


ID_SCHEMA = {'type': 'string', 'minLength': 1, 'maxLength': 64}
TASK_SCHEMA = object_schema({
    'owner': {'type': 'string', 'enum': RESIDENTS},
    'appliance': {'type': 'string', 'enum': list(APPLIANCES)},
    'duration': {'type': 'integer', 'minimum': 15, 'maximum': 180, 'multipleOf': 15},
    'earliest': {'type': 'integer', 'minimum': 0, 'maximum': 180, 'multipleOf': 15},
    'latest': {'type': 'integer', 'minimum': 15, 'maximum': 180, 'multipleOf': 15},
})
TOOLS = [
    {'name': 'accord_state', 'title': 'Read simulated household',
     'description': 'Read the local demo agenda, proposals and simulated receipts. No appliance telemetry.',
     'inputSchema': object_schema({}),
     'annotations': {'readOnlyHint': True, 'destructiveHint': False, 'idempotentHint': True, 'openWorldHint': False}},
    {'name': 'accord_propose', 'title': 'Propose household agenda',
     'description': 'Persist a proposal using the existing greedy planner. Does not commit an agenda or operate devices. A placement failure is not proof of infeasibility.',
     'inputSchema': object_schema({'requests': {'type': 'array', 'minItems': 1, 'maxItems': 8, 'items': TASK_SCHEMA}}),
     'annotations': {'readOnlyHint': False, 'destructiveHint': False, 'idempotentHint': False, 'openWorldHint': False}},
    {'name': 'accord_consent', 'title': 'Record simulated consent',
     'description': 'DEMO ONLY: select Alice or Bob to grant or withdraw simulated consent for an exact proposal. This does not authenticate a person. Requires explicit demo consent enabled at server startup.',
     'inputSchema': object_schema({'plan_id': ID_SCHEMA, 'resident': {'type': 'string', 'enum': RESIDENTS},
                                  'approved': {'type': 'boolean'}, 'simulation_acknowledged': {'type': 'boolean', 'const': True}}),
     'annotations': {'readOnlyHint': False, 'destructiveHint': True, 'idempotentHint': True, 'openWorldHint': False}},
    {'name': 'accord_transition', 'title': 'Commit or undo simulated agenda',
     'description': 'Commit an exact proposal after both simulated approvals, or undo only the latest unchanged commit receipt. No physical execution. Requires explicit demo consent mode and confirmed=true.',
     'inputSchema': object_schema({'action': {'type': 'string', 'enum': ['commit', 'undo']},
                                  'id': ID_SCHEMA, 'confirmed': {'type': 'boolean', 'const': True}}),
     'annotations': {'readOnlyHint': False, 'destructiveHint': True, 'idempotentHint': False, 'openWorldHint': False}},
]
TOOL_MAP = {t['name']: t for t in TOOLS}


def validate(value, schema, path='arguments'):
    """Validate the small, explicitly supported schema vocabulary used above."""
    kind = schema['type']
    expected = {'object': dict, 'array': list, 'string': str, 'integer': int, 'boolean': bool}[kind]
    if type(value) is not expected:
        raise AccordError(f'{path}: expected {kind}')
    if 'enum' in schema and value not in schema['enum']:
        raise AccordError(f'{path}: unsupported value')
    if 'const' in schema and value != schema['const']:
        raise AccordError(f'{path}: explicit acknowledgement required')
    if kind == 'object':
        if set(value) != set(schema['required']):
            raise AccordError(f'{path}: missing or unexpected fields')
        for key, item in value.items():
            validate(item, schema['properties'][key], f'{path}.{key}')
    if kind == 'array':
        if not schema['minItems'] <= len(value) <= schema['maxItems']:
            raise AccordError(f'{path}: invalid number of items')
        for index, item in enumerate(value):
            validate(item, schema['items'], f'{path}[{index}]')
    if kind == 'string' and ('minLength' in schema or 'maxLength' in schema):
        if not schema.get('minLength', 0) <= len(value) <= schema.get('maxLength', 4096):
            raise AccordError(f'{path}: invalid string length')
    if kind == 'integer':
        if not schema['minimum'] <= value <= schema['maximum'] or value % schema['multipleOf']:
            raise AccordError(f'{path}: invalid time slot')


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field')
        result[key] = value
    return result


def strict_json(raw):
    def reject_constant(value):
        raise ValueError('Nonfinite JSON value')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=no_duplicates, parse_constant=reject_constant)


def rpc_error(code, message, request_id=None):
    return {'jsonrpc': '2.0', 'id': request_id, 'error': {'code': code, 'message': message}}


def result(data, is_error=False):
    return {'content': [{'type': 'text', 'text': json.dumps(data, sort_keys=True)}],
            'structuredContent': data, 'isError': is_error}


class Session:
    def __init__(self, first_id):
        self.ready = False
        self.ids = {first_id}
        self.calls = deque()
        self.created = time.monotonic()
        self.lock = threading.RLock()


class MCPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, state_path, token, port=0, demo_consent=False):
        if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{32,256}', token):
            raise ValueError('Use a local token with 32-256 URL-safe characters')
        super().__init__(('127.0.0.1', port), MCPHandler)
        self.accord = Accord(state_path)
        self.token = token
        self.demo_consent = demo_consent
        self.sessions = {}
        self.sessions_lock = threading.RLock()
        self.hosts = {f'127.0.0.1:{self.server_port}', f'localhost:{self.server_port}'}

    def tool(self, name, args):
        try:
            validate(args, TOOL_MAP[name]['inputSchema'])
            # Bound durable demo growth. The precheck and mutation share the engine lock.
            with self.accord.lock:
                if name == 'accord_state':
                    data = self.accord.snapshot()
                elif name == 'accord_propose':
                    if len(self.accord.state['plans']) >= MAX_PLANS:
                        raise AccordError('Demo plan limit reached. Archive this workspace and start a new state file.')
                    data = self.accord.propose(args['requests'])
                else:
                    if not self.demo_consent:
                        raise AccordError('Simulated consent disabled. A local operator must restart with --demo-consent.')
                    if name == 'accord_consent':
                        data = self.accord.approve(args['plan_id'], args['resident'], args['approved'])
                    elif args['action'] == 'commit':
                        data = self.accord.execute(args['id'])
                    else:
                        data = self.accord.undo(args['id'])
            return result({'simulation': True, 'data': data})
        except AccordError as exc:
            return result({'simulation': True, 'error': str(exc)}, True)
        except OSError:
            return result({'simulation': True, 'error': 'Local persistence failed; operation rolled back.'}, True)


class MCPHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *args):
        pass  # Never log bearer credentials or request contents.

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def send(self, status, body=None, headers=None):
        raw = b'' if body is None else json.dumps(body, ensure_ascii=True, separators=(',', ':')).encode()
        self.send_response(status)
        for key, value in {'Content-Type': 'application/json', 'Content-Length': str(len(raw)),
                           'Cache-Control': 'no-store', 'Connection': 'close',
                           'X-Content-Type-Options': 'nosniff', **(headers or {})}.items():
            self.send_header(key, value)
        self.end_headers()
        if raw:
            self.wfile.write(raw)
        self.close_connection = True

    def preflight(self):
        if self.path != '/mcp':
            self.send(404, {'error': 'NOT_FOUND'}); return False
        hosts = self.headers.get_all('Host') or []
        origins = self.headers.get_all('Origin') or []
        if len(hosts) != 1 or hosts[0] not in self.server.hosts:
            self.send(403, {'error': 'HOST_REFUSED'}); return False
        if origins and (len(origins) != 1 or origins[0] != f'http://{hosts[0]}'):
            self.send(403, {'error': 'ORIGIN_REFUSED'}); return False
        auth = self.headers.get_all('Authorization') or []
        if len(auth) != 1 or not hmac.compare_digest(auth[0].encode('utf-8'), ('Bearer ' + self.server.token).encode('ascii')):
            self.send(401, {'error': 'AUTH_REQUIRED'}, {'WWW-Authenticate': 'Bearer'}); return False
        return True

    def session(self):
        values = self.headers.get_all('Mcp-Session-Id') or []
        if len(values) != 1:
            self.send(400, {'error': 'SESSION_REQUIRED'}); return None
        versions = self.headers.get_all('MCP-Protocol-Version') or []
        if versions != [PROTOCOL]:
            self.send(400, {'error': 'UNSUPPORTED_PROTOCOL_VERSION'}); return None
        with self.server.sessions_lock:
            session = self.server.sessions.get(values[0])
            if session is None or time.monotonic() - session.created > SESSION_SECONDS:
                self.server.sessions.pop(values[0], None)
                self.send(404, {'error': 'SESSION_EXPIRED'}); return None
            return session

    def do_GET(self):
        if self.preflight():
            self.send(405, {'error': 'SSE_STREAM_NOT_PROVIDED'}, {'Allow': 'POST, DELETE'})

    def do_DELETE(self):
        if not self.preflight() or self.session() is None:
            return
        with self.server.sessions_lock:
            self.server.sessions.pop(self.headers['Mcp-Session-Id'], None)
        self.send(204)

    def do_POST(self):
        if not self.preflight():
            return
        accepted = {value.strip().split(';')[0] for value in self.headers.get('Accept', '').split(',')}
        if not {'application/json', 'text/event-stream'} <= accepted:
            self.send(406, {'error': 'ACCEPT_JSON_AND_EVENT_STREAM_REQUIRED'}); return
        if len(self.headers.get_all('Content-Type') or []) != 1 or self.headers.get_content_type() != 'application/json':
            self.send(415, {'error': 'JSON_REQUIRED'}); return
        lengths = self.headers.get_all('Content-Length') or []
        if self.headers.get('Transfer-Encoding') or len(lengths) != 1 or not re.fullmatch(r'[0-9]{1,6}', lengths[0]):
            self.send(400, {'error': 'CONTENT_LENGTH_REQUIRED'}); return
        size = int(lengths[0])
        if not 0 < size <= MAX_BODY:
            self.send(413, {'error': 'BODY_LIMIT'}); return
        try:
            raw = self.rfile.read(size)
            if len(raw) != size:
                raise ValueError('Truncated request')
            message = strict_json(raw)
        except (ValueError, UnicodeError, TimeoutError, RecursionError):
            self.send(400, rpc_error(-32700, 'Parse error')); return
        if type(message) is not dict or message.get('jsonrpc') != '2.0' or not isinstance(message.get('method'), str):
            self.send(400, rpc_error(-32600, 'Invalid request; JSON-RPC batches are unsupported')); return
        has_id = 'id' in message
        request_id = message.get('id')
        if has_id and (type(request_id) not in (str, int) or (isinstance(request_id, str) and len(request_id) > 128)):
            self.send(400, rpc_error(-32600, 'Request ID must be a bounded string or integer')); return
        params = message.get('params', {})
        if type(params) is not dict:
            if has_id:
                self.send(200, rpc_error(-32602, 'Parameters must be an object', request_id))
            else:
                self.send(202)
            return
        method = message['method']
        if method == 'initialize' and has_id:
            if self.headers.get('Mcp-Session-Id'):
                self.send(400, rpc_error(-32600, 'Initialize requires a new session', request_id)); return
            info = params.get('clientInfo')
            if (not isinstance(params.get('protocolVersion'), str) or type(params.get('capabilities')) is not dict
                or type(info) is not dict or not isinstance(info.get('name'), str) or not isinstance(info.get('version'), str)):
                self.send(200, rpc_error(-32602, 'Invalid initialize parameters', request_id)); return
            with self.server.sessions_lock:
                now = time.monotonic()
                self.server.sessions = {key: val for key, val in self.server.sessions.items() if now - val.created <= SESSION_SECONDS}
                if len(self.server.sessions) >= MAX_SESSIONS:
                    self.send(429, rpc_error(-32000, 'Session limit reached', request_id)); return
                session_id = secrets.token_urlsafe(32)
                self.server.sessions[session_id] = Session(request_id)
            self.send(200, {'jsonrpc': '2.0', 'id': request_id, 'result': {
                'protocolVersion': PROTOCOL, 'capabilities': {'tools': {'listChanged': False}},
                'serverInfo': {'name': 'invictus-home-accord', 'version': '0.2.0'},
                'instructions': 'Local household simulation only. Resident labels are not identities; no Alexa or appliance control. Never infer physical execution from a receipt.'
            }}, {'Mcp-Session-Id': session_id}); return
        session = self.session()
        if session is None:
            return
        with session.lock:
            if not has_id:
                if method == 'notifications/initialized':
                    session.ready = True
                # Notifications, including unknown ones, never receive JSON-RPC replies.
                self.send(202); return
            if request_id in session.ids:
                self.send(200, rpc_error(-32600, 'Request ID already used; no operation performed', request_id)); return
            if len(session.ids) >= MAX_REQUESTS:
                self.send(429, rpc_error(-32000, 'Session request limit; reconnect', request_id)); return
            session.ids.add(request_id)
            if method == 'ping':
                response = {}
            elif not session.ready:
                self.send(200, rpc_error(-32002, 'Send notifications/initialized before tool use', request_id)); return
            elif method == 'tools/list':
                if set(params) - {'_meta'}:
                    self.send(200, rpc_error(-32602, 'No cursor: this server returns the complete tool list', request_id)); return
                response = {'tools': TOOLS}
            elif method == 'tools/call':
                if (set(params) - {'name', 'arguments', '_meta'} or not isinstance(params.get('name'), str)
                    or params.get('name') not in TOOL_MAP
                    or type(params.get('arguments', {})) is not dict):
                    self.send(200, rpc_error(-32602, 'Unknown tool or malformed tools/call parameters', request_id)); return
                now = time.monotonic()
                while session.calls and session.calls[0] < now - 60:
                    session.calls.popleft()
                if len(session.calls) >= MAX_CALLS_PER_MINUTE:
                    response = result({'simulation': True, 'error': 'Tool rate limit; retry after one minute.'}, True)
                else:
                    session.calls.append(now)
                    response = self.server.tool(params['name'], params.get('arguments', {}))
            else:
                self.send(200, rpc_error(-32601, 'Method not found', request_id)); return
            self.send(200, {'jsonrpc': '2.0', 'id': request_id, 'result': response})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--state', type=Path, default=Path(__file__).with_name('mcp-state.json'))
    parser.add_argument('--demo-consent', action='store_true', help='Explicitly allow simulated resident approvals and reversible agenda changes')
    args = parser.parse_args()
    token = os.environ.get('HOME_ACCORD_MCP_TOKEN', '')
    try:
        server = MCPServer(args.state, token, args.port, args.demo_consent)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(f'Home Accord MCP listening on http://127.0.0.1:{server.server_port}/mcp', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
