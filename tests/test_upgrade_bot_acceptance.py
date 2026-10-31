import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('upgrade_acceptance',Path(__file__).parents[1]/'scripts/upgrade_bot_acceptance.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class AcceptanceLauncherTests(unittest.TestCase):
    def test_held_candidate_is_not_retried_or_given_new_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'upgrade-bot.json').write_text(json.dumps(dict(target=dict(environment='test'))))
            operations=[]
            job=dict(id='owned',state='queued',deadline=99,repair_attempts=0)
            class PublicJobs:
                def __init__(self,root):pass
                def execute(self,actor,operation,arguments,**kwargs):
                    operations.append(operation)
                    if operation=='upgrades.advance':job.update(state='held',reason='repair_attempts_exhausted',repair_attempts=3)
                    return dict(result=dict(job=dict(job)))
            with patch.object(module,'UpgradeJobs',PublicJobs),patch.object(module,'local_actor',return_value=object()):
                result=module.run(root,'release',root/'evidence')
            self.assertEqual(operations,['upgrades.enable','upgrades.start','upgrades.advance','upgrades.show'])
            self.assertEqual(result['job']['deadline'],99)
            self.assertEqual(result['job']['repair_attempts'],3)
            self.assertEqual(result['exit_code'],1)
            self.assertEqual(json.loads((root/'evidence/completion.json').read_text())['status'],'held')

    def test_production_target_is_refused_before_public_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'upgrade-bot.json').write_text(json.dumps(dict(target=dict(environment='production'))))
            with patch.object(module,'UpgradeJobs') as jobs:
                with self.assertRaisesRegex(ValueError,'disposable test'):module.run(root,'release',root/'evidence')
                jobs.assert_not_called()
