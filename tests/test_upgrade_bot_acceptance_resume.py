import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('upgrade_acceptance_resume',Path(__file__).parents[1]/'scripts/upgrade_bot_acceptance_resume.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class VerificationContinuationTests(unittest.TestCase):
    def test_same_job_reconciliation_stops_on_held_verification_without_new_admission(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'upgrade-bot.json').write_text(json.dumps(dict(target=dict(environment='test'))))
            calls=[];job=dict(id='existing',state='held',deadline=100,repair_attempts=3,created_at=1)
            class Jobs:
                def __init__(self,root):pass
                def execute(self,actor,operation,arguments,**kwargs):
                    calls.append(operation)
                    if operation=='upgrades.reconcile':job.update(state='queued')
                    if operation=='upgrades.advance':job.update(state='held',reason='verification_rejected')
                    return dict(result=dict(job=dict(job)))
            with patch.object(module,'UpgradeJobs',Jobs),patch.object(module,'local_actor',return_value=object()):
                result=module.run(root,'existing',100,3,root/'evidence')
            self.assertEqual(calls,['upgrades.show','upgrades.reconcile','upgrades.advance','upgrades.show'])
            self.assertEqual(result['job']['repair_attempts'],3)
            self.assertEqual(result['job']['deadline'],100)
            self.assertEqual(result['status'],'held')

    def test_original_accounting_mismatch_refuses_before_readmission(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'upgrade-bot.json').write_text(json.dumps(dict(target=dict(environment='test'))))
            calls=[]
            class Jobs:
                def __init__(self,root):pass
                def execute(self,actor,operation,arguments,**kwargs):
                    calls.append(operation)
                    return dict(result=dict(job=dict(id='existing',state='held',deadline=101,repair_attempts=3)))
            with patch.object(module,'UpgradeJobs',Jobs),patch.object(module,'local_actor',return_value=object()):
                result=module.run(root,'existing',100,3,root/'evidence')
            self.assertEqual(calls,['upgrades.show'])
            self.assertEqual(result['exit_code'],1)
            self.assertIn('original accounting',result['reason'])
