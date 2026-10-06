import unittest, tempfile
from unittest.mock import patch
from pathlib import Path
from app import Accord, AccordError, digest

class Invariants(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.engine=Accord(Path(self.tmp.name)/'state.json')
    def request(self, appliance='Washing machine', owner='Alice', duration=60, latest=180):
        return dict(appliance=appliance,owner=owner,duration=duration,earliest=0,latest=latest)
    def approved(self, requests=None):
        p=self.engine.propose(requests or [self.request()])
        for resident in ('Alice','Bob'): self.engine.approve(p['id'],resident)
        return p
    def test_no_commit_without_all_consents(self):
        p=self.engine.propose([self.request()])
        with self.assertRaises(AccordError): self.engine.execute(p['id'])
        self.engine.approve(p['id'],'Alice')
        with self.assertRaises(AccordError): self.engine.execute(p['id'])
        self.assertEqual(self.engine.snapshot()['tasks'],[])
    def test_withdrawal_blocks_commit(self):
        p=self.approved();self.engine.approve(p['id'],'Bob',False)
        with self.assertRaises(AccordError):self.engine.execute(p['id'])
    def test_stale_proposal_rejected_after_other_commit(self):
        old=self.approved();new=self.approved([self.request('Dishwasher','Bob')]);self.engine.execute(new['id'])
        with self.assertRaises(AccordError):self.engine.execute(old['id'])
    def test_limit_revision_invalidates_consent(self):
        p=self.approved();self.engine.set_cap(3000)
        with self.assertRaises(AccordError):self.engine.execute(p['id'])
    def test_undo_restores_exact_agenda_and_persists(self):
        first=self.approved();self.engine.execute(first['id']);before=self.engine.snapshot()['tasks']
        second=self.approved([self.request('Dishwasher','Bob')]);receipt=self.engine.execute(second['id'])
        self.engine.undo(receipt['id']);self.assertEqual(self.engine.snapshot()['tasks'],before)
        self.assertEqual(Accord(self.engine.path).snapshot(),self.engine.snapshot())
    def test_no_undo_overwrites_later_changes(self):
        p=self.approved();r=self.engine.execute(p['id']);self.engine.set_cap(3000)
        with self.assertRaises(AccordError):self.engine.undo(r['id'])
    def test_schedule_respects_power_and_single_resource(self):
        p=self.approved([self.request(),self.request(owner='Bob'),self.request('Dishwasher','Bob')]);self.engine.execute(p['id'])
        tasks=self.engine.snapshot()['tasks']
        for minute in range(180):
            active=[t for t in tasks if t['start']<=minute<t['end']]
            self.assertLessEqual(sum(t['watts'] for t in active),2500)
            self.assertEqual(len({t['resource'] for t in active}),len(active))
    def test_impossible_request_leaves_no_mutation(self):
        before=self.engine.snapshot()
        with self.assertRaises(AccordError):self.engine.propose([self.request(latest=60),self.request('Dryer','Bob',60,60)])
        self.assertEqual(before,self.engine.snapshot())
    def test_double_commit_rejected_and_receipt_hash_valid(self):
        p=self.approved();r=self.engine.execute(p['id'])
        expected=r.pop('hash');self.assertEqual(expected,digest(r))
        with self.assertRaises(AccordError):self.engine.execute(p['id'])
    def test_failed_disk_commit_rolls_back_memory_and_disk(self):
        p=self.approved();before=self.engine.snapshot()
        with patch.object(self.engine,'save',side_effect=OSError('Disk full')):
            with self.assertRaises(OSError):self.engine.execute(p['id'])
        self.assertEqual(self.engine.snapshot(),before)
        self.assertEqual(Accord(self.engine.path).snapshot(),before)
    def test_invalid_input_and_cap_below_committed_usage(self):
        for key,value in [('duration',1),('earliest',True),('owner','Mallory')]:
            req=self.request();req[key]=value
            with self.assertRaises(AccordError):self.engine.propose([req])
        p=self.approved();self.engine.execute(p['id'])
        with self.assertRaises(AccordError):self.engine.set_cap(500)

if __name__=='__main__':unittest.main(verbosity=2)
