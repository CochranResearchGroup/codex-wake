"""Family metadata reaches the existing visible formatter without hiding attention."""
import unittest
from codex_wake.tab_format_projection import project

class FamilyDisplayTests(unittest.TestCase):
    def resource(self):
        return dict(target=dict(presentation='tmux'), bot_family=dict(bot_id='task', root_bot_id='root', name='Repair billing', scope_kind='task', scope_ref='#604'), traits=dict(traits=dict(activity=dict(value='waiting-for-input',status='observed',observed_at=100))))

    def test_family_labels_survive_all_existing_layouts_and_attention_wins(self):
        for policy in ({},dict(compact=True),dict(preset='slate'),dict(render_mode='plain')):
            shown=project(self.resource(),policy,now=105)
            self.assertIn('task:Repair billing',shown['options']['window-status-format'])
            self.assertIn('#604',shown['options']['window-status-format'].replace('##','#'))
            self.assertIn('#W',shown['options']['window-status-format'])
            self.assertEqual(shown['state'],'waiting')
            self.assertEqual(shown['colour'],'yellow')
            self.assertEqual(shown['details']['bot_family']['root_bot_id'],'root')

    def test_family_accent_is_stable_and_metadata_literal(self):
        row=self.resource();row['traits']={};row['bot_family']['name']='#{pid}#[bg=red]'
        a=project(row,now=105);row['bot_family']['bot_id']='sibling'
        b=project(row,now=105)
        self.assertEqual(a['colour'],b['colour'])
        self.assertIn('##{pid}',a['options']['window-status-format'])
        self.assertNotIn('bg=red]',a['options']['window-status-style'])
