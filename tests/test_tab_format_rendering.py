"""Rendering contract: text remains legible without colour and metadata is literal."""
import unittest
from codex_wake.tab_format_projection import project


def trait(value):return dict(value=value,status='observed',freshness='fresh',observed_at=100)


def tab(profile='personal'):
    return dict(target=dict(presentation='tmux'),window=dict(name='manual name'),traits=dict(panes=[dict(
        pane_id='%1',traits=dict(harness=trait('codex'),build=trait('modded'),account=trait(profile),activity=trait('waiting-for-input')))]))


class RenderingTests(unittest.TestCase):
    def test_plain_fallback_keeps_selected_marker_and_attention_without_colour(self):
        shown=project(tab(),dict(render_mode='plain'),now=105)
        self.assertEqual(shown['options']['window-status-style'],'fg=default,bg=default')
        self.assertIn('[#I',shown['options']['window-status-current-format'])
        self.assertNotIn('[#I',shown['options']['window-status-format'])
        self.assertIn('WAIT',shown['options']['window-status-format'])
        self.assertIn('CX+',shown['options']['window-status-format'])
        self.assertIn('#W',shown['options']['window-status-current-format'])

    def test_ascii_fallback_and_unicode_cell_bound_preserve_literal_metadata(self):
        from codex_wake.tab_format_rendering import badge_text
        self.assertEqual(badge_text('界'*12,ascii_only=False),'界'*8)
        self.assertTrue(badge_text('界 café \x1b #{pid}',ascii_only=True).isascii())
        shown=project(tab('#{pid},}#[bg=red]'),dict(ascii=True,render_mode='basic'),now=105)
        self.assertIn('##{pid}',shown['options']['window-status-format'])
        self.assertNotIn('colour',shown['options']['window-status-style'])
        self.assertEqual(shown['state'],'waiting')

    def test_stale_plain_rendering_retains_text_and_native_selection(self):
        from codex_wake.tab_format_expiry import expiring_options
        shown=project(tab(),dict(render_mode='plain'),now=105)
        stale=expiring_options(shown['options'],observed_at=100,render_mode='plain')
        self.assertNotIn('STALE',stale['window-status-current-format'])
        self.assertIn('[#I',stale['window-status-current-format'])
        self.assertNotIn('colour',stale['window-status-current-format'])
        self.assertNotIn('bg=red',stale['window-status-current-format'])

    def test_capabilities_do_not_promote_a_backend_name_to_runtime_qualification(self):
        from codex_wake.tab_format_rendering import capabilities
        unknown=capabilities('other')
        self.assertEqual(unknown['status'],'unsupported')
        self.assertFalse(unknown['native_selection'])
        known=capabilities('psmux',identity={'executable_sha256':'unqualified-build'})
        self.assertEqual(known['protocol'],'requires_native_qualification')
        self.assertEqual(known['client_rendering'],'requires_client_acceptance')
        self.assertEqual(known['colour_depth'],'unknown')

    def test_psmux_style_parser_cannot_consume_untrusted_metadata_after_expansion(self):
        value=tab('#[bg=red]')
        value['target']['presentation']='psmux'
        shown=project(value,dict(render_mode='full'),now=105)
        self.assertIn('## [bg=red]',shown['options']['window-status-format'])
        self.assertNotIn('##[bg=red]',shown['options']['window-status-format'])
