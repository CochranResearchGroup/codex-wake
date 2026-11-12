"""Shell success must describe tab effects, not journal admission."""
import unittest

from codex_wake.tab_result import exit_status


class TabResultTests(unittest.TestCase):
    def test_unsuccessful_direct_and_retained_results_fail_but_pause_succeeds(self):
        for status in ('partial','uncertain','held','disabled','unsupported','failed','stale_target','unavailable'):
            for value in ({'status':status}, {'status':'completed','result':{'operation':{
                    'operation':'tabs.create','phase':'terminal','execution':'completed',
                    'result':{'status':status}}}}):
                with self.subTest(value=value):
                    self.assertEqual(exit_status(value),3)
        for operation, expected in [('tabs.format.pause',0),('tabs.format.enable',3)]:
            self.assertEqual(exit_status({'status':'completed','result':{'operation':{
                'operation':operation,'phase':'terminal','execution':'completed',
                'result':{'status':'paused','reason':'manual_session_style'}}}}),expected)
        self.assertEqual(exit_status({'status':'applied','failures':[{'code':'write_failed'}]}),3)
        self.assertEqual(exit_status({'status':'rolled_back','failures':[]}),0)
