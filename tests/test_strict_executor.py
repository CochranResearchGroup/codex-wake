import tempfile
import unittest
from pathlib import Path
from codex_wake.process import boot_id_value
from codex_wake.strict_executor import Guard


class StrictExecutorTests(unittest.TestCase):
    def test_boot_generation_mismatch_fences_before_launch(self):
        with tempfile.TemporaryDirectory() as root:
            guard = Guard(dict(wake_root=root, objective_id='goal', endpoint='unix:///tmp/owned.sock',
                codex_home=root, argv=['/bin/sleep', '20'], cwd=root,
                started_upper=100, started_boottime=10, boot_id='different-boot',
                deadline=200, status_path=str(Path(root)/'status.json'),
                configuration={'strict_execution': dict(poll_seconds=.2, accounting_max_age_seconds=45,
                    stop_grace_seconds=2, checkpoint_grace_seconds=1)}))
            self.assertEqual(guard.check(boottime=11), 'boot_identity_changed')

    def test_elapsed_deadline_reserves_both_graces_even_without_wall_clock(self):
        with tempfile.TemporaryDirectory() as root:
            guard = Guard(dict(wake_root=root, objective_id='goal', endpoint='unix:///tmp/owned.sock',
                codex_home=root, argv=['/bin/sleep', '20'], cwd=root,
                started_upper=100, started_boottime=10, boot_id=boot_id_value(),
                deadline=110, status_path=str(Path(root)/'status.json'),
                configuration={'strict_execution': dict(poll_seconds=.2, accounting_max_age_seconds=45,
                    stop_grace_seconds=2, checkpoint_grace_seconds=1)}))
            self.assertEqual(guard.check(boottime=17), 'deadline_reached')

    def test_dead_controller_fences_without_native_rpc(self):
        import json
        with tempfile.TemporaryDirectory() as root:
            lifecycle = Path(root)/'lifecycle'
            lifecycle.mkdir()
            (lifecycle/'supervision.json').write_text(json.dumps(dict(active=True, pid=999999999,
                identity={'start_time_ticks': 1}, observed_at=100, interval=1)))
            guard = Guard(dict(wake_root=root, objective_id='goal', endpoint='unix:///tmp/owned.sock',
                codex_home=root, argv=['/bin/sleep', '20'], cwd=root,
                started_upper=100, started_boottime=10, boot_id=boot_id_value(),
                deadline=200, status_path=str(Path(root)/'status.json'),
                configuration={'strict_execution': dict(poll_seconds=.2, accounting_max_age_seconds=45,
                    stop_grace_seconds=2, checkpoint_grace_seconds=1)}))
            self.assertEqual(guard.check(boottime=11), 'controller_unavailable')

    def fixture(self, root):
        import json, os
        from codex_wake.process import process_identity
        from codex_wake.objective_ledger import ObjectiveLedger
        cfg = dict(revision=1, objective_token_limit=150, objective_time_limit_seconds=100,
            session_token_limit=100, session_time_limit_seconds=80, max_correction_cycles=2,
            started_at=100, objective_deadline=200, strict_execution=dict(poll_seconds=.2,
            accounting_max_age_seconds=5, stop_grace_seconds=2, checkpoint_grace_seconds=1))
        lifecycle = Path(root)/'lifecycle'; lifecycle.mkdir()
        (lifecycle/'supervision.json').write_text(json.dumps(dict(active=True, pid=os.getpid(),
            identity=process_identity(os.getpid()), observed_at=100, interval=1, observed_boottime=10, boot_id=boot_id_value())))
        ledger = ObjectiveLedger(root, 'goal'); ledger.configure(cfg, 'operator', now=100)
        ledger.reserve('worker', 100, 80, now=100)
        (lifecycle/'spawn.json').write_text(json.dumps(dict(thread_id='owned-thread', budget_actor='worker',
            state='running', intent=dict(operation='spawn', configuration=cfg,
            continuation=dict(objective_id='goal'), launch=dict(app_server='unix:///tmp/owned.sock', codex_home=root)))))
        sessions=Path(root)/'sessions'; sessions.mkdir()
        rollout=sessions/'owned.jsonl'
        rollout.write_text(json.dumps(dict(type='session_meta', payload=dict(id='owned-thread')))+'\n'+
            json.dumps(dict(type='event_msg',timestamp='1970-01-01T00:01:40Z',payload=dict(type='token_count',
                info=dict(total_token_usage=dict(total_tokens=20,input_tokens=20,cached_input_tokens=10)))))+'\n')
        guard = Guard(dict(wake_root=root, objective_id='goal', endpoint='unix:///tmp/owned.sock',
            codex_home=root, argv=['/bin/sleep', '20'], cwd=root,
            started_upper=100, started_boottime=10, boot_id=boot_id_value(),
            deadline=180, status_path=str(Path(root)/'status.json'), configuration=cfg))
        return guard, ledger, rollout

    def test_native_cumulative_usage_charges_reserved_actor_including_cache(self):
        with tempfile.TemporaryDirectory() as root:
            guard, ledger, _ = self.fixture(root)
            self.assertIsNone(guard.check(boottime=11))
            self.assertEqual(ledger.inspect(now=101)['actors']['worker']['used'], 20)

    def test_settled_idle_assignment_does_not_falsely_expire_usage(self):
        with tempfile.TemporaryDirectory() as root:
            import json
            guard, ledger, _ = self.fixture(root)
            ledger.record('worker', 20, settled=True, now=100)
            heartbeat=Path(root)/'lifecycle/supervision.json'
            value=json.loads(heartbeat.read_text());value['observed_at']=110;value['observed_boottime']=20;heartbeat.write_text(json.dumps(value))
            self.assertIsNone(guard.check(boottime=20))

    def test_old_usage_cannot_be_refreshed_by_repeated_polling(self):
        with tempfile.TemporaryDirectory() as root:
            import json
            guard, _, _ = self.fixture(root)
            self.assertIsNone(guard.check(boottime=11))
            heartbeat=Path(root)/'lifecycle/supervision.json'
            value=json.loads(heartbeat.read_text());value['observed_at']=110;value['observed_boottime']=20;heartbeat.write_text(json.dumps(value))
            self.assertEqual(guard.check(boottime=20), 'accounting_stale')

    def test_known_usage_disappearing_stops_instead_of_restarting_grace(self):
        with tempfile.TemporaryDirectory() as root:
            guard, _, rollout = self.fixture(root)
            self.assertIsNone(guard.check(boottime=11))
            rollout.unlink()
            self.assertEqual(guard.check(boottime=12), 'accounting_missing')

    def test_guard_cli_writes_private_generation_fence_before_any_child_launch(self):
        import json, subprocess, sys
        with tempfile.TemporaryDirectory() as root:
            guard, _, _ = self.fixture(root)
            cfg=guard.config | {'boot_id': 'old-boot', 'generation': 'owned-generation',
                'argv': ['/bin/sh','-c','touch should-not-exist']}
            source=Path(root)/'guard.json'; source.write_text(json.dumps(cfg))
            result=subprocess.run([sys.executable,'-m','codex_wake.strict_executor',str(source)],
                capture_output=True,text=True,timeout=3)
            self.assertEqual(result.returncode, 5)
            status=Path(root)/'status.json'
            self.assertEqual(json.loads(status.read_text())['reason'], 'boot_identity_changed')
            self.assertEqual(json.loads(status.read_text())['generation'], 'owned-generation')
            self.assertEqual(status.stat().st_mode & 0o777, 0o600)
            self.assertFalse((Path(root)/'should-not-exist').exists())

    def test_known_zero_snapshot_disappearing_is_accounting_loss(self):
        with tempfile.TemporaryDirectory() as root:
            guard, _, rollout = self.fixture(root)
            rollout.write_text(rollout.read_text().replace('"total_tokens": 20','"total_tokens": 0'))
            self.assertIsNone(guard.check(boottime=11))
            rollout.unlink()
            self.assertEqual(guard.check(boottime=12), 'accounting_missing')

    def test_complete_usage_event_survives_incomplete_next_append(self):
        with tempfile.TemporaryDirectory() as root:
            guard, _, rollout = self.fixture(root)
            with rollout.open('a') as stream:
                stream.write('{"type":')
            self.assertIsNone(guard.check(boottime=11))

    def test_native_decrease_and_session_exhaustion_are_fences(self):
        for amount, expected in ((10, 'accounting_decreased'), (100, 'session_tokens_exhausted')):
            with self.subTest(amount=amount), tempfile.TemporaryDirectory() as root:
                guard, _, rollout = self.fixture(root)
                self.assertIsNone(guard.check(boottime=11))
                rollout.write_text(rollout.read_text().replace('"total_tokens": 20',f'"total_tokens": {amount}'))
                self.assertEqual(guard.check(boottime=12), expected)

    def test_controller_holding_ledger_lock_cannot_block_independent_guard(self):
        import fcntl, time
        with tempfile.TemporaryDirectory() as root:
            guard, ledger, _ = self.fixture(root)
            with ledger.lock_path.open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                started=time.monotonic()
                self.assertEqual(guard.check(boottime=11), 'accounting_unavailable')
                self.assertLess(time.monotonic()-started, .2)

    def test_renewed_ledger_does_not_silently_reauthorize_old_guard_generation(self):
        with tempfile.TemporaryDirectory() as root:
            guard, ledger, _ = self.fixture(root)
            changed=guard.config['configuration'] | {'revision': 2, 'objective_token_limit': 200}
            ledger.extend(changed, 'operator-renewal', now=101)
            self.assertEqual(guard.check(boottime=11), 'configuration_changed')

    def test_fresh_heartbeat_with_later_trusted_upper_is_not_a_dead_controller(self):
        import json
        with tempfile.TemporaryDirectory() as root:
            guard, _, _ = self.fixture(root)
            heartbeat=Path(root)/'lifecycle/supervision.json'
            value=json.loads(heartbeat.read_text());value['observed_at']=120;heartbeat.write_text(json.dumps(value))
            self.assertIsNone(guard.check(boottime=11))
            self.assertEqual(guard.check(boottime=17), 'controller_unavailable')
    def test_handoff_preflight_and_inherited_spawn_charge_one_cumulative_actor(self):
        import json
        with tempfile.TemporaryDirectory() as root:
            guard, ledger, source_rollout = self.fixture(root)
            ledger.record('worker', 20, settled=True, now=100)
            ledger.bind_goal('goal:owned-thread:100', 'worker', 0, now=100)
            ledger.reserve('handoff:next', 100, 80, now=100)
            ledger.record('handoff:next', 10, now=100)
            ledger.bind_goal('goal:successor-thread:101', 'handoff:next', 10, now=100)
            lifecycle = Path(root)/'lifecycle'
            intent = dict(operation='handoff', continuation=dict(objective_id='goal'),
                launch=dict(app_server=guard.config['endpoint'], codex_home=root))
            (lifecycle/'handoff.json').write_text(json.dumps(dict(thread_id='owned-thread',
                successor_thread_id='successor-thread', budget_actor='handoff:next',
                configuration=guard.config['configuration'], source_goal=dict(threadId='owned-thread',createdAt=100),
                successor_goal=dict(threadId='successor-thread',createdAt=101),intent=intent)))
            inherited = json.loads((lifecycle/'spawn.json').read_text())
            inherited.update(thread_id='successor-thread', budget_actor='handoff:next')
            inherited['intent']['budget_inherited']='handoff:next'
            (lifecycle/'inherited.json').write_text(json.dumps(inherited))
            (Path(root)/'sessions/successor.jsonl').write_text(source_rollout.read_text()
                .replace('owned-thread','successor-thread').replace('"total_tokens": 20','"total_tokens": 30'))
            self.assertIsNone(guard.check(boottime=11))
            view = ledger.inspect(now=101)
            self.assertEqual(view['tokens_used'], 50)
            self.assertEqual(view['actors']['handoff:next']['used'], 30)
            self.assertEqual(set(view['actors']), {'worker','handoff:next'})
            # Removing the redundant inherited receipt must retain attribution
            # through the canonical handoff; preflight and successor stay one actor.
            (lifecycle/'inherited.json').unlink()
            successor_rollout = Path(root)/'sessions/successor.jsonl'
            successor_rollout.write_text(successor_rollout.read_text().replace('"total_tokens": 30','"total_tokens": 40'))
            self.assertIsNone(guard.check(boottime=12))
            self.assertEqual(ledger.inspect(now=102)['tokens_used'], 60)

    def test_native_wall_timestamp_cannot_extend_monotonic_observation_lease(self):
        import json
        with tempfile.TemporaryDirectory() as root:
            guard, ledger, rollout = self.fixture(root)
            rollout.write_text(rollout.read_text().replace('1970-01-01T00:01:40Z','2099-01-01T00:00:00Z'))
            self.assertIsNone(guard.check(boottime=11))
            self.assertEqual(ledger.inspect(now=101)['tokens_used'], 20)
            heartbeat = Path(root)/'lifecycle/supervision.json'
            value = json.loads(heartbeat.read_text()); value['observed_at']=106;value['observed_boottime']=16
            heartbeat.write_text(json.dumps(value))
            self.assertEqual(guard.check(boottime=16), 'accounting_stale')

    def test_fresh_suspend_aware_heartbeat_survives_utc_observation_loss(self):
        import json
        with tempfile.TemporaryDirectory() as root:
            guard, _, _ = self.fixture(root)
            path=Path(root)/'lifecycle/supervision.json'
            heartbeat=json.loads(path.read_text())
            heartbeat.update(observed_at=None, observed_boottime=10, boot_id=boot_id_value())
            path.write_text(json.dumps(heartbeat))
            self.assertIsNone(guard.check(boottime=11))
            self.assertEqual(guard.check(boottime=16), 'controller_unavailable')

    def test_supervisor_publishes_boottime_even_when_authenticated_utc_is_unavailable(self):
        import time
        from unittest.mock import patch
        from codex_wake.lifecycle_supervision import publish_supervision
        with tempfile.TemporaryDirectory() as root:
            before=time.clock_gettime(time.CLOCK_BOOTTIME)
            with patch('codex_wake.lifecycle_supervision.trusted_upper',side_effect=ValueError('no UTC')):
                heartbeat=publish_supervision(root,.2)
            self.assertIsNone(heartbeat['observed_at'])
            self.assertEqual(heartbeat['boot_id'],boot_id_value())
            self.assertGreaterEqual(heartbeat['observed_boottime'],before)

    def test_strict_controller_heartbeat_requires_same_boot_and_nonfuture_elapsed_clock(self):
        import json
        for changes in ({'boot_id': 'different-boot'}, {'observed_boottime': 12},
                        {'observed_boottime': None}):
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as root:
                guard, _, _ = self.fixture(root)
                path=Path(root)/'lifecycle/supervision.json'
                heartbeat=json.loads(path.read_text());heartbeat.update(changes)
                path.write_text(json.dumps(heartbeat))
                self.assertEqual(guard.check(boottime=11), 'controller_unavailable')
