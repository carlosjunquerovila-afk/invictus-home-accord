"""Audit regressions: malformed HTTP framing must not block a worker or mutate state."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from app import Accord
from test_http import QuietHandler

class AuditHTTP(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        self.server.accord = Accord(Path(self.tmp.name) / 'state.json')
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(2); self.tmp.cleanup()
    def request(self, headers, body=b'{}'):
        c = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=1)
        try:
            c.putrequest('POST', '/cap')
            c.putheader('Origin', f'http://127.0.0.1:{self.server.server_port}')
            for key, value in headers: c.putheader(key, value)
            c.endheaders(body)
            r = c.getresponse()
            return r.status, json.loads(r.read())
        finally: c.close()
    def test_invalid_framing_refused_without_mutation(self):
        before = self.server.accord.snapshot()
        for headers in [[('Content-Length', '-1')], [('Content-Length', '2'), ('Content-Length', '2')], [('Content-Length', '2'), ('Transfer-Encoding', 'chunked')], []]:
            with self.subTest(headers=headers): self.assertEqual(self.request(headers)[0], 400)
        self.assertEqual(self.server.accord.snapshot(), before)
    def test_disk_failure_returns_json_and_rolls_back(self):
        before = self.server.accord.snapshot()
        body = b'{"cap":3000}'
        with patch.object(self.server.accord, 'save', side_effect=OSError('private disk detail')):
            status, result = self.request([('Content-Length', str(len(body)))], body)
        self.assertEqual(status, 500)
        self.assertNotIn('private', str(result))
        self.assertEqual(self.server.accord.snapshot(), before)

    def test_lost_success_reply_does_not_claim_rollback(self):
        from email.message import Message
        from io import BytesIO
        handler = object.__new__(QuietHandler)
        handler.server = self.server
        handler.path = '/cap'
        handler.headers = Message()
        host = f'127.0.0.1:{self.server.server_port}'
        body = b'{"cap":3000}'
        for key, value in [('Host', host), ('Origin', 'http://' + host),
                           ('Content-Length', str(len(body)))]:
            handler.headers[key] = value
        handler.rfile = BytesIO(body)
        responses = []
        def broken_send(status, value):
            responses.append((status, value))
            if status == 200:
                raise BrokenPipeError('lost success response')
        handler.send = broken_send
        handler.do_POST()
        self.assertEqual([status for status, _ in responses], [200])
        self.assertTrue(handler.close_connection)
        self.assertEqual(self.server.accord.snapshot()['cap'], 3000)
        self.assertEqual(Accord(self.server.accord.path).snapshot()['cap'], 3000)
