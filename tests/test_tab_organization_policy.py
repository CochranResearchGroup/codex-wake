"""Opted-in policy effects through the public owner on an isolated tmux server."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

from codex_wake.controller_tab_adapters import TmuxAttachmentTransport
from codex_wake.process import process_identity


@unittest.skipUnless(shutil.which('tmux'), 'tmux unavailable')
class TabOrganizationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.socket = str(self.root / 'tmux.sock')
        self.tmux('new-session', '-d', '-s', 'policy', '-n', 'focused', 'sleep 120')
        self.addCleanup(lambda: subprocess.run(['tmux', '-S', self.socket, 'kill-server'], capture_output=True))
        self.tmux('new-window', '-d', '-t', '$0:', '-n', 'zeta', 'sleep 120')
        self.tmux('new-window', '-d', '-t', '$0:', '-n', 'alpha', 'sleep 120')
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        self.clock = [100.0]
        self.transport = TmuxAttachmentTransport(self.socket, '$0')
        self.workspaces = {'owned': dict(kind='byobu', transport=self.transport, observer=self.observer)}

    def tmux(self, *args):
        return subprocess.check_output(['tmux', '-S', self.socket, *args], text=True).strip()

    def layout(self):
        return self.tmux('list-windows', '-t', '$0', '-F', '#{window_name}').splitlines()

    def observer(self, timeout):
        snapshot = self.transport.snapshot(time.monotonic() + timeout)
        result = {}
        for w in snapshot['windows']:
            for p in w['panes']:
                identity = process_identity(p['pid'])
                harness = 'codex' if w['name'].startswith('alpha') else 'grok'
                result[p['pane_id']] = dict(fresh=True, conversation_id=p['pane_id'], namespace='fixture',
                    root=str(self.root), state='ready', process=dict(pid=p['pid'],
                    start_ticks=identity['start_time_ticks'], boot_id=identity['boot_id']),
                    traits={'harness': dict(value=harness, status='observed', freshness='fresh', observed_at=self.clock[0])})
        return result

    def owner(self):
        from codex_wake.tab_organization_policy import TabOrganizationPolicy
        return TabOrganizationPolicy(self.root, workspaces=self.workspaces, clock=lambda: self.clock[0])

    def configure(self, owner):
        return owner.execute('tabs.policy.configure', dict(workspace='owned', mode='traits', criteria=['harness'],
            debounce_seconds=2, min_interval_seconds=30, max_swaps_per_tick=2))

    def test_default_disabled_then_debounced_opt_in_effect_is_reversible(self):
        owner = self.owner()
        before = self.layout()
        self.assertEqual(owner.execute('tabs.policy.tick', {})['policy']['state'], 'disabled')
        self.assertEqual(self.layout(), before)
        self.configure(owner)
        self.assertEqual(self.layout(), before)
        owner.execute('tabs.policy.enable', {})
        first = owner.execute('tabs.policy.tick', {})
        self.assertEqual(first['policy']['last_reason'], 'debouncing')
        self.assertEqual(self.layout(), before)
        self.clock[0] += 3
        applied = owner.execute('tabs.policy.tick', {})
        self.assertEqual(applied['result']['status'], 'applied')
        self.assertEqual(self.layout(), ['focused', 'alpha', 'zeta'])
        receipt = applied['result']['receipt']['receipt_id']
        from codex_wake.tab_organization import TabOrganization
        undone = TabOrganization(self.root, transport=self.transport, observer=self.observer,
                                 authorize=lambda action: None).undo(receipt, deadline=time.monotonic() + 5)
        self.assertEqual(undone['status'], 'undone')
        self.assertEqual(self.layout(), before)

    def test_manual_layout_pauses_and_disable_survives_restart(self):
        owner = self.owner()
        self.configure(owner)
        owner.execute('tabs.policy.enable', {})
        windows = self.transport.snapshot(time.monotonic() + 5)['windows']
        self.tmux('swap-window', '-d', '-s', windows[1]['window_id'], '-t', windows[2]['window_id'])
        manual = self.layout()
        held = owner.execute('tabs.policy.tick', {})
        self.assertEqual(held['policy']['state'], 'paused')
        self.assertEqual(held['policy']['last_reason'], 'manual_layout_or_binding_changed')
        self.assertEqual(self.layout(), manual)
        owner.execute('tabs.policy.disable', {})
        self.clock[0] += 60
        self.assertEqual(self.owner().execute('tabs.policy.tick', {})['policy']['state'], 'disabled')
        self.assertEqual(self.layout(), manual)

    def test_stale_trait_evidence_holds_without_mislabeling_manual_movement(self):
        owner = self.owner()
        self.configure(owner)
        owner.execute('tabs.policy.enable', {})
        good = self.observer(5)
        self.workspaces['owned']['observer'] = lambda timeout: good
        self.clock[0] += 21
        before = self.layout()
        result = self.owner().execute('tabs.policy.tick', {})
        self.assertFalse(result['physical_effects'])
        self.assertEqual(result['policy']['last_reason'], 'unqualified_observations')
        self.assertEqual(self.layout(), before)

    def test_uncertain_swap_is_retained_and_restart_never_replays_it(self):
        from codex_wake.managed_inventory import InventoryError
        class Interrupted(TmuxAttachmentTransport):
            def swap(self, first, second, deadline):
                super().swap(first, second, deadline)
                raise OSError('synthetic lost response after actual swap')
        self.workspaces['owned']['transport'] = Interrupted(self.socket, '$0')
        owner = self.owner()
        self.configure(owner)
        owner.execute('tabs.policy.enable', {})
        owner.execute('tabs.policy.tick', {})
        self.clock[0] += 3
        result = owner.execute('tabs.policy.tick', {})
        self.assertEqual(result['policy']['state'], 'paused')
        self.assertEqual(result['policy']['last_reason'], 'layout_uncertain')
        self.assertIsNotNone(result['policy']['pending_plan'])
        observed = self.layout()
        self.clock[0] += 60
        restarted = self.owner().execute('tabs.policy.tick', {})
        self.assertFalse(restarted['physical_effects'])
        self.assertEqual(self.layout(), observed)
        with self.assertRaises(InventoryError) as caught:
            self.owner().execute('tabs.policy.enable', {})
        self.assertEqual(caught.exception.code, 'policy_reconciliation_required')
        resumed = self.owner().execute('tabs.policy.enable', {'acknowledge_pending': True})
        self.assertEqual(resumed['policy']['state'], 'enabled')
        self.assertIsNone(resumed['policy']['pending_plan'])
        self.assertEqual(resumed['policy']['last_reconciled_plan']['plan_id'], result['policy']['pending_plan'])
        self.assertEqual(self.layout(), observed)
        # Explicitly accepting the current layout never rewrites old uncertainty.
        from codex_wake.tab_organization import TabOrganization
        records = TabOrganization(self.root, transport=self.transport)
        self.assertEqual(records.read(result['policy']['last_receipt'])['status'], 'uncertain')

    def test_swap_cap_refuses_whole_plan_before_any_movement(self):
        self.tmux('new-window', '-d', '-t', '$0:', '-n', 'alpha2', 'sleep 120')
        owner = self.owner()
        owner.execute('tabs.policy.configure', dict(workspace='owned', mode='traits', criteria=['harness'],
            debounce_seconds=0, min_interval_seconds=30, max_swaps_per_tick=1))
        owner.execute('tabs.policy.enable', {})
        before = self.layout()
        result = owner.execute('tabs.policy.tick', {})
        self.assertEqual(result['policy']['last_reason'], 'swap_limit')
        self.assertFalse(result['physical_effects'])
        self.assertEqual(self.layout(), before)

    def test_rate_limit_and_operator_pause_have_no_additional_effects(self):
        owner = self.owner()
        self.configure(owner)
        owner.execute('tabs.policy.enable', {})
        owner.execute('tabs.policy.tick', {})
        self.clock[0] += 3
        owner.execute('tabs.policy.tick', {})
        old_observer = self.observer
        def inverted(timeout):
            result = old_observer(timeout)
            for sample in result.values():
                trait = sample['traits']['harness']
                trait['value'] = 'grok' if trait['value'] == 'codex' else 'codex'
            return result
        self.workspaces['owned']['observer'] = inverted
        before = self.layout()
        limited = self.owner().execute('tabs.policy.tick', {})
        self.assertEqual(limited['policy']['last_reason'], 'rate_limited')
        self.assertEqual(self.layout(), before)
        self.owner().execute('tabs.policy.pause', {'reason': 'operator arranging tabs'})
        self.clock[0] += 60
        held = self.owner().execute('tabs.policy.tick', {})
        self.assertEqual(held['policy']['state'], 'paused')
        self.assertEqual(held['policy']['last_reason'], 'operator arranging tabs')
        self.assertEqual(self.layout(), before)

    def test_explicit_pin_and_saved_view_remain_independent(self):
        from codex_wake.tab_views import TabViews
        from codex_wake.managed_inventory import InventoryError
        views = TabViews(self.root)
        before = self.layout()
        views.execute('tabs.view-save', {'name': 'errors', 'definition': {'filters': {'error': 'present'}}})
        self.assertEqual(self.layout(), before)
        owner = self.owner()
        with self.assertRaises(InventoryError) as unsupported:
            owner.execute('tabs.policy.configure', {'workspace': 'owned', 'view': 'errors'})
        self.assertEqual(unsupported.exception.code, 'unsupported_target')
        self.assertEqual(owner.execute('tabs.policy.status', {})['policy']['state'], 'disabled')
        snapshot = self.transport.snapshot(time.monotonic() + 5)
        alpha = next(w['window_id'] for w in snapshot['windows'] if w['name'] == 'alpha')
        owner.execute('tabs.policy.configure', dict(workspace='owned', mode='traits', criteria=['harness'], pins=[alpha]))
        owner.execute('tabs.policy.enable', {})
        self.clock[0] += 60
        result = owner.execute('tabs.policy.tick', {})
        self.assertFalse(result['physical_effects'])
        self.assertEqual(self.layout(), before)
