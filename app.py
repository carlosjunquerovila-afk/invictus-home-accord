"""Local household agent-workflow simulation. No external calls or device control."""
from copy import deepcopy
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse, json, threading, uuid
from functools import wraps

STEP = 15
RESIDENTS = ['Alice', 'Bob']
APPLIANCES = {'Dishwasher': (1000, 'dishwasher'), 'Washing machine': (1800, 'washer'), 'Dryer': (2000, 'dryer')}

class AccordError(ValueError):
    pass

def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def mutation(method):
    """Rollback in-memory mutations if validation or atomic file replacement fails."""
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with self.lock:
            before = deepcopy(self.state)
            try:
                return method(self, *args, **kwargs)
            except Exception:
                self.state = before
                raise
    return wrapped

class Accord:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()
        if self.path.exists():
            self.state = json.loads(self.path.read_text())
        else:
            self.state = {'version': 0, 'cap': 2500, 'tasks': [], 'plans': {}, 'receipts': []}
            self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix('.tmp')
        temp.write_text(json.dumps(self.state, indent=2))
        temp.replace(self.path)

    def snapshot(self):
        with self.lock:
            return deepcopy(self.state)

    def fits(self, candidate, scheduled, cap):
        for t in scheduled:
            if candidate['start'] < t['end'] and t['start'] < candidate['end'] and t['resource'] == candidate['resource']:
                return False
        for moment in range(candidate['start'], candidate['end'], STEP):
            used = sum(t['watts'] for t in scheduled if t['start'] <= moment < t['end'])
            if used + candidate['watts'] > cap:
                return False
        return True

    def normalize(self, raw):
        if raw.get('owner') not in RESIDENTS or raw.get('appliance') not in APPLIANCES:
            raise AccordError('Choose a known resident and appliance.')
        def integer(key, minimum, maximum):
            value = raw.get(key)
            if type(value) is not int or value < minimum or value > maximum or value % STEP:
                raise AccordError(f'{key} must be a multiple of 15 between {minimum} and {maximum}.')
            return value
        duration = integer('duration', STEP, 180)
        earliest = integer('earliest', 0, 180)
        latest = integer('latest', STEP, 180)
        if earliest + duration > latest:
            raise AccordError('The requested time window is too short.')
        watts, resource = APPLIANCES[raw['appliance']]
        return {'id': str(uuid.uuid4()), 'owner': raw['owner'], 'appliance': raw['appliance'], 'watts': watts,
                'resource': resource, 'duration': duration, 'earliest': earliest, 'latest': latest}

    @mutation
    def propose(self, requests):
        with self.lock:
            if not isinstance(requests, list) or not 1 <= len(requests) <= 8:
                raise AccordError('Supply between one and eight tasks.')
            normalized = [self.normalize(r) for r in requests]
            scheduled = deepcopy(self.state['tasks'])
            additions = []
            # Deterministic earliest-feasible placement. No claim of optimal scheduling.
            for task in sorted(normalized, key=lambda t: (t['latest'], t['earliest'], t['owner'])):
                placed = None
                for start in range(task['earliest'], task['latest'] - task['duration'] + 1, STEP):
                    candidate = {**task, 'start': start, 'end': start + task['duration']}
                    if self.fits(candidate, scheduled, self.state['cap']):
                        placed = candidate
                        break
                if placed is None:
                    raise AccordError('No feasible placement found by the greedy planner. Widen a window, reduce duration, or revise the power limit. This does not prove no feasible schedule exists.')
                scheduled.append(placed)
                additions.append(placed)
            plan = {'id': str(uuid.uuid4()), 'base_version': self.state['version'], 'cap': self.state['cap'],
                    'additions': additions, 'required': RESIDENTS.copy(), 'approvals': [], 'status': 'pending'}
            self.state['plans'][plan['id']] = plan
            self.save()
            return deepcopy(plan)

    def plan(self, plan_id):
        plan = self.state['plans'].get(plan_id)
        if plan is None:
            raise AccordError('Unknown proposal.')
        if plan['status'] != 'pending':
            raise AccordError('This proposal is already closed.')
        if plan['base_version'] != self.state['version']:
            raise AccordError('Stale proposal: household state changed. Create a fresh proposal.')
        return plan

    @mutation
    def approve(self, plan_id, resident, consent=True):
        with self.lock:
            plan = self.plan(plan_id)
            if resident not in plan['required'] or type(consent) is not bool:
                raise AccordError('Unknown resident or invalid consent.')
            plan['approvals'] = [r for r in plan['approvals'] if r != resident]
            if consent:
                plan['approvals'].append(resident)
            self.save()
            return deepcopy(plan)

    def receipt(self, kind, before, after, **extra):
        item = {'id': str(uuid.uuid4()), 'kind': kind, 'version': self.state['version'],
                'before_hash': digest(before), 'after_hash': digest(after),
                'previous_hash': self.state['receipts'][-1]['hash'] if self.state['receipts'] else None,
                **extra}
        item['hash'] = digest(item)
        self.state['receipts'].append(item)
        return deepcopy(item)

    @mutation
    def execute(self, plan_id):
        with self.lock:
            plan = self.plan(plan_id)
            if set(plan['approvals']) != set(plan['required']):
                raise AccordError('Every resident must approve this exact proposal before committing.')
            scheduled = deepcopy(self.state['tasks'])
            for task in plan['additions']:
                if not self.fits(task, scheduled, self.state['cap']):
                    raise AccordError('Constraints changed or proposal is invalid.')
                scheduled.append(deepcopy(task))
            before = deepcopy(self.state['tasks'])
            self.state['tasks'] = scheduled
            self.state['version'] += 1
            plan['status'] = 'committed'
            result = self.receipt('commit', before, scheduled, plan_id=plan_id, approvals=plan['approvals'].copy(), before_tasks=before)
            self.save()
            return result

    @mutation
    def set_cap(self, cap):
        with self.lock:
            if type(cap) is not int or not 500 <= cap <= 5000:
                raise AccordError('Power limit must be an integer between 500 and 5000 W.')
            for minute in range(0, 180, STEP):
                if sum(t['watts'] for t in self.state['tasks'] if t['start'] <= minute < t['end']) > cap:
                    raise AccordError('The new limit would invalidate the committed agenda.')
            if cap != self.state['cap']:
                self.state['cap'] = cap
                self.state['version'] += 1
                self.save()

    @mutation
    def undo(self, receipt_id):
        with self.lock:
            if not self.state['receipts']:
                raise AccordError('There is no receipt to undo.')
            original = self.state['receipts'][-1]
            if original['id'] != receipt_id or original['kind'] != 'commit' or original['version'] != self.state['version']:
                raise AccordError('Undo requires the latest unchanged commit. Later changes must not be overwritten.')
            if digest(self.state['tasks']) != original['after_hash']:
                raise AccordError('The agenda does not match its receipt.')
            before = deepcopy(self.state['tasks'])
            self.state['tasks'] = deepcopy(original['before_tasks'])
            self.state['version'] += 1
            result = self.receipt('undo', before, self.state['tasks'], target=receipt_id)
            self.save()
            return result

