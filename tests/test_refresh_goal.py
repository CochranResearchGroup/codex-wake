"""Operational refresh cannot turn a campaign stop into fresh authority."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from codex_wake.refresh_goal import pause, restore, settle_ui


class RefreshGoalTests(unittest.TestCase):
    def test_resource_stop_after_operational_pause_prevents_activation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'receipt.json'
            goal=dict(status='active',objective='same',createdAt=1,tokenBudget=100,
                      tokensUsed=20,timeUsedSeconds=3,updatedAt=2)
            receipt=dict(thread_id='source',intent={})
            calls=[]
            def request(method,params):
                calls.append((method,params))
                if method=='thread/goal/set':goal['status']=params['status']
                return dict(goal=dict(goal))
            with patch('codex_wake.refresh_goal.resource_ready',side_effect=[True,False]):
                self.assertTrue(pause(path,receipt,{},dict(goal),request))
                self.assertFalse(restore(path,receipt,{},request))
            self.assertEqual(goal['status'],'paused')
            self.assertEqual([p['status'] for m,p in calls if m=='thread/goal/set'],['paused'])
            self.assertEqual(json.loads(path.read_text())['reason'],'refresh_goal_restore_held')

    def test_stop_latch_is_not_eligible_even_with_armed_snapshot(self):
        from codex_wake.refresh_goal import resource_ready
        proof=dict(state='armed',stop_latched=True,controller=dict(fresh=True),
                   accounting=dict(state='qualified'),used_tokens=20,token_limit=100,deadline=9999)
        for intent in ({}, dict(configuration={'revision':1})):
            receipt=dict(thread_id='source',intent=intent)
            with self.subTest(configured=bool(intent)),patch('codex_wake.goal_supervision.show',return_value=proof),patch(
                    'codex_wake.lifecycle_budget.track_refresh_budget',return_value=True):
                self.assertFalse(resource_ready(Path('/unused'),receipt,
                    dict(goal_supervision=dict(root='/unused',policy='/unused',allocation_id='same')),{}))

    def test_modal_is_dismissed_once_without_activating_goal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'receipt.json';goal=dict(status='paused',tokensUsed=2,timeUsedSeconds=1,updatedAt=1)
            receipt=dict(thread_id='source',goal_before=goal,state='awaiting_preflight')
            frame='\n'.join(('\x1b[1mResume paused goal?\x1b[0m','\x1b[1;7m› 1. Resume goal',
                'Mark it active and continue when idle','2. Leave paused','Keep it paused; use /goal resume later'))
            calls=[]
            def command(runtime,*args,**kwargs):
                calls.append(args)
                return frame if args[0]=='capture-pane' else '0,0' if args[0]=='display-message' else ''
            with patch('codex_wake.session_lifecycle.tmux_command',side_effect=command),patch(
                    'codex_wake.sessions.revalidate_attachment',return_value=True):
                self.assertFalse(settle_ui(path,receipt,dict(timeout=1),dict(pane_id='%1'),lambda *a:dict(goal=goal)))
                self.assertFalse(settle_ui(path,receipt,dict(timeout=1),dict(pane_id='%1'),lambda *a:dict(goal=goal)))
            self.assertEqual([c for c in calls if c[0]=='send-keys'],[('send-keys','-t','%1','Escape')])
            self.assertEqual(goal['status'],'paused')
            self.assertEqual(receipt['reason'],'refresh_composer_or_dialog_unverified')
