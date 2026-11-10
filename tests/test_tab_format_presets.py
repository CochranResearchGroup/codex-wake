"""Named presets are portable, reusable and preserve original theme custody."""
import unittest
from test_tab_formatting import FormattingTests
from codex_wake.tab_format_policy import validate_policy
from codex_wake.tab_format_projection import project


class PresetPolicyTests(unittest.TestCase):
    def test_named_presets_set_compact_defaults_and_validate_names(self):
        from codex_wake.managed_inventory import InventoryError
        for name in ('slate','dusk','graphite'):
            p=validate_policy({'preset':name})
            self.assertEqual(p['preset'],name)
            self.assertTrue(p['compact']);self.assertFalse(p['show_stale'])
            self.assertEqual(p['render_mode'],'full')
        with self.assertRaises(InventoryError):validate_policy({'preset':'#[bg=red]'})

    def test_slate_uses_preview_colors_on_badges_not_entire_tabs(self):
        def trait(value):return dict(value=value,status='observed',freshness='fresh',observed_at=100)
        r=dict(target=dict(presentation='tmux'),traits=dict(panes=[dict(traits=dict(
            harness=trait('codex'),build=trait('modded'),activity=trait('running'),account=trait('unneeded-profile')))]))
        shown=project(r,validate_policy({'preset':'slate'}),now=105)
        self.assertEqual(shown['options']['window-status-style'],'fg=#aeb9ca,bg=#171c24')
        self.assertIn('bg=#2b3544',shown['options']['window-status-current-style'])
        self.assertIn('#86bdb5',shown['options']['window-status-format'])
        self.assertNotIn('unneeded-profile',str(shown['options']))
        self.assertIn('#W',shown['options']['window-status-format'])


class PresetNativeTests(FormattingTests):
    def test_switch_presets_and_rollback_preserves_initial_baseline(self):
        before=self.tmux('show-options','-w','-t','@0')
        for preset in ('slate','dusk','graphite','slate'):
            self.call('configure',preset=preset)
            self.assertEqual(self.call('resume' if preset!='slate' or self.call('status')['record'] else 'enable')['status'],'applied')
            self.assertEqual(self.call('status')['policy']['preset'],preset)
            fmt=self.tmux('show-options','-w','-v','-t','@0','window-status-format')
            self.assertNotIn('STALE',fmt)
            text=self.tmux('display-message','-p','-t','@0',fmt)
            self.assertIn('original name',text)
        self.assertEqual(self.call('rollback')['status'],'rolled_back')
        self.assertEqual(self.tmux('show-options','-w','-t','@0'),before)

class PresetExpiryTests(unittest.TestCase):
    def test_quiet_expiry_dims_selected_palette_without_gray_background(self):
        from codex_wake.tab_format_expiry import expiring_options
        options={'window-status-format':' #I:#W ','window-status-current-format':' [#I:#W] ',
                 'window-status-style':'fg=#aeb9ca,bg=#171c24',
                 'window-status-current-style':'fg=#edf2fa,bg=#2b3544,bold'}
        expired=expiring_options(options,observed_at=100,show_stale=False)
        self.assertNotIn('STALE',str(expired))
        self.assertNotIn('colour238',str(expired))
        self.assertIn('bg=#171c24',expired['window-status-format'])
        self.assertIn('bg=#2b3544',expired['window-status-current-format'])
        self.assertIn('dim',expired['window-status-format'])
