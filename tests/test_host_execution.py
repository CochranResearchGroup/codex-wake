"""Contract tests at the systemd subprocess protocol boundary."""
import os
import time
import uuid
import subprocess
import tempfile
import unittest
from codex_wake.host_execution import SystemdExecution

LIMITS = dict(memory_max_bytes=67108864, memory_swap_max_bytes=0,
              cpu_quota_percent=50, tasks_max=16, stop_grace_seconds=1)

class Runner:
    def __init__(self): self.calls = []; self.active = False
    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        if argv[0] == 'systemd-run': self.active = True; return subprocess.CompletedProcess(argv, 0, '', '')
        if 'show' in argv:
            data = ('LoadState=loaded\nActiveState=active\nSubState=running\nInvocationID=abc123\n'
                    'ControlGroup=/user.slice/codex-wake-objective-test.service\nMainPID=123\n'
                    'MemoryMax=67108864\nMemorySwapMax=0\nCPUQuotaPerSecUSec=500ms\nTasksMax=16\n') if self.active else 'LoadState=not-found\n'
            return subprocess.CompletedProcess(argv, 0, data, '')
        return subprocess.CompletedProcess(argv, 0, '', '')

class HostExecutionTests(unittest.TestCase):
    def test_launch_binds_identity_and_independent_runtime(self):
        runner = Runner()
        with tempfile.TemporaryDirectory() as cwd:
            result = SystemdExecution(runner=runner).launch('codex-wake-objective-test.service',
                ['/bin/sleep', '3'], cwd=cwd, environment={}, limits=LIMITS, runtime_seconds=5)
        self.assertEqual(result['invocation_id'], 'abc123')
        launch = next(x for x in runner.calls if x[0] == 'systemd-run')
        self.assertIn('--property=RuntimeMaxSec=5', launch)
        self.assertIn('--property=KillMode=control-group', launch)
        self.assertIn('--property=MemorySwapMax=0', launch)

    def test_stop_refuses_reused_unit_without_effect(self):
        runner = Runner(); runner.active = True
        adapter = SystemdExecution(runner=runner)
        with self.assertRaisesRegex(RuntimeError, 'identity'):
            adapter.stop(dict(unit='codex-wake-objective-test.service', invocation_id='old',
                              control_group='/user.slice/codex-wake-objective-test.service'))
        self.assertFalse(any('stop' in command for command in runner.calls))

    def test_invalid_limits_have_no_host_effect(self):
        for updates in ({'tasks_max': True}, {'memory_max_bytes': 0}, {'cpu_quota_percent': float('nan')}):
            runner = Runner()
            with tempfile.TemporaryDirectory() as cwd, self.assertRaises(ValueError):
                SystemdExecution(runner=runner).launch('codex-wake-objective-test.service',
                    ['/bin/sleep', '1'], cwd=cwd, environment={}, limits={**LIMITS, **updates}, runtime_seconds=1)
            self.assertEqual(runner.calls, [])

    def test_existing_unit_is_never_replaced(self):
        runner = Runner(); runner.active = True
        with tempfile.TemporaryDirectory() as cwd, self.assertRaisesRegex(RuntimeError, 'already exists'):
            SystemdExecution(runner=runner).launch('codex-wake-objective-test.service', ['/bin/true'],
                cwd=cwd, environment={}, limits=LIMITS, runtime_seconds=1)
        self.assertFalse(any(c[0] == 'systemd-run' for c in runner.calls))

    def test_retired_unit_is_terminal_without_stop_effect(self):
        runner = Runner()
        identity = dict(unit='codex-wake-objective-test.service', invocation_id='old',
                        control_group='/codex-wake-objective-absent-' + uuid.uuid4().hex)
        result = SystemdExecution(runner=runner).stop(identity)
        self.assertTrue(result['identity_retired'])
        self.assertEqual(result['members'], [])
        self.assertFalse(any('stop' in command for command in runner.calls))

    @unittest.skipUnless(os.environ.get('CODEX_WAKE_HOST_EXECUTION_LIVE') == '1', 'opt-in disposable systemd test')
    def test_live_deadline_stops_service_without_controller(self):
        adapter = SystemdExecution()
        unit = 'codex-wake-objective-test-' + uuid.uuid4().hex + '.service'
        with tempfile.TemporaryDirectory() as cwd:
            identity = adapter.launch(unit, ['/bin/sleep', '9'], cwd=cwd, environment={},
                                      limits=LIMITS, runtime_seconds=1)
            try:
                running = adapter.inspect(identity)
                self.assertTrue(running['populated'])
                self.assertEqual(running['kernel_limits']['memory.max'], '67108864')
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    try:
                        state = adapter.inspect(identity)
                    except RuntimeError as exc:
                        if str(exc) != 'active executor cgroup unavailable':
                            raise
                        # Manager state and kernel cgroup removal are not atomic.
                        # Re-observe this exact invocation under the same deadline.
                        time.sleep(.05)
                        continue
                    if not state['populated']:
                        break
                    time.sleep(.05)
                self.assertFalse(state['populated'])
                self.assertEqual(state['members'], [])
            finally:
                adapter.stop(identity)
                # Only this disposable failed unit is released; no wildcard effects.
                subprocess.run(['systemctl', '--user', 'reset-failed', unit], capture_output=True)

if __name__ == '__main__': unittest.main()
