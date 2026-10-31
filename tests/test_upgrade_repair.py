"""Public repair executor acceptance, using real Git/process boundaries."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from codex_wake.upgrade_repair import UpgradeRepair


class UpgradeRepairTests(unittest.TestCase):
    def fixture(self, root):
        source=root/'source';source.mkdir()
        subprocess.run(['git','init','-q',str(source)],check=True)
        subprocess.run(['git','config','user.email','fixture@example.invalid'],cwd=source,check=True)
        subprocess.run(['git','config','user.name','Fixture'],cwd=source,check=True)
        (source/'feature.txt').write_text('old\n')
        subprocess.run(['git','add','.'],cwd=source,check=True)
        subprocess.run(['git','commit','-qm','base'],cwd=source,check=True)
        (source/'feature.txt').write_text('new\n')
        patch=root/'feature.patch';patch.write_bytes(subprocess.check_output(['git','diff','--binary'],cwd=source))
        subprocess.run(['git','checkout','--','.'],cwd=source,check=True)
        reviewer=root/'review.py'
        reviewer.write_text("""import json,os,pathlib
p=json.loads(pathlib.Path(os.environ['CODEX_UPGRADE_PACKET']).read_text())
r=dict(schema_version=1,status='approved',reviewer='independent',candidate_digest=p['candidate_digest'],tests_digest=p['tests_digest'],capabilities={c:'Verified feature and unchanged acceptance contract' for c in p['required_capabilities']},retirements={})
pathlib.Path(os.environ['CODEX_UPGRADE_RESPONSE']).write_text(json.dumps(r))
""")
        config=dict(base_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip(),patches=[dict(path=str(patch),sha256=hashlib.sha256(patch.read_bytes()).hexdigest(),id='feature',intent='feature remains new')],
            worker=dict(identity='repairer',argv=[sys.executable,str(root/'worker.py')]),
            reviewer=dict(identity='independent',argv=[sys.executable,str(reviewer)]),
            verify=[[sys.executable,'-c',"from pathlib import Path; assert Path('feature.txt').read_text() == 'new\\n'"]],regenerate=[])
        recipe=dict(schema_version=1,id='candidate',channel='modded',upstream_version='0.166.0',revision='fixture',source=dict(official_url='https://github.com/openai/codex/releases/download/fixture/source.tar'),patches=config['patches'],build=[],qualify=[])
        job=dict(id='job-one',deadline=time.time()+30,repair_attempts=0,limits=dict(repair_attempts=3,total_seconds=30,temporary_bytes=1024**2),required_capabilities=['scoped_reload'])
        return source,config,recipe,job

    def test_clean_replay_is_reviewed_and_snapshot_is_pinned_for_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source,config,recipe,job=self.fixture(root)
            result=UpgradeRepair(source,root/'evidence',config).run(job,recipe)
            self.assertEqual(result['status'],'reviewed',result)
            prepared=json.loads(Path(result['prepared_recipe']).read_text())
            snapshot=Path(prepared['source']['tree'])
            self.assertEqual((snapshot/'feature.txt').read_text(),'new\n')
            self.assertEqual(prepared['patches'],[])
            self.assertEqual(prepared['source']['files']['feature.txt'],hashlib.sha256(b'new\n').hexdigest())
            self.assertEqual(result['repair_attempts'],0)
            self.assertEqual(result['review']['reviewer'],'independent')
            self.assertEqual(result['patch_provenance'][0]['disposition'],'applied')

    def test_conflict_worker_repairs_and_spends_persisted_attempt_before_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source,config,recipe,job=self.fixture(root)
            (source/'feature.txt').write_text('upstream\n')
            subprocess.run(['git','add','.'],cwd=source,check=True)
            subprocess.run(['git','commit','-qm','upstream change'],cwd=source,check=True)
            config['base_revision']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
            worker=root/'worker.py';worker.write_text("""import json,os,pathlib,subprocess
pathlib.Path('feature.txt').write_text('new\\n')
subprocess.run(['git','add','feature.txt'],check=True)
pathlib.Path(os.environ['CODEX_UPGRADE_RESPONSE']).write_text(json.dumps(dict(schema_version=1,status='repaired',identity='repairer',patch_dispositions={'feature':dict(disposition='rewritten',evidence='Retained requested feature on changed upstream')},retirements={})))
""")
            charges=[]
            result=UpgradeRepair(source,root/'evidence',config,checkpoint=charges.append).run(job,recipe)
            self.assertEqual(result['status'],'reviewed',result)
            self.assertEqual(charges,[{'repair_attempts':1}])
            self.assertEqual(result['patch_provenance'][0]['disposition'],'rewritten')
            self.assertIn('tui_health',result['review']['capabilities'])
            self.assertIn('orphan_output',result['review']['capabilities'])
            again=UpgradeRepair(source,root/'evidence',config).run(job,recipe)
            self.assertEqual(again['repair_attempts'],1)

    def test_worker_cannot_omit_later_patches_or_claim_another_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source,config,recipe,job=self.fixture(root)
            (source/'feature.txt').write_text('upstream\n')
            subprocess.run(['git','add','.'],cwd=source,check=True)
            subprocess.run(['git','commit','-qm','upstream change'],cwd=source,check=True)
            config['base_revision']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
            (root/'worker.py').write_text("""import json,os,pathlib,subprocess
