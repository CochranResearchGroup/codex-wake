"""Display policy acceptance at the public controller boundary."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from codex_wake.controller_tab_adapters import TmuxAttachmentTransport
from codex_wake.controller_tabs import ControllerTabs


class GlobalPolicyTests(unittest.TestCase):
    def test_global_optout_persists_without_a_terminal_and_has_its_own_target(self):
        with tempfile.TemporaryDirectory() as directory:
            owner=ControllerTabs(directory,workspaces={},host='host',environment='local')
            result=owner.execute('tabs.format.configure',dict(scope='global',policy={'enabled':False}))
            self.assertEqual(result['status'],'configured')
            restarted=ControllerTabs(directory,workspaces={},host='host',environment='local')
            result=restarted.execute('tabs.format.status',dict(scope='global'))
            self.assertFalse(result['policy']['enabled'])
            self.assertEqual(result['target']['workspace'],'*')
            self.assertEqual(result['target']['presentation'],'formatting')
            self.assertEqual(len(result['target']['generation']),64)

    def test_public_cli_global_configure_and_inspect_need_no_adapter(self):
        import sys
        with tempfile.TemporaryDirectory() as directory:
            config=Path(directory)/'controller-tabs.json'
            config.write_text(json.dumps(dict(schema_version=1,workspaces={})));config.chmod(0o600)
            def command(*args):
                result=subprocess.run([sys.executable,'-m','codex_wake.entrypoint','--wake-root',directory,
                    'tabs',*args],capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                return json.loads(result.stdout)
            command('format-configure','--scope','global','--policy','{"enabled":false}')
            self.assertFalse(command('format-inspect','--scope','global')['policy']['enabled'])

    def test_workspace_grant_cannot_change_or_inspect_global_policy(self):
        import time
        from types import SimpleNamespace
        from codex_wake.controller_auth import Actor, AuthError
        from codex_wake.controller_http import ProtectedOperations
        from codex_wake.controller_operations import ControllerOperations
        from codex_wake.managed_inventory import ManagedInventory
        with tempfile.TemporaryDirectory() as directory:
            tabs=ControllerTabs(directory,workspaces={},host='host',environment='local')
            scope=dict(host='host',environment='local',workspace='work',presentation='tmux')
            actor=Actor('caller','service','client','grant','issuer','resource',frozenset(('control','observe')),
                        [scope],time.time()+60)
            facade=ProtectedOperations(SimpleNamespace(authenticate=lambda token:actor),
                ControllerOperations(ManagedInventory(directory),host='host',environment='local',tabs=tabs))
            with self.assertRaises(AuthError):
                facade.execute('token','tabs.format.configure',dict(scope='global',policy={'enabled':False},
                    expected_target=tabs.format_target(scope='global')))
            with self.assertRaises(AuthError):
                facade.execute('token','tabs.format.inspect',dict(scope='global'))
            self.assertTrue(tabs.execute('tabs.format.status',dict(scope='global'))['policy']['enabled'])

    def test_invalid_policy_cannot_inject_terminal_styles_or_redefine_provider(self):
        from codex_wake.managed_inventory import InventoryError
        with tempfile.TemporaryDirectory() as directory:
            tabs=ControllerTabs(directory,workspaces={},host='host',environment='local')
            for policy in ({'render_mode':'automatic'}, {'enabled':'false'},
                {'style_rules':[dict(match={'provider':'codex'},colour='red')]},
                {'style_rules':[dict(match={'harness':'codex'},colour='red,bold')]},
                {'style_rules':[dict(match={'model':'line\nbreak'},colour='green')]}):
                with self.subTest(policy=policy):
                    with self.assertRaises(InventoryError):
                        tabs.execute('tabs.format.configure',dict(scope='global',policy=policy))
            good={'style_rules':[dict(match={'inference_provider':'ollama'},colour='colour255')]}
            self.assertEqual(tabs.execute('tabs.format.configure',dict(scope='global',policy=good))['policy']['style_rules'],good['style_rules'])


import test_tab_formatting as formatting_fixture


@unittest.skipUnless(shutil.which('tmux'), 'tmux unavailable')
class WorkspacePolicyTests(unittest.TestCase):
    setUp=formatting_fixture.FormattingTests.setUp
    tmux=formatting_fixture.FormattingTests.tmux
    call=formatting_fixture.FormattingTests.call

    def test_manual_style_hold_survives_reenable_and_restart_until_explicit_resume(self):
        self.call('enable')
        self.tmux('set-option','-w','-t','@0','window-status-style','bg=green,fg=black')
        self.call('reenable')
        self.assertEqual(self.tmux('show-options','-w','-v','-t','@0','window-status-style').strip(),'bg=green,fg=black')
        self.assertTrue(self.call('inspect')['record']['windows']['@0']['paused'])
        self.tabs=ControllerTabs(self.root,workspaces=self.tabs.workspaces,host='test',environment='local')
        self.call('reenable')
        self.assertTrue(self.call('inspect')['record']['windows']['@0']['paused'])
        self.assertEqual(self.call('resume')['status'],'applied')
        self.assertFalse(self.call('inspect')['record']['windows']['@0'].get('paused',False))
        self.assertNotEqual(self.tmux('show-options','-w','-v','-t','@0','window-status-style').strip(),'bg=green,fg=black')

    def test_theme_parent_changes_hold_and_rollback_preserves_new_global_theme(self):
        self.call('enable')
        self.tmux('set-option','-g','-w','window-status-style','fg=yellow,bg=blue')
        self.call('reenable')
        saved=self.call('inspect')['record']['windows']['@0']
        self.assertTrue(saved['paused'])
        self.assertEqual(self.call('rollback')['status'],'rolled_back')
        self.assertEqual(self.tmux('show-options','-g','-w','-v','window-status-style').strip(),'fg=yellow,bg=blue')
        self.assertEqual(self.tmux('show-options','-w','-t','@0','window-status-style'),'')

    def test_workspace_preferences_reset_without_discarding_original_custody(self):
        self.call('configure',policy={'show_model':True,'render_mode':'basic'})
        restarted=ControllerTabs(self.root,workspaces=self.tabs.workspaces,host='test',environment='local')
        self.tabs=restarted
        self.assertTrue(self.call('status')['policy']['show_model'])
        self.call('enable')
        original=self.call('inspect')['record']['windows']['@0']['original']
        result=self.call('reset')
        self.assertEqual(result['status'],'reset')
        inspected=self.call('inspect')
        self.assertFalse(inspected['policy']['show_model'])
        self.assertEqual(inspected['policy']['render_mode'],'full')
        self.assertEqual(inspected['record']['windows']['@0']['original'],original)
        self.assertEqual(self.call('reenable')['status'],'applied')

    def test_global_optout_dominates_workspace_override_and_inspection_keeps_details(self):
        self.call('configure',policy={'enabled':True})
        self.tabs.execute('tabs.format.configure',dict(scope='global',policy={'enabled':False}))
        self.assertEqual(self.call('enable')['status'],'disabled')
        self.assertFalse(self.call('status')['policy']['enabled'])
        self.tabs.execute('tabs.format.configure',dict(scope='global',policy={'enabled':True}))
        self.assertEqual(self.call('enable')['status'],'applied')
        inspected=self.call('inspect')
        self.assertIn('panes',inspected['record']['windows']['@0']['projection']['details'])
        self.assertEqual(inspected['capabilities']['protocol'],'requires_native_qualification')
        self.tmux('rename-window','-t','@0','renamed normally')
        self.assertEqual(self.call('reenable')['status'],'applied')
        self.assertFalse(self.call('inspect')['record']['windows']['@0'].get('paused',False))
        self.assertEqual(self.tmux('display-message','-p','-t','@0','#{window_name}').strip(),'renamed normally')

    def test_namespace_alias_cannot_capture_decorated_settings_as_another_original(self):
        from codex_wake.managed_inventory import InventoryError
        self.call('enable')
        original=self.call('inspect')['record']['windows']['@0']['original']
        self.tabs.workspaces['alias']=self.tabs.workspaces['work']
        with self.assertRaises(InventoryError) as error:
            self.tabs.execute('tabs.format.enable',dict(workspace='alias'))
        self.assertEqual(error.exception.code,'formatting_custody_conflict')
        self.assertEqual(self.call('inspect')['record']['windows']['@0']['original'],original)
        self.assertEqual(self.call('rollback')['status'],'rolled_back')
