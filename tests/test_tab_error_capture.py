"""Current-screen checks share native clients without retaining raw screens."""
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from codex_wake.tab_organization import TmuxTransport
from codex_wake.tab_observation import ObservationCache


@unittest.skipUnless(shutil.which('tmux'),'tmux unavailable')
class ErrorCaptureTests(unittest.TestCase):
    def test_due_panes_share_capture_roundtrip_and_cached_panes_are_not_recaptured(self):
        class Transport(TmuxTransport):
            def command(self,deadline,*args):
                if 'capture-pane' in args:
                    self.capture_roundtrips+=1
                    if self.fail_capture:
                        raise TimeoutError('synthetic current-screen failure')
                return super().command(deadline,*args)
        with tempfile.TemporaryDirectory() as directory:
            socket=str(Path(directory)/'tmux.sock');tmux=['tmux','-S',socket]
            command="printf '\\n%.0s' $(seq 1 22); printf '\\033[31mError: private fixture text\\033[0m\\n'; exec sleep 60"
            subprocess.run([*tmux,'new-session','-d','-s','fixture',command],check=True)
            try:
                for _ in range(2):subprocess.run([*tmux,'new-window','-d','-t','fixture','sleep 60'],check=True)
                transport=Transport(socket,'$0');transport.capture_roundtrips=0;transport.fail_capture=False
                until=time.monotonic()+3
                while 'private fixture text' not in transport.command(until,'capture-pane','-p','-e','-t','%0'):
                    self.assertLess(time.monotonic(),until);time.sleep(.01)
                snapshot=transport.snapshot(until);transport.capture_roundtrips=0
                now=[0.0];cache=ObservationCache(directory,monotonic=lambda:now[0])
                observed,_=cache.observe('fixture',snapshot,transport=transport,deadline=time.monotonic()+3)
                errors=[p['traits']['error'] for row in observed.values() for p in row['panes']]
                self.assertEqual([e['value'] for e in errors],['present','absent','absent'])
                self.assertNotIn('private fixture text',str(observed))
                self.assertEqual(transport.capture_roundtrips,1,'due panes should share one finite native client')
                now[0]=6;cache.mark_dirty('fixture',['%0'])
                observed,_=cache.observe('fixture',snapshot,transport=transport,deadline=time.monotonic()+3)
                self.assertEqual(observed['@0']['panes'][0]['traits']['error']['value'],'present')
                self.assertEqual(transport.capture_roundtrips,2,'only the dirty pane is due after six seconds')
                now[0]=12;transport.fail_capture=True
                cache.mark_dirty('fixture',['%0','%1','%2'])
                failed,_=cache.observe('fixture',snapshot,transport=transport,deadline=time.monotonic()+3)
                self.assertEqual(transport.capture_roundtrips,3,'one failed batch must not fan out into retries')
                errors=[p['traits']['error'] for row in failed.values() for p in row['panes']]
                self.assertTrue(all(error['value']=='unknown' for error in errors))
                self.assertEqual(errors[0]['last_observation']['value'],'present')
                self.assertNotIn('private fixture text',str(failed))
            finally:
                subprocess.run([*tmux,'kill-server'],check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
