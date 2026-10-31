import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('operator_probe',Path(__file__).parents[1]/'scripts/upgrade_bot_operator_probe.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class OperatorNoticeGrantTests(unittest.TestCase):
    def test_notice_control_scope_does_not_renew_expiry_or_replace_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);original=dict(version=1,local_caller=dict(subject='owner',client_id='client',grant_id='grant',expires_at=1234,scopes=['admin','observe'],targets=[{'namespace':'upgrade'}]))
            (root/'controller-messaging.json').write_text(json.dumps(original))
            result=module.register_notice_recipient(root,{'namespace':'exact-operator'})
            after=json.loads((root/'controller-messaging.json').read_text())
            self.assertEqual(after['local_caller']['expires_at'],1234)
            self.assertEqual([after['local_caller'][key] for key in ('subject','client_id','grant_id')],['owner','client','grant'])
            self.assertEqual(after['local_caller']['scopes'],['admin','observe','control'])
            self.assertEqual(after['local_caller']['targets'],[{'namespace':'upgrade'},{'namespace':'exact-operator'}])
            self.assertTrue(result['expiry_unchanged'])
            self.assertEqual(result['scopes_added'],['control'])
            again=module.register_notice_recipient(root,{'namespace':'exact-operator'})
            self.assertEqual(json.loads((root/'controller-messaging.json').read_text()),after)
            self.assertEqual(again['scopes_added'],[])
