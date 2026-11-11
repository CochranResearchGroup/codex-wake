"""CLI status follows the retained operation outcome, including partial setup."""
import json
import os
import signal
import shutil
import subprocess
import sys
import time
import unittest

import test_tab_format_autostart as autostart_fixture


@unittest.skipUnless(shutil.which('tmux'),'tmux unavailable')
class FormattingCLIStatusTests(unittest.TestCase):
    setUp=autostart_fixture.FormattingAutostartTests.setUp
    tmux=autostart_fixture.FormattingAutostartTests.tmux

    def test_unqualified_running_monitor_is_partial_exit_without_restarting_it(self):
        started=self.monitor.execute('tabs.monitor.start',dict(interval=300,stale_after=600))
        # A published owner is not a completed cycle. Wait through the public
        # status seam before freezing this fixture; stopping mid-cycle can
        # strand its formatting lock and test contention instead of capability.
        deadline=time.monotonic()+10
        while True:
            report=self.monitor.execute('tabs.monitor.status',{})['monitor']
            if ((report.get('last_formatting') or {}).get('status')=='completed'
                    and report.get('last_routing') is not None):break
            self.assertLess(time.monotonic(),deadline,report)
            time.sleep(.01)
        identity=started['monitor']['process'];pid=identity['pid']
        # Freeze only this owned fixture publisher so it cannot overwrite the
        # legacy-capability fixture while the real CLI observes it.
        os.kill(pid,signal.SIGSTOP)
        try:
            path=self.root/'tab-monitor'/'owner.json'
            record=json.loads(path.read_text());record['capabilities']=[]
            path.write_text(json.dumps(record))
            completed=subprocess.run([sys.executable,'-m','codex_wake.entrypoint','--wake-root',str(self.root),
                'tabs','format','enable','--workspace','work','--json'],capture_output=True,text=True,timeout=15)
            value=json.loads(completed.stdout)['result']['operation']['result']
            self.assertIsNotNone(value,completed.stdout+'\n'+completed.stderr)
            self.assertEqual(value['status'],'partial')
            self.assertIn('monitor_formatting_unqualified',[f['code'] for f in value['failures']])
            self.assertEqual(self.monitor.execute('tabs.monitor.status',{})['monitor']['process'],identity)
            self.assertEqual(completed.returncode,3,completed.stdout+completed.stderr)
        finally:
            os.kill(pid,signal.SIGCONT)
