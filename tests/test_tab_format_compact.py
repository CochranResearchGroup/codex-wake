"""Compact tabs keep native names and omit repeated status/profile noise."""
import unittest
from codex_wake.tab_format_projection import project
from codex_wake.tab_format_expiry import expiring_options
from codex_wake.tab_format_policy import validate_policy


class CompactFormatTests(unittest.TestCase):
    def test_compact_plain_has_only_type_activity_and_native_name(self):
        def trait(v):return dict(value=v,observed_at=100,status='observed',freshness='fresh')
        resource=dict(traits=dict(panes=[dict(traits=dict(harness=trait('codex'),build=trait('modded'),account=trait('very-long-profile'),activity=trait('running')))]))
        policy=dict(compact=True,show_stale=False,render_mode='plain')
        self.assertEqual(validate_policy(policy),policy)
        shown=project(resource,policy,now=105)
        self.assertEqual(shown['options']['window-status-format'],' #I:CX+*#W ')
        self.assertNotIn('very-long-profile',str(shown['options']))
        self.assertEqual(shown['options']['window-status-style'],'fg=default,bg=default')
        expired=expiring_options(shown['options'],observed_at=100,render_mode='plain',show_stale=False)
        self.assertNotIn('STALE',str(expired))
        self.assertEqual(expired,shown['options'])
        self.assertEqual(project(resource,policy,now=125)['state'],'unknown')
        self.assertNotIn('STALE',str(project(resource,policy,now=125)['options']))

    def test_compact_shell_is_just_native_number_and_name(self):
        resource=dict(traits=dict(panes=[dict(traits={'session_presence':dict(value='absent')})]))
        shown=project(resource,dict(compact=True,render_mode='plain',show_stale=False),now=105)
        self.assertEqual(shown['options']['window-status-format'],' #I:#W ')
        self.assertIn('[#I:',shown['options']['window-status-current-format'])