pathlib.Path('feature.txt').write_text('new\\n')
subprocess.run(['git','add','feature.txt'],check=True)
pathlib.Path(os.environ['CODEX_UPGRADE_RESPONSE']).write_text(json.dumps(dict(schema_version=1,status='repaired',identity='unknown',patch_dispositions={},retirements={})))
""")
            result=UpgradeRepair(source,root/'evidence',config).run(job,recipe)
            self.assertEqual(result['status'],'held',result)
            self.assertEqual(result['reason'],'worker_identity_or_status_mismatch')

    def test_staged_conflict_markers_cannot_be_reviewed_as_a_clean_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source,config,recipe,job=self.fixture(root)
            (source/'feature.txt').write_text('upstream\n')
            subprocess.run(['git','add','.'],cwd=source,check=True)
            subprocess.run(['git','commit','-qm','upstream change'],cwd=source,check=True)
            config['base_revision']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
            job['limits']['repair_attempts']=1
            (root/'worker.py').write_text("""import json,os,pathlib,subprocess
pathlib.Path('feature.txt').write_text('new\\n')
pathlib.Path('other.rs').write_text('<<<<<<< ours\\na\\n=======\\nb\\n>>>>>>> theirs\\n')
subprocess.run(['git','add','.'],check=True)
pathlib.Path(os.environ['CODEX_UPGRADE_RESPONSE']).write_text(json.dumps(dict(schema_version=1,status='repaired',identity='repairer',patch_dispositions={'feature':dict(disposition='rewritten',evidence='ported')},retirements={})))
""")
            result=UpgradeRepair(source,root/'evidence',config).run(job,recipe)
            self.assertEqual(result['status'],'held',result)
            self.assertEqual(result['reason'],'repair_attempts_exhausted')

    def test_host_repair_config_cannot_omit_original_recipe_patches(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source,config,recipe,job=self.fixture(root)
            recipe['patches']=json.loads(json.dumps(recipe['patches']))
            recipe['patches'].append(dict(path=str(root/'omitted.patch'),sha256='a'*64))
            result=UpgradeRepair(source,root/'evidence',config).run(job,recipe)
            self.assertEqual(result['status'],'held',result)
            self.assertEqual(result['reason'],'original_patch_stack_mismatch')

    def test_reviewer_source_mutation_invalidates_approval_and_generated_files_are_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source,config,recipe,job=self.fixture(root)
            reviewer=Path(config['reviewer']['argv'][1])
            reviewer.write_text(reviewer.read_text()+"\npathlib.Path('generated.rs').write_text('changed after review')\n")
            result=UpgradeRepair(source,root/'evidence',config).run(job,recipe)
            self.assertEqual(result['status'],'held',result)
            self.assertEqual(result['reason'],'candidate_changed_during_review')

    def test_crash_during_attempt_checkpoint_keeps_the_attempt_charged(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source,config,recipe,job=self.fixture(root)
            (source/'feature.txt').write_text('upstream\n')
            subprocess.run(['git','add','.'],cwd=source,check=True)
            subprocess.run(['git','commit','-qm','upstream change'],cwd=source,check=True)
            config['base_revision']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
            def interrupted(unused):raise KeyboardInterrupt()
            with self.assertRaises(KeyboardInterrupt):
                UpgradeRepair(source,root/'evidence',config,checkpoint=interrupted).run(job,recipe)
            result=UpgradeRepair(source,root/'evidence',config).run(job,recipe)
            self.assertEqual(result['status'],'held')
            self.assertEqual(result['repair_attempts'],1)
            self.assertEqual(result['reason'],'interrupted_repair_reconcile_required')

    def test_upstream_workspace_pin_must_match_before_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source,config,recipe,job=self.fixture(root)
            config['base_revision']='a'*40
            result=UpgradeRepair(source,root/'evidence',config).run(job,recipe)
            self.assertEqual(result['status'],'held',result)
            self.assertEqual(result['reason'],'upstream_source_identity_mismatch')
            self.assertEqual((source/'feature.txt').read_text(),'old\n')
