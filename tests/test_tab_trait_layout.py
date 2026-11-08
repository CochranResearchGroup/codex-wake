import shutil
import time
import unittest
import test_tab_organization as ordering_fixture
from codex_wake.tab_organization import TabOrganization, TmuxTransport


@unittest.skipUnless(shutil.which('tmux'),'tmux unavailable')
class TraitLayoutTests(unittest.TestCase):
    setUp=ordering_fixture.TabOrderingTests.setUp
    tmux=ordering_fixture.TabOrderingTests.tmux
    layout=ordering_fixture.TabOrderingTests.layout

    def test_trait_grouping_physically_reorders_and_conditionally_undoes(self):
        def evidence(timeout):
            result=ordering_fixture.TabOrderingTests.evidence(self,timeout)
            for value in result.values():
                value['traits']={'build':dict(value='modded' if value['state']=='working' else 'stock',status='observed')}
            return result
        owner=TabOrganization(self.root/'wake',transport=TmuxTransport(self.socket,self.session),observer=evidence,authorize=lambda action:None)
        before=evidence(5)
        plan=owner.preview(mode='traits',criteria=['build'],deadline=time.monotonic()+5)['plan']
        self.assertEqual([v['name'] for v in plan['target']],['focused','working','ready'])
        result=owner.apply(plan['plan_id'],deadline=time.monotonic()+5)
        self.assertEqual(result['status'],'applied')
        self.assertEqual(self.layout(),['focused','working','ready'])
        self.assertEqual(evidence(5),before)
        undone=owner.undo(result['receipt']['receipt_id'],deadline=time.monotonic()+5)
        self.assertEqual(undone['status'],'undone')
        self.assertEqual(self.layout(),['focused','ready','working'])
