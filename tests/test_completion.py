"""Completion reads parser/registry metadata without launching account operations."""
import json
import subprocess
import os
import tempfile
import unittest
from pathlib import Path

from codex_wake.completion import candidates, render_script


class CompletionTests(unittest.TestCase):
    def test_commands_flags_and_choices_follow_the_real_parser(self):
        self.assertIn('accounts', candidates(['acc'], 0))
        self.assertIn('login', candidates(['accounts', 'lo'], 1))
        self.assertIn('--device-auth', candidates(['accounts', 'login', 'alice', '--d'], 3))
        self.assertEqual(candidates(['accounts', 'login', 'alice', '--channel', 's'], 4), ['stock'])

    def test_account_names_respect_selected_root_and_explicit_admission(self):
        with tempfile.TemporaryDirectory(prefix='completion root ') as temporary:
            root = Path(temporary)
            (root / 'controller-accounts.toml').write_text('[profiles]\nknown_profiles=["codex-alice","codex-bob"]\n[profiles.aliases]\nwork="alice"\nother="bob"\n[accounts]\nenabled=["alice"]\n')
            for header in (['--wake-root', str(root)], ['--wake-root=' + str(root)]):
                words = header + ['accounts', 'login', '']
                self.assertEqual(candidates(words, len(words)-1), ['alice', 'work'])
            # Completion must never follow a registry symlink, even to valid TOML.
            registry = root / 'controller-accounts.toml'
            registry.rename(root / 'elsewhere')
            registry.symlink_to(root / 'elsewhere')
            words = ['--wake-root', str(root), 'accounts', 'login', '']
            self.assertEqual(candidates(words, len(words)-1), [])

    def test_enabled_alias_uses_the_same_account_admission_as_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'controller-accounts.toml').write_text('[profiles]\nknown_profiles=["alice"]\n[profiles.aliases]\nwork="alice"\n[accounts]\nenabled=["work"]\n')
            words = ['--wake-root', directory, 'accounts', 'login', '']
            self.assertEqual(candidates(words, len(words)-1), ['alice', 'work'])

    def test_equal_form_account_flag_completes_names_and_aliases(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'controller-accounts.toml').write_text('[profiles]\nknown_profiles=["alice"]\n[profiles.aliases]\nwork="alice"\n')
            for flag, value in [('--account', 'al'), ('--account', 'wo')]:
                words = ['--wake-root', directory, 'builds', 'list', flag + '=' + value]
                expected = flag + '=' + ('alice' if value == 'al' else 'work')
                self.assertEqual(candidates(words, len(words)-1), [expected])

    def test_scripts_execute_in_bash_and_zsh_with_space_containing_root(self):
        import shlex
        import sys
        with tempfile.TemporaryDirectory(prefix='shell completion ') as temporary:
            root = Path(temporary)
            (root / 'controller-accounts.toml').write_text('[profiles]\nknown_profiles=["codex-alice"]\n')
            launcher = root / 'codex-wake'
            launcher.write_text('#!/bin/sh\n[ "$1" = completion ] && shift\nexec '+shlex.quote(sys.executable)+' -m codex_wake.completion "$@"\n')
            launcher.chmod(0o700)
            bash = root / 'completion.bash'
            bash.write_text(render_script('bash'))
            command = 'source "$1"; COMP_WORDS=("$2" --wake-root "$3" accounts login al); COMP_CWORD=5; _codex_wake; printf "%s\\n" "${COMPREPLY[@]}"'
            p = subprocess.run(['bash','--noprofile','--norc','-c',command,'bash',str(bash),str(launcher),str(root)],capture_output=True,text=True,check=True)
            self.assertEqual(p.stdout.strip(), 'alice')
            zsh = root / 'completion.zsh'
            zsh.write_text(render_script('zsh'))
            # compadd is a shell builtin valid only in a completion widget. Capture
            # its arguments here while running the generated function in real zsh.
            command = 'autoload -Uz compinit; compinit -D; source "$1"; function compadd { shift; print -l -- "$@"; }; words=("$2" --wake-root "$3" accounts login al); CURRENT=6; _codex_wake'
            p = subprocess.run(['zsh','-f','-c',command,'zsh',str(zsh),str(launcher),str(root)],capture_output=True,text=True,check=True,env=dict(os.environ,HOME=str(root)))
            self.assertEqual(p.stdout.strip(), 'alice')

    def test_interactive_tab_completion_in_both_shells_preserves_quoted_root(self):
        import pty
        import select
        import signal
        import shlex
        import sys
        import time
        with tempfile.TemporaryDirectory(prefix='interactive completion ') as temporary:
            root = Path(temporary)
            (root / 'controller-accounts.toml').write_text('[profiles]\nknown_profiles=["codex-alice"]\n')
            launcher = root / 'codex-wake'
            launcher.write_text('#!/bin/sh\n[ "$1" = completion ] && shift\nexec '+shlex.quote(sys.executable)+' -m codex_wake.completion "$@"\n')
            launcher.chmod(0o700)
            for shell in ('bash', 'zsh'):
                script = root / ('complete.'+shell)
                script.write_text(render_script(shell))
                master, slave = pty.openpty()
                env = dict(os.environ, HOME=str(root), PATH=str(root)+os.pathsep+os.environ['PATH'], TERM='xterm')
                argv = ['bash','--noprofile','--norc','-i'] if shell == 'bash' else ['zsh','-f','-i']
                process = subprocess.Popen(argv,stdin=slave,stdout=slave,stderr=slave,env=env,start_new_session=True)
                os.close(slave)
                def until(marker):
                    data = b''
                    deadline = time.monotonic()+10
                    while marker not in data and time.monotonic()<deadline:
                        if select.select([master],[],[],.2)[0]:
                            data += os.read(master,65536)
                    self.assertIn(marker,data,(shell,data))
                    return data
                try:
                    if shell == 'bash':
                        binding = '"\\C-x\\C-v": printf "\\036%s\\037" "$READLINE_LINE"'
                        setup = 'PS1=""; source '+shlex.quote(str(script))+'; bind -x '+shlex.quote(binding)+'; printf "\\036READY\\037"\n'
                    else:
                        setup = 'PS1=""; autoload -Uz compinit; compinit -D; source '+shlex.quote(str(script))+"; function _capture { print -rn -- $'\\036'$BUFFER$'\\037'; }; zle -N _capture; bindkey '^X^V' _capture; printf '\\036READY\\037'\n"
                    os.write(master,setup.encode())
                    until(b'\x1eREADY\x1f')
                    line='codex-wake --wake-root='+shlex.quote(str(root))+' accounts login al'
                    os.write(master,line.encode()+b'\t\x18\x16')
                    captured=until(b'\x1f')
                    self.assertIn(b'accounts login alice',captured,(shell,captured))
                    line='codex-wake --wake-root='+shlex.quote(str(root))+' builds list --account=al'
                    os.write(master,b'\x15'+line.encode()+b'\t\x18\x16')
                    captured=until(b'\x1f')
                    self.assertIn(b'builds list --account=alice',captured,(shell,captured))
                finally:
                    os.killpg(process.pid,signal.SIGTERM)
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid,signal.SIGKILL)
                        process.wait(timeout=3)
                    os.close(master)

    def test_equal_form_choice_completion_and_invalid_inputs_are_bounded(self):
        self.assertEqual(candidates(['accounts','login','alice','--channel=s'],3), ['--channel=stock'])
        self.assertEqual(candidates(['accounts'], -1), [])
