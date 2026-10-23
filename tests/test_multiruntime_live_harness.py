"""Provider-free readiness regression for the opt-in MR06 launcher."""
import subprocess
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from scripts.multiruntime_live_qualification import prepare_tmux

@unittest.skipUnless(shutil.which("tmux"), "tmux required for terminal startup evidence")
class StartupEvidenceTests(unittest.TestCase):
    def test_immediate_tui_exit_keeps_pane_and_original_error_without_model_calls(self):
        with tempfile.TemporaryDirectory(prefix='cw-mr06-harness-') as tmp:
            root=Path(tmp);socket=root/'tmux.sock'
            def tmux(*args):
                return subprocess.run(['tmux','-S',str(socket),*map(str,args)],capture_output=True,
                                      text=True,check=True,timeout=3).stdout
            try:
                pane=prepare_tmux(tmux,root,['sh','-c','echo CW_STARTUP_FAILURE; exit 7'])
                deadline=time.monotonic()+3
                while tmux('display-message','-p','-t',pane,'#{pane_dead}').strip()!='1':
                    if time.monotonic()>deadline:self.fail('fixture command did not exit')
                    time.sleep(.02)
                while True:
                    captured=tmux('capture-pane','-p','-S','-2000','-t',pane)
                    if 'CW_STARTUP_FAILURE' in captured:break
                    if time.monotonic()>deadline:self.fail('startup error was not retained: '+captured)
                    time.sleep(.02)
                self.assertIn('CW_STARTUP_FAILURE',captured)
                self.assertEqual(tmux('display-message','-p','-t',pane,'#{pane_dead_status}').strip(),'7')
            finally:
                subprocess.run(['tmux','-S',str(socket),'kill-server'],capture_output=True,timeout=3)

class ActorHelperEvidenceTests(unittest.TestCase):
    def test_receive_prints_verified_claim_for_the_calling_tui(self):
        import json
        import os
        import sys
        from scripts.multiruntime_live_qualification import HELPER
        with tempfile.TemporaryDirectory(prefix='cw-claim-output-') as tmp:
            root=Path(tmp)
            cli=root/'fixture-cli'
            cli.write_text('#!'+sys.executable+'\nimport json,sys\n'
                           'print(json.dumps({"claimed":True} if sys.argv[2]=="ack" else '
                           '{"message":{"message_id":"fixture-reply"}}))\n')
            cli.chmod(0o700)
            (root/'actor-config.json').write_text(json.dumps(dict(cli=str(cli),bus=str(root/'bus'),
                codex_cap='fixture-capability',endpoint='fixture-endpoint',codex_thread='fixture-thread',nonce='fixture')))
            (root/'reverse-message.json').write_text('{"message_id":"fixture-message"}')
            helper=root/'actor_step.py';helper.write_text(HELPER)
            env=dict(os.environ,CODEX_THREAD_ID='fixture-thread')
            result=subprocess.run([sys.executable,str(helper),'codex','receive'],env=env,
                                  capture_output=True,text=True,check=True,timeout=5)
            shown=json.loads(result.stdout)
            self.assertEqual(shown['status'],'passed')
            self.assertIs(shown.get('claimed'),True)


class DispatchReceiptTests(unittest.TestCase):
    def test_cli_dispatch_envelope_reports_original_attempt_and_submission(self):
        from scripts.multiruntime_live_qualification import notification_outcome
        receipt={'schema_version':1,'success':True,'dispatch':{'status':'processed',
            'submitted':1,'results':[{'attempt_id':'fixture-attempt','status':'submitted'}]}}
        self.assertEqual(notification_outcome(receipt),(True,True,False))
