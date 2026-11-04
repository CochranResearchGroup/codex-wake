"""Rendered-client failure diagnostics through actual PowerShell and WSL."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from codex_wake.powershell_client import render

PS=Path('/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe')

@unittest.skipUnless(PS.is_file(),'requires actual Windows PowerShell and WSL')
class BootstrapDiagnosticsTests(unittest.TestCase):
    def invoke_fixture(self,stderr,exit_code=7,stdout='{"token":"PRIVATE_CONNECTION_SENTINEL"}'):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            cli=root/'fixture'
            cli.write_text('#!/usr/bin/env python3\nimport sys\nprint('+repr(stdout)+')\nprint('+repr(stderr)+',file=sys.stderr)\nsys.exit('+str(exit_code)+')\n')
            cli.chmod(0o700)
            script=root/'wake.ps1';script.write_text(render(root,cli=cli,distro='Ubuntu'))
            win=subprocess.check_output(['wslpath','-w',str(script)],text=True).strip()
            result=subprocess.run([str(PS),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',win,'result','absent'],capture_output=True,text=True,timeout=20)
            return result

    def test_structured_bootstrap_failure_preserves_exit_and_safe_category(self):
        result=self.invoke_fixture(json.dumps({'error':{'code':'controller_unavailable','message':'PRIVATE_ERROR_SENTINEL'}}))
        self.assertEqual(result.returncode,2)
        self.assertEqual(result.stdout,'')
        self.assertIn('wsl_exit=7',result.stderr)
        self.assertIn('category=controller_unavailable',result.stderr)
        self.assertNotIn('PRIVATE_',result.stdout+result.stderr)

    def test_unknown_native_error_never_prints_raw_stderr(self):
        for stderr in ['PRIVATE_UNKNOWN_SENTINEL',json.dumps({'error':{'code':'PRIVATE_CODE_SENTINEL','message':'PRIVATE_ERROR_SENTINEL'}})]:
            with self.subTest(stderr_type='structured' if stderr.startswith('{') else 'plain'):
                result=self.invoke_fixture(stderr,exit_code=19)
                self.assertEqual(result.returncode,2)
                self.assertEqual(result.stdout,'')
                self.assertIn('wsl_exit=19 category=unknown',result.stderr)
                self.assertNotIn('PRIVATE_',result.stdout+result.stderr)

    def test_malformed_successful_bootstrap_does_not_echo_private_stdout(self):
        result=self.invoke_fixture('',exit_code=0,stdout='PRIVATE_BAD_CONNECTION_SENTINEL')
        self.assertEqual(result.returncode,2)
        self.assertEqual(result.stdout,'')
        self.assertIn('category=invalid_connection',result.stderr)
        self.assertNotIn('PRIVATE_',result.stderr)
