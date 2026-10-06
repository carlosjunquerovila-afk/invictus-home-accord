"""Real loopback HTTP test; no external service is accessed."""
import json, tempfile, threading, unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
from app import Handler, Accord

class QuietHandler(Handler):
    def log_message(self, *args): pass

class HTTPWorkflow(unittest.TestCase):
    def test_real_http_consent_commit_and_undo(self):
        with tempfile.TemporaryDirectory() as tmp:
            server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
            server.accord=Accord(Path(tmp)/'state.json')
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            root=f'http://127.0.0.1:{server.server_port}'
            def post(path,payload,origin=None):
                headers={'Content-Type':'application/json'}
                if origin:headers['Origin']=origin
                with urlopen(Request(root+path,json.dumps(payload).encode(),headers),timeout=2) as response:return json.load(response)
            try:
                with urlopen(root,timeout=2) as response:
                    html=response.read().decode();self.assertIn('Alexa+ experience simulation',html);self.assertIn('plan my evening',html)
                proposal=post('/plan',{'requests':[dict(owner='Alice',appliance='Dishwasher',duration=60,earliest=0,latest=180)]})
                with self.assertRaises(HTTPError) as caught:post('/execute',{'id':proposal['id']})
                self.assertEqual(caught.exception.code,400)
                with self.assertRaises(HTTPError) as caught:post('/approve',{'id':proposal['id'],'resident':'Alice'},'https://untrusted.example')
                self.assertEqual(caught.exception.code,403)
                for resident in ('Alice','Bob'):post('/approve',{'id':proposal['id'],'resident':resident})
                receipt=post('/execute',{'id':proposal['id']})
                with urlopen(root+'/state',timeout=2) as response:self.assertEqual(len(json.load(response)['tasks']),1)
                post('/undo',{'id':receipt['id']})
                with urlopen(root+'/state',timeout=2) as response:self.assertEqual(json.load(response)['tasks'],[])
            finally:
                server.shutdown();server.server_close();thread.join(timeout=2)

if __name__=='__main__':unittest.main(verbosity=2)
