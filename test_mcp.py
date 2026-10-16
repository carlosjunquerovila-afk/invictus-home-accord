"""Real loopback HTTP checks for the optional MCP bridge; no external AI/device calls."""
from contextlib import closing
import http.client
import json
from pathlib import Path
import secrets
import tempfile
import threading
import unittest
from unittest.mock import patch

from mcp_server import MCPServer, PROTOCOL


class Client:
    def __init__(self, server):
        self.server = server
        self.session = None
        self.counter = 0

    def exchange(self, body=None, method='POST', headers=None, raw=None):
        base = {'Authorization': 'Bearer ' + self.server.token,
                'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'}
        if self.session:
            base.update({'Mcp-Session-Id': self.session, 'MCP-Protocol-Version': PROTOCOL})
        for key, value in (headers or {}).items():
            if value is None:
                base.pop(key, None)
            else:
                base[key] = value
        payload = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        with closing(http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)) as connection:
            connection.request(method, '/mcp', body=payload, headers=base)
            response = connection.getresponse()
            data = response.read()
            return response.status, dict(response.getheaders()), json.loads(data) if data else None

    def request(self, method, params=None, request_id=None):
        self.counter += 1
        return self.exchange({'jsonrpc': '2.0', 'id': self.counter if request_id is None else request_id,
                              'method': method, 'params': {} if params is None else params})

    def initialize(self, offered=PROTOCOL, ready=True):
        status, headers, data = self.request('initialize', {'protocolVersion': offered,
            'capabilities': {}, 'clientInfo': {'name': 'local-wire-check', 'version': '1.0'}})
        assert status == 200 and 'result' in data, data
        self.session = headers['Mcp-Session-Id']
        if ready:
            assert self.exchange({'jsonrpc': '2.0', 'method': 'notifications/initialized'})[0] == 202
        return data['result']

    def call(self, name, arguments):
        status, _, data = self.request('tools/call', {'name': name, 'arguments': arguments})
        assert status == 200, (status, data)
        return data['result']


TASK = {'owner': 'Alice', 'appliance': 'Dishwasher', 'duration': 15, 'earliest': 0, 'latest': 180}


class MCPWireTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.server = MCPServer(Path(self.temp.name) / 'state.json', secrets.token_urlsafe(32), demo_consent=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.client = Client(self.server)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)

    def data(self, result):
        self.assertFalse(result['isError'], result)
        value = result['structuredContent']
        self.assertEqual(json.loads(result['content'][0]['text']), value)
        self.assertTrue(value['simulation'])
        return value['data']

    def proposal(self):
        return self.data(self.client.call('accord_propose', {'requests': [TASK]}))['id']

    def consent(self, plan_id, resident, approved=True):
        return self.client.call('accord_consent', {'plan_id': plan_id, 'resident': resident,
            'approved': approved, 'simulation_acknowledged': True})

    def transition(self, action, identifier):
        return self.client.call('accord_transition', {'action': action, 'id': identifier, 'confirmed': True})

    def test_real_http_handshake_four_tools_commit_and_undo(self):
        init = self.client.initialize()
        self.assertEqual(init['protocolVersion'], PROTOCOL)
        self.assertEqual(init['capabilities'], {'tools': {'listChanged': False}})
        status, _, tools = self.client.request('tools/list')
        self.assertEqual(status, 200)
        names = {item['name'] for item in tools['result']['tools']}
        self.assertEqual(names, {'accord_state', 'accord_propose', 'accord_consent', 'accord_transition'})
        before = self.data(self.client.call('accord_state', {}))
        plan_id = self.proposal()
        self.assertTrue(self.transition('commit', plan_id)['isError'])
        for resident in ('Alice', 'Bob'):
            self.data(self.consent(plan_id, resident))
        receipt = self.data(self.transition('commit', plan_id))
        self.assertEqual(receipt['kind'], 'commit')
        after = self.data(self.client.call('accord_state', {}))
        self.assertEqual(len(after['tasks']), 1)
        self.data(self.transition('undo', receipt['id']))
        self.assertEqual(self.data(self.client.call('accord_state', {}))['tasks'], before['tasks'])

    def test_consent_withdrawal_and_stale_plan_are_refused(self):
        self.client.initialize()
        first, second = self.proposal(), self.proposal()
        for plan in (first, second):
            for resident in ('Alice', 'Bob'):
                self.data(self.consent(plan, resident))
        self.data(self.consent(first, 'Bob', False))
        self.assertTrue(self.transition('commit', first)['isError'])
        self.data(self.transition('commit', second))
        self.assertTrue(self.consent(first, 'Bob')['isError'])
        self.assertTrue(self.transition('commit', first)['isError'])
        self.assertEqual(len(self.server.accord.snapshot()['tasks']), 1)

    def test_demo_consent_must_be_enabled_by_operator(self):
        self.server.demo_consent = False
        self.client.initialize()
        plan = self.proposal()
        self.assertTrue(self.consent(plan, 'Alice')['isError'])
        self.assertTrue(self.transition('commit', plan)['isError'])
        self.assertEqual(self.server.accord.snapshot()['plans'][plan]['approvals'], [])

    def test_lifecycle_negotiation_version_and_termination(self):
        init = self.client.initialize(offered='1900-01-01', ready=False)
        self.assertEqual(init['protocolVersion'], PROTOCOL)
        self.assertEqual(self.client.request('tools/list')[2]['error']['code'], -32002)
        self.assertEqual(self.client.request('ping')[2]['result'], {})
        self.assertEqual(self.client.exchange({'jsonrpc': '2.0', 'method': 'notifications/initialized'})[0], 202)
        self.assertEqual(self.client.exchange({'jsonrpc': '2.0', 'id': 8, 'method': 'tools/list'},
            headers={'MCP-Protocol-Version': '2024-11-05'})[0], 400)
        self.assertEqual(self.client.exchange(method='GET')[0], 405)
        self.assertEqual(self.client.exchange(method='DELETE')[0], 204)
        self.assertEqual(self.client.request('tools/list')[0], 404)

    def test_auth_origin_host_and_media_type_fail_before_mutation(self):
        self.client.initialize()
        body = {'jsonrpc': '2.0', 'id': 10, 'method': 'tools/call',
                'params': {'name': 'accord_propose', 'arguments': {'requests': [TASK]}}}
        for headers, expected in [({'Authorization': None}, 401),
                ({'Authorization': 'Bearer invalid'}, 401), ({'Authorization': 'Bearer éééé'}, 401),
                ({'Origin': 'https://attacker.invalid'}, 403),
                ({'Host': 'attacker.invalid'}, 403), ({'Content-Type': 'text/plain'}, 415),
                ({'Accept': 'application/json'}, 406)]:
            with self.subTest(headers=headers):
                self.assertEqual(self.client.exchange(body, headers=headers)[0], expected)
        self.assertEqual(self.server.accord.snapshot()['plans'], {})

    def test_malformed_wire_and_unhashable_tool_names_do_not_crash(self):
        self.client.initialize()
        for raw in [b'not json', b'[]', b'{"jsonrpc":"2.0","jsonrpc":"2.0"}',
                    b'{"jsonrpc":"2.0","method":"tools/list","id":true}',
                    b'{"jsonrpc":"2.0","method":"tools/list","id":null}',
                    b'{"jsonrpc":"2.0","method":"tools/list","id":NaN}']:
            status, _, response = self.client.exchange(raw=raw)
            self.assertEqual(status, 400)
            self.assertIsNone(response['id'])
        for name in ([], {}, None, 'does_not_exist'):
            response = self.client.request('tools/call', {'name': name, 'arguments': {}})
            self.assertEqual(response[2]['error']['code'], -32602)
        self.assertIn('tools', self.client.request('tools/list')[2]['result'])

    def test_input_validation_keeps_state_unchanged(self):
        self.client.initialize()
        before = self.server.accord.snapshot()
        bad = [None, [], {}, {'requests': []}, {'requests': [dict(TASK, duration=True)]},
               {'requests': [dict(TASK, duration=16)]}, {'requests': [dict(TASK, extra='x')]},
               {'requests': [dict(TASK, owner='Mallory')]}, {'requests': [TASK], 'extra': 'x'}]
        for arguments in bad:
            response = self.client.request('tools/call', {'name': 'accord_propose', 'arguments': arguments})[2]
            self.assertTrue('error' in response or response['result']['isError'])
        self.assertEqual(self.server.accord.snapshot(), before)

    def test_duplicate_request_and_closed_proposal_cannot_double_commit(self):
        self.client.initialize()
        plan = self.proposal()
        for resident in ('Alice', 'Bob'):
            self.data(self.consent(plan, resident))
        params = {'name': 'accord_transition', 'arguments': {'action': 'commit', 'id': plan, 'confirmed': True}}
        self.assertFalse(self.client.request('tools/call', params, request_id='commit-once')[2]['result']['isError'])
        self.assertEqual(self.client.request('tools/call', params, request_id='commit-once')[2]['error']['code'], -32600)
        other = Client(self.server)
        other.initialize()
        self.assertTrue(other.call('accord_transition', params['arguments'])['isError'])
        self.assertEqual(len(self.server.accord.snapshot()['receipts']), 1)

    def test_http_persistence_failure_rolls_back_and_redacts_path(self):
        self.client.initialize()
        before = self.server.accord.snapshot()
        with patch.object(self.server.accord, 'save', side_effect=OSError('/private/example')):
            response = self.client.call('accord_propose', {'requests': [TASK]})
        self.assertTrue(response['isError'])
        self.assertNotIn('/private', json.dumps(response))
        self.assertEqual(self.server.accord.snapshot(), before)
        self.proposal()  # The same server recovers after the storage failure.

    def test_notifications_never_execute_tools_or_emit_rpc_responses(self):
        self.client.initialize()
        status, _, data = self.client.exchange({'jsonrpc': '2.0', 'method': 'tools/call',
            'params': {'name': 'accord_propose', 'arguments': {'requests': [TASK]}}})
        self.assertEqual((status, data), (202, None))
        self.assertEqual(self.server.accord.snapshot()['plans'], {})


if __name__ == '__main__':
    unittest.main(verbosity=2)
