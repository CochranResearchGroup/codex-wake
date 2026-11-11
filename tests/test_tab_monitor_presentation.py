"""Human monitor CLI keeps retained uncertainty and machine exit semantics."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from codex_wake.controller_tabs import ControllerTabs
from codex_wake.tab_commands import command


class MonitorPresentationTests(unittest.TestCase):
    def test_stop_lost_response_has_readable_uncertainty_and_unchanged_json_exit(self):
        class LostResponseTabs(ControllerTabs):
            def execute(self, operation, arguments):
                value=super().execute(operation,arguments)
                if operation=='tabs.monitor.stop':
                    raise OSError('synthetic response lost after stop')
                return value

        with tempfile.TemporaryDirectory() as directory:
            owner=LostResponseTabs(directory,workspaces={},host='fixture',environment='test')
            args=SimpleNamespace(wake_root=Path(directory),tab_command='monitor-stop',
                arguments={},request_id='stop-lost-response',as_json=False)
            output=io.StringIO()
            with contextlib.redirect_stdout(output):
                code=command(args,owner=owner)
            self.assertEqual(code,3)
            self.assertIn('uncertain',output.getvalue())
            self.assertIn('tabs monitor-status',output.getvalue())
            args.as_json=True
            output=io.StringIO()
            with contextlib.redirect_stdout(output):
                code=command(args,owner=owner)
            self.assertEqual(code,3)
            value=json.loads(output.getvalue())
            self.assertEqual(value['result']['operation']['phase'],'uncertain')
            self.assertIsNone(value['result']['operation']['result'])
            from codex_wake.tab_monitor import TabMonitor
            self.assertNotEqual(TabMonitor(directory).status()['monitor']['status'],'running')


if __name__=='__main__':
    unittest.main()
