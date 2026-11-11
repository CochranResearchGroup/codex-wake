from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class ServiceAuditCommandTests(unittest.TestCase):
    def test_resource_sample_distinguishes_valid_reset_and_missing_accounting(self):
        from codex_wake.service_audit import sample_resources
        def row(unit, cpu, pid=10, memory=1048576):
            return {'unit': unit, 'active': 'active', 'pid': pid, 'restarts': 0,
                    'invocation_id': unit + str(pid), 'cpu_usage_nsec': cpu, 'memory_bytes': memory}
        before = {'services': [row('good', 1_000_000_000), row('reset', 3_000_000_000),
                               row('missing', None), row('restart', 100)]}
        after = {'services': [row('good', 1_500_000_000), row('reset', 1_000_000_000),
                              row('missing', None, memory=None), row('restart', 200, pid=11)]}
        sample = sample_resources(before, after, 2.0)
        rows = {row['unit']: row for row in sample['services']}
        self.assertEqual(rows['good']['cpu_percent_one_core'], 25.0)
        self.assertEqual(rows['reset']['cpu_status'], 'counter_reset')
        self.assertEqual(rows['missing']['cpu_status'], 'unavailable')
        self.assertEqual(rows['restart']['cpu_status'], 'process_changed')
        self.assertIsNone(rows['restart']['cpu_percent_one_core'])
        self.assertEqual(sample['totals']['cpu_percent_one_core_observed'], 25.0)
        self.assertFalse(sample['totals']['cpu_complete'])
        self.assertFalse(sample['totals']['memory_complete'])
        self.assertEqual(sample['elapsed_seconds'], 2.0)

    def test_public_command_reports_configured_overlap_without_mutating_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / 'wake'; root.mkdir()
            registry = base / 'registry'; registry.mkdir()
            (registry / 'repo.json').write_text(json.dumps({'root_id': 'repo', 'enabled': True, 'wake_root': str(root)}))
            bindir = base / 'bin'; bindir.mkdir()
            fake = bindir / 'systemctl'
            fake.write_text('''#!/usr/bin/env python3
import sys
args=sys.argv
if 'list-unit-files' in args:
 print('codex-wake-supervisor.service enabled enabled')
 print('codex-wake-repo.service enabled enabled')
 print('codex-wake-old.service masked enabled')
elif 'list-units' in args:
 pass
elif 'show' in args:
 print('Id=codex-wake-supervisor.service\\nActiveState=active\\nUnitFileState=enabled\\nMainPID=100\\nExecStart={ argv[]=codex-wake supervisor run --interval 7 --registry-dir '+%r+' ; ignore_errors=no ; }\\n')
 print('Id=codex-wake-repo.service\\nActiveState=active\\nUnitFileState=enabled\\nMainPID=101\\nWorkingDirectory='+%r+'\\nExecStart={ argv[]=codex-waked --wake-root '+%r+' --interval 60 ; ignore_errors=no ; }\\n')
 print('Id=codex-wake-old.service\\nActiveState=inactive\\nUnitFileState=masked\\nMainPID=0\\nWorkingDirectory='+%r+'\\nConditionResult=no\\nExecStart={ argv[]=codex-waked --wake-root '+%r+' ; ignore_errors=no ; }\\n')
else:
 sys.exit(90)
''' % (str(registry), str(base/'missing'), str(root), str(base/'missing-old'), str(root)))
            fake.chmod(0o755)
            env = dict(os.environ, PATH=str(bindir)+os.pathsep+os.environ['PATH'])
            command = [sys.executable, '-m', 'codex_wake.service_audit', '--registry-dir', str(registry)]
            before = sorted(str(p.relative_to(base)) for p in base.rglob('*'))
            result = subprocess.run([*command, '--json'], text=True, capture_output=True, env=env, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data['roots'][0]['interval'], 7.0)
            self.assertEqual(data['roots'][0]['interval_source'], 'supervisor')
            self.assertEqual(data['summary']['definitions'], 3)
            self.assertEqual(data['summary']['active'], 2)
            self.assertEqual(len(data['configured_overlap']), 1)
            self.assertEqual(data['configured_overlap'][0]['wake_root'], str(root))
            self.assertEqual(len(data['configured_overlap'][0]['owners']), 2)
            old = next(row for row in data['services'] if row['unit'] == 'codex-wake-old.service')
            self.assertTrue(old['masked'])
            self.assertTrue(old['wake_root_exists'])
            self.assertFalse(old['working_directory_exists'])
            self.assertIn('preserve_mask', old['classification'])
            self.assertNotIn('"ExecStart":', result.stdout)
            human = subprocess.run(command, text=True, capture_output=True, env=env, timeout=10)
            self.assertEqual(human.returncode, 0, human.stderr)
            sampled = subprocess.run([*command, '--sample-seconds', '0.001', '--json'], text=True, capture_output=True, env=env, timeout=10)
            self.assertEqual(sampled.returncode, 0, sampled.stderr)
            sample = json.loads(sampled.stdout)['resource_sample']
            self.assertGreaterEqual(sample['elapsed_seconds'], 0.001)
            self.assertFalse(sample['totals']['cpu_complete'])
            self.assertTrue(all(row['cpu_status'] == 'unavailable' for row in sample['services']))
            invalid = subprocess.run([*command, '--sample-seconds', 'nan'], text=True, capture_output=True, env=env, timeout=10)
            self.assertEqual(invalid.returncode, 2)
            self.assertIn('3 service definitions; 2 active', human.stdout)
            self.assertIn('Configured polling overlap', human.stdout)
            self.assertNotIn('duplicate delivery occurred', human.stdout)
            self.assertEqual(before, sorted(str(p.relative_to(base)) for p in base.rglob('*')))
            entry_path = registry / 'repo.json'
            entry = json.loads(entry_path.read_text())
            entry['poll_interval'] = 60
            entry['interval'] = 999  # unrelated historical data is not the scheduler contract
            entry_path.write_text(json.dumps(entry))
            explicit = subprocess.run([*command, '--json'], text=True, capture_output=True, env=env, timeout=10)
            self.assertEqual(explicit.returncode, 0, explicit.stderr)
            explicit_root = json.loads(explicit.stdout)['roots'][0]
            self.assertEqual(explicit_root['interval'], 60.0)
            self.assertEqual(explicit_root['poll_interval'], 60)
            self.assertEqual(explicit_root['interval_source'], 'registration')
            entry.pop('poll_interval')
            entry_path.write_text(json.dumps(entry))
            # A selected registry with no corresponding service cannot establish cadence.
            unmatched = base / 'unmatched'; unmatched.mkdir()
            (unmatched / 'repo.json').write_text(json.dumps(entry))
            unknown = subprocess.run([sys.executable, '-m', 'codex_wake.service_audit', '--registry-dir', str(unmatched), '--json'], text=True, capture_output=True, env=env, timeout=10)
            self.assertEqual(unknown.returncode, 0, unknown.stderr)
            unknown_root = json.loads(unknown.stdout)['roots'][0]
            self.assertIsNone(unknown_root['interval'])
            self.assertEqual(unknown_root['interval_source'], 'unknown')


if __name__ == '__main__':
    unittest.main()
