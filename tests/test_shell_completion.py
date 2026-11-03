"""User install lifecycle preserves unrelated and edited shell configuration."""
import tempfile
import unittest
from pathlib import Path

from codex_wake.shell_completion import configure


class ShellCompletionTests(unittest.TestCase):
    def test_install_repeat_and_uninstall_preserve_shell_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            startup = home / '.bashrc'
            startup.write_text('export KEEP=yes\n')
            configure('install', home=home)
            first = startup.read_text()
            self.assertIn('export KEEP=yes', first)
            self.assertIn('codex-wake completion', first)
            configure('install', home=home)
            self.assertEqual(startup.read_text(), first)
            configure('uninstall', home=home)
            self.assertEqual(startup.read_text(), 'export KEEP=yes\n')
            self.assertFalse((home / '.local/share/bash-completion/completions/codex-wake').exists())

    def test_edits_and_ambiguous_markers_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            configure('install', shell='bash', home=home)
            file = home / '.local/share/bash-completion/completions/codex-wake'
            file.write_text(file.read_text() + '# User edit\n')
            with self.assertRaisesRegex(ValueError, 'edited completion'):
                configure('install', shell='bash', home=home)
            result = configure('uninstall', shell='bash', home=home)
            self.assertIn(str(file), result['preserved'])
            self.assertIn('# User edit', file.read_text())
            self.assertNotIn('codex-wake completion', (home / '.bashrc').read_text())
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            rc = home / '.bashrc'
            rc.write_text('# >>> codex-wake completion >>>\nuser edit\n')
            with self.assertRaisesRegex(ValueError, 'ambiguous'):
                configure('install', shell='bash', home=home)
            self.assertEqual(rc.read_text(), '# >>> codex-wake completion >>>\nuser edit\n')
            self.assertFalse((home / '.local/share/bash-completion/completions/codex-wake').exists())

    def test_symlink_and_unowned_file_refusal_is_effect_free(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            elsewhere = home / 'elsewhere'
            elsewhere.write_text('preserve me')
            (home / '.bashrc').symlink_to(elsewhere)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                configure('install', shell='bash', home=home)
            self.assertEqual(elsewhere.read_text(), 'preserve me')
            self.assertFalse((home / '.local/share/bash-completion/completions/codex-wake').exists())
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            file = home / '.local/share/bash-completion/completions/codex-wake'
            file.parent.mkdir(parents=True)
            file.write_text('another implementation')
            with self.assertRaisesRegex(ValueError, 'unowned'):
                configure('install', shell='bash', home=home)
            self.assertEqual(file.read_text(), 'another implementation')

    def test_installer_default_optout_and_completion_failure(self):
        import os
        import subprocess
        with tempfile.TemporaryDirectory(prefix='installer home ') as temporary:
            home = Path(temporary)
            bin_dir = home / 'bin'
            bin_dir.mkdir()
            log = home / 'calls'
            (bin_dir / 'uv').write_text('#!/bin/sh\nif [ "$1 $2 $3" = "tool dir --bin" ]; then printf "%s\\n" "$TEST_BIN"; else printf "uv install\\n" >> "$TEST_LOG"; fi\n')
            (bin_dir / 'codex-wake').write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$TEST_LOG"\nexit "${TEST_EXIT:-0}"\n')
            for file in bin_dir.iterdir():
                file.chmod(0o700)
            env = dict(os.environ, PATH=str(bin_dir)+os.pathsep+os.environ['PATH'], TEST_BIN=str(bin_dir), TEST_LOG=str(log))
            installer = str(Path(__file__).resolve().parents[1] / 'scripts/install.sh')
            subprocess.run(['bash',installer,'--home',str(home),'--shell','bash'],env=env,capture_output=True,check=True)
            self.assertIn('completion install --shell bash --home '+str(home), log.read_text())
            log.write_text('')
            subprocess.run(['bash',installer,'--no-completion'],env=env,capture_output=True,check=True)
            self.assertEqual(log.read_text(), 'uv install\n')
            p = subprocess.run(['bash',installer],env=dict(env,TEST_EXIT='2'),capture_output=True,text=True)
            self.assertEqual(p.returncode, 2)
            self.assertIn('completion setup failed', p.stderr)
            self.assertNotIn('installation completed', p.stdout)

    def test_existing_explicit_activation_is_not_duplicated_or_removed(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            rc = home / '.bashrc'
            original = '. "$HOME/.local/share/bash-completion/completions/codex-wake"\n'
            rc.write_text(original)
            configure('install', shell='bash', home=home)
            self.assertEqual(rc.read_text(), original)
            configure('uninstall', shell='bash', home=home)
            self.assertEqual(rc.read_text(), original)
