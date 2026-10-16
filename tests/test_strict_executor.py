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

    def test_settlement_at_session_cap_does_not_remove_exhaustion_fence(self):
        with tempfile.TemporaryDirectory() as root:
            guard, ledger, rollout = self.fixture(root)
            rollout.write_text(rollout.read_text().replace('"total_tokens": 20','"total_tokens": 100'))
            ledger.record('worker',100,settled=True,now=100)
            self.assertEqual(guard.check(boottime=11),'session_tokens_exhausted')

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

    def test_failed_native_turn_retains_cumulative_usage_including_cached_input(self):
        import json
        with tempfile.TemporaryDirectory() as root:
            guard,ledger,rollout=self.fixture(root)
            self.assertIsNone(guard.check(boottime=11))
            with rollout.open('a') as stream:
                stream.write(json.dumps(dict(type='event_msg',timestamp='1970-01-01T00:01:41Z',
                    payload=dict(type='token_count',info=dict(total_token_usage=dict(
                        total_tokens=35,input_tokens=30,cached_input_tokens=15,output_tokens=5)))))+'\n')
                stream.write(json.dumps(dict(type='event_msg',payload=dict(type='turn_aborted',
                    turn_id='failed-native-turn')))+'\n')
            self.assertIsNone(guard.check(boottime=12))
            view=ledger.inspect(now=102)
            self.assertEqual(view['tokens_used'],35)
            self.assertEqual(view['actors']['worker']['used'],35)

    def test_aggregate_rollout_capacity_fences_before_scanning_large_valid_files(self):
        import json
        with tempfile.TemporaryDirectory() as root:
            guard,_,rollout=self.fixture(root)
            padding=json.dumps(dict(type='padding',payload='x'*(17*1024*1024)))+'\n'
            rollout.write_text(rollout.read_text()+padding)
            (rollout.parent/'second.jsonl').write_text(json.dumps(dict(type='session_meta',
                payload=dict(id='not-yet-attributed')))+'\n'+padding)
            self.assertEqual(guard.check(boottime=11),'accounting_capacity_exceeded')

    def test_guard_executable_readback_separates_ledger_poll_from_native_usage_observation(self):
        import json,subprocess,sys,time,os
        with tempfile.TemporaryDirectory() as root:
            guard,_,_=self.fixture(root)
            now=time.clock_gettime(time.CLOCK_BOOTTIME)
            heartbeat=Path(root)/'lifecycle/supervision.json'
            value=json.loads(heartbeat.read_text());value['observed_boottime']=now
            heartbeat.write_text(json.dumps(value))
            cfg=guard.config | dict(started_boottime=now,generation='readback-fixture',argv=['/bin/sleep','.5'])
            source=Path(root)/'guard.json';source.write_text(json.dumps(cfg))
            environment=dict(os.environ);environment.pop('INVOCATION_ID',None)
            result=subprocess.run([sys.executable,'-m','codex_wake.strict_executor',str(source)],
                env=environment,capture_output=True,text=True,timeout=3)
            self.assertEqual(result.returncode,5,result.stderr)
            status=json.loads((Path(root)/'status.json').read_text())
            self.assertEqual(status['reason'],'executor_exited')
            accounting=status['accounting'];actor=accounting['actors']['worker']
            self.assertEqual(accounting['tokens_used'],20)
            self.assertEqual(actor['native_total_tokens'],20)
            self.assertEqual(actor['native_published_epoch'],100)
            self.assertGreater(accounting['last_verified_boottime'],actor['first_observed_boottime'])
            self.assertGreater(actor['lease_age_seconds'],0)
            self.assertIsNone(accounting['publication_delay_seconds'])
            self.assertIsNone(accounting['maximum_token_overshoot'])

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
                self.assertIsNone(guard.check(boottime=11))
                self.assertLess(time.monotonic()-started, .2)
                import json
                heartbeat=Path(root)/'lifecycle/supervision.json'
                value=json.loads(heartbeat.read_text());value['observed_boottime']=16
                heartbeat.write_text(json.dumps(value))
                self.assertEqual(guard.check(boottime=16), 'accounting_unavailable')

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

    def test_later_admission_gets_only_its_own_first_snapshot_lease(self):
        import json
        with tempfile.TemporaryDirectory() as root:
            guard, ledger, rollout = self.fixture(root)
            ledger.record('worker', 20, settled=True, now=100)
            heartbeat = Path(root)/'lifecycle/supervision.json'
            def check(elapsed):
                value=json.loads(heartbeat.read_text())
                value.update(observed_boottime=10+elapsed)
                heartbeat.write_text(json.dumps(value))
                return guard.check(boottime=10+elapsed)
            self.assertIsNone(check(1))
            self.assertIsNone(check(45))
            self.assertTrue(ledger.reserve('next-worker', 100, 40, now=145)['admitted'])
            # Admission is visible before thread receipt or first usage exists.
            self.assertIsNone(check(46))
            receipt=json.loads((Path(root)/'lifecycle/spawn.json').read_text())
            receipt.update(thread_id='next-thread',budget_actor='next-worker')
            receipt['intent']['budget_inherited']='next-worker'
            (Path(root)/'lifecycle/next.json').write_text(json.dumps(receipt))
            self.assertIsNone(check(47))
            target=Path(root)/'sessions/next.jsonl'
            target.write_text(rollout.read_text().replace('owned-thread','next-thread')
                .replace('"total_tokens": 20','"total_tokens": 7'))
            self.assertIsNone(check(48))
            self.assertEqual(ledger.inspect(now=148)['tokens_used'],27)
            # Its first snapshot cannot start a fresh grace at observation48.
            self.assertEqual(check(52),'accounting_stale')

    def test_later_unbound_admission_without_snapshot_expires(self):
        import json
        with tempfile.TemporaryDirectory() as root:
            guard, ledger, _ = self.fixture(root)
            ledger.record('worker',20,settled=True,now=100)
            heartbeat=Path(root)/'lifecycle/supervision.json'
            def check(elapsed):
                value=json.loads(heartbeat.read_text());value['observed_boottime']=10+elapsed
                heartbeat.write_text(json.dumps(value))
                return guard.check(boottime=10+elapsed)
            self.assertIsNone(check(1))
            self.assertTrue(ledger.reserve('unbound-worker',100,40,now=145)['admitted'])
            self.assertIsNone(check(45))
            self.assertEqual(check(51),'accounting_missing')

    def test_first_native_null_counter_gets_only_the_reserved_startup_grace(self):
        import json
        with tempfile.TemporaryDirectory() as root:
            guard,ledger,rollout=self.fixture(root)
            rows=rollout.read_text().splitlines();row=json.loads(rows[1]);row['payload']['info']=None
            rollout.write_text(rows[0]+'\n'+json.dumps(row)+'\n')
            ledger.record('worker',None,now=100)
            self.assertIsNone(guard.check(boottime=11))
            self.assertFalse(ledger.inspect(now=101)['accounting_known'])
            heartbeat=Path(root)/'lifecycle/supervision.json';value=json.loads(heartbeat.read_text())
            value['observed_boottime']=16;heartbeat.write_text(json.dumps(value))
            self.assertEqual(guard.check(boottime=16),'accounting_missing')

    def test_resident_monitor_does_not_interrupt_strict_reservation_before_first_usage(self):
        import json
        from unittest.mock import patch
        from codex_wake.lifecycle_supervision import poll_spawns
        with tempfile.TemporaryDirectory() as root:
            guard,ledger,rollout=self.fixture(root)
            rows=rollout.read_text().splitlines();row=json.loads(rows[1]);row['payload']['info']=None
            rollout.write_text(rows[0]+'\n'+json.dumps(row)+'\n')
            path=Path(root)/'lifecycle/spawn.json';receipt=json.loads(path.read_text())
            receipt.update(submission_id='assignment',objective_budget={'accounting_known':True})
            receipt['intent'].update(objective_ref='bootstrap')
            receipt['intent']['continuation'].update(approval='operator')
            receipt['intent']['launch'].update(codex_path='/bin/true',timeout=1)
            path.write_text(json.dumps(receipt));interrupts=[]
            native=dict(id='owned-thread',path=str(rollout),turns=[dict(id='turn',status='inProgress',
                items=[dict(type='userMessage',clientId='assignment')])])
            def request(endpoint,codex,method,params,timeout):
                if method=='thread/read':return {'thread':native}
                if method=='turn/interrupt':interrupts.append(params);return {}
                raise AssertionError(method)
            with patch('codex_wake.native_protocol.native_request',side_effect=request),patch(
                    'codex_wake.lifecycle_budget.trusted_upper',return_value=101),patch(
                    'codex_wake.lifecycle_supervision.trusted_upper',return_value=101):
                poll_spawns(root)
            self.assertEqual(interrupts,[],path.read_text())
            self.assertFalse(ledger.inspect(now=101)['accounting_known'])