class Handler(BaseHTTPRequestHandler):
    def send(self, status, value, content_type='application/json'):
        data = json.dumps(value).encode() if content_type == 'application/json' else value
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == '/':
            return self.send(200, Path(__file__).with_name('index.html').read_bytes(), 'text/html; charset=utf-8')
        if self.path == '/state':
            return self.send(200, self.server.accord.snapshot())
        self.send(404, {'error': 'Not found'})

    def do_POST(self):
        try:
            # Same-origin localhost interface only; refuse cross-site browser mutation.
            origin = self.headers.get('Origin')
            expected = f'http://{self.headers.get("Host")}'
            if origin and origin != expected:
                return self.send(403, {'error': 'Cross-origin action refused.'})
            size = int(self.headers.get('Content-Length', 0))
            if size > 32768:
                return self.send(413, {'error': 'Request too large'})
            data = json.loads(self.rfile.read(size))
            engine = self.server.accord
            if self.path == '/plan': result = engine.propose(data.get('requests'))
            elif self.path == '/approve': result = engine.approve(data.get('id'), data.get('resident'), data.get('consent', True))
            elif self.path == '/execute': result = engine.execute(data.get('id'))
            elif self.path == '/undo': result = engine.undo(data.get('id'))
            elif self.path == '/cap': engine.set_cap(data.get('cap')); result = engine.snapshot()
            else: return self.send(404, {'error': 'Not found'})
            self.send(200, result)
        except (AccordError, ValueError, TypeError, AttributeError) as exc:
            self.send(400, {'error': str(exc)})

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--state', default=str(Path(__file__).with_name('state.json')))
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    server.accord = Accord(args.state)
    print(f'Invictus Home Accord: http://127.0.0.1:{args.port}', flush=True)
    server.serve_forever()
