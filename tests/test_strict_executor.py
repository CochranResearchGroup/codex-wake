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
            identity=process_identity(os.getpid()), observed_at=100, interval=1)))
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
            value=json.loads(heartbeat.read_text());value['observed_at']=110;heartbeat.write_text(json.dumps(value))
            self.assertIsNone(guard.check(boottime=20))

    def test_old_usage_cannot_be_refreshed_by_repeated_polling(self):
        with tempfile.TemporaryDirectory() as root:
            import json
            guard, _, _ = self.fixture(root)
            self.assertIsNone(guard.check(boottime=11))
            heartbeat=Path(root)/'lifecycle/supervision.json'
            value=json.loads(heartbeat.read_text());value['observed_at']=110;heartbeat.write_text(json.dumps(value))
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
