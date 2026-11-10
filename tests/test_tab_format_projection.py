"""Visual policy tests use public projection values from worked trait examples."""
import unittest

from codex_wake.tab_format_projection import project


def trait(value, at=100, status='observed', **fields):
    return dict(value=value, observed_at=at, status=status,
                freshness='fresh' if status=='observed' else status, source='fixture', **fields)


def resource(*panes):
    return dict(window=dict(window_id='@1',name='untouched name'),
                traits=dict(panes=[dict(pane_id='%'+str(i),traits=p) for i,p in enumerate(panes)],traits={}))


class ProjectionTests(unittest.TestCase):
    def test_mixed_tab_keeps_fresh_error_over_other_pane_warning_and_waiting(self):
        tab=resource(dict(harness=trait('codex'),build=trait('stock'),error=trait('present'),
                          activity=trait('running')),
                     dict(harness=trait('grok'),health=trait('unresponsive'),
                          activity=trait('waiting-for-input')))
        shown=project(tab,now=105)
        self.assertEqual(shown['label'],'MIX')
        self.assertEqual(shown['state'],'error')
        self.assertEqual(shown['colour'],'red')
        self.assertIn('ERR',shown['options']['window-status-format'])
        self.assertIn('#W',shown['options']['window-status-format'])
        self.assertIn('underscore',shown['options']['window-status-current-format'])

    def test_model_provider_rules_preserve_configured_vs_observed_and_legacy_provider(self):
        tab=resource(dict(harness=trait('custom-open'),model_identity=trait('qwen',status='configured'),
                          inference_provider=trait('ollama',status='configured'),provider=trait('grok'),
                          activity=trait('running')))
        shown=project(tab,dict(show_model=True,show_provider=True,style_rules=[
            dict(match={'inference_provider':'ollama'},colour='green'),
            dict(match={'harness':'custom-open'},colour='cyan')]),now=105)
        self.assertEqual(shown['colour'],'cyan')
        self.assertIn('cfg:qwen',shown['options']['window-status-format'])
        self.assertIn('cfg:ollama',shown['options']['window-status-format'])
        self.assertNotIn('grok',shown['options']['window-status-format'])
        self.assertEqual(shown['details']['panes'][0]['dimensions']['model']['status'],'configured')
        tab['traits']['panes'][0]['traits']['inference_provider']=trait('ollama')
        shown=project(tab,dict(style_rules=[dict(match={'inference_provider':'ollama'},colour='green')]),now=105)
        self.assertEqual(shown['colour'],'green')

    def test_stale_independent_traits_cannot_hide_fresh_error_or_invent_health(self):
        tab=resource(dict(harness=trait('codex',at=1),health=trait('unresponsive',at=1),
                          activity=trait('waiting-for-input',at=1),error=trait('present')))
        self.assertEqual(project(tab,now=105)['state'],'error')
        self.assertEqual(project(tab,now=121)['state'],'unknown')
        tab=resource(dict(session_presence=trait('absent'),health=trait('unknown',status='unsupported'),
                          error=trait('absent')))
        shown=project(tab,now=105)
        self.assertEqual(shown['label'],'SH')
        self.assertEqual(shown['state'],'unknown')
        self.assertNotIn('HLTH',shown['options']['window-status-format'])
        tab['traits']['panes'][0]['traits']['error']=trait('present',at=106)
        self.assertNotEqual(project(tab,now=105)['state'],'error')

    def test_activity_changes_type_intensity_without_losing_selected_cue(self):
        tab=resource(dict(harness=trait('codex'),build=trait('modded'),activity=trait('running')))
        running=project(tab,now=105)
        tab['traits']['panes'][0]['traits']['activity']=trait('idle')
        idle=project(tab,now=105)
        self.assertEqual(running['label'],'CX+')
        self.assertNotEqual(running['options']['window-status-style'],idle['options']['window-status-style'])
        for shown in (running,idle):
            self.assertIn('bold,underscore',shown['options']['window-status-current-style'])

    def test_quiet_valid_source_keeps_running_and_type_without_freshness_dimming(self):
        tab=resource(dict(harness=trait('codex',at=1),build=trait('modded',at=1),
                          activity=trait('running',at=1,source_available=True,source_epoch='one')))
        early=project(tab,dict(preset='slate'),now=5)
        quiet=project(tab,dict(preset='slate'),now=1000)
        self.assertEqual(quiet['state'],'running')
        self.assertEqual(quiet['label'],'CX+')
        self.assertEqual(quiet['options'],early['options'])
        self.assertNotIn('STALE',str(quiet['options']))
        self.assertNotIn('dim',str(quiet['options']))

    def test_source_loss_removes_cues_but_retains_inspect_evidence_and_type(self):
        tab=resource(dict(harness=trait('codex',at=1),build=trait('stock',at=1),
                          activity=trait('running',source_available=False),
                          error=trait('present',source_available=False)))
        shown=project(tab,dict(preset='slate'),now=105)
        self.assertEqual(shown['label'],'CX')
        self.assertEqual(shown['state'],'unknown')
        self.assertNotIn('*',shown['options']['window-status-format'])
        self.assertNotIn('!',shown['options']['window-status-format'])
        self.assertEqual(shown['details']['panes'][0]['attention']['error']['value'],'present')

    def test_untrusted_badges_and_native_manual_name_are_literal_on_tmux(self):
        import shutil
        import subprocess
        import tempfile
        from pathlib import Path
        if not shutil.which('tmux'):
            self.skipTest('tmux unavailable')
        tab=resource(dict(session_presence=trait('absent'),account=trait('#{pid}'),
                          model_identity=trait('#[bg=red]'),inference_provider=trait('#(printf BAD)')))
        shown=project(tab,dict(show_model=True,show_provider=True),now=105)
        with tempfile.TemporaryDirectory() as directory:
            socket=str(Path(directory)/'tmux.sock')
            def tmux(*arguments):
                return subprocess.run(['tmux','-S',socket,*arguments],capture_output=True,text=True,check=True,timeout=5).stdout
            tmux('new-session','-d','-s','fixture','-n','manual ##{pid}','sleep 30')
            try:
                displayed=tmux('display-message','-p','-t','@0',shown['options']['window-status-format'])
                self.assertIn('#{pid}',displayed)
                self.assertIn('#[bg=red]',displayed)
                self.assertIn('#(printf BAD)',displayed)
                self.assertIn('manual #{pid}',displayed)
                self.assertNotIn('\x1b',displayed)
                for key,value in shown['options'].items():
                    tmux('set-option','-w','-t','@0',key,value)
            finally:
                tmux('kill-server')
