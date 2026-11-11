"""Read-only inventory of explicit Wake service and root configuration.

This command never evaluates wake predicates or reads record/prompt bodies.
Systemd counters cover service cgroups, not all Wake-related host processes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
from typing import Any


PROPERTIES = (
    'Id', 'ActiveState', 'UnitFileState', 'MainPID', 'CPUUsageNSec',
    'MemoryCurrent', 'NRestarts', 'WorkingDirectory', 'ConditionResult', 'ExecStart',
    'InvocationID',
)


class AuditError(Exception):
    """The inventory could not be established; absence must not look healthy."""


def _systemctl(*args: str) -> str:
    result = subprocess.run(['systemctl', '--user', *args, '--no-pager'],
                            capture_output=True, text=True, timeout=10)
    if result.returncode:
        # Do not echo command output: unit arguments may contain credentials.
        raise AuditError(f'systemctl {args[0]} failed (exit {result.returncode}); user service inventory is unavailable')
    return result.stdout


def _argument(command: str, name: str) -> str | None:
    match = re.search(r'argv\[\]=(.*?)(?: ; [a-z_]+=|\s*}\s*$)', command)
    if not match or '\\' in match.group(1):
        return None
    try:
        words = shlex.split(match.group(1))
    except ValueError:
        return None
    option = '--' + name
    for index, word in enumerate(words):
        if word.startswith(option + '='):
            return word[len(option) + 1:]
        if word == option and index + 1 < len(words):
            return words[index + 1]
    return None


def _canonical(value: str | None, base: str | None = None) -> str | None:
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute() and base:
        path = Path(base) / path
    return str(path.resolve())


def _default_registry() -> Path:
    return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home()/'.config'))) / 'codex-wake' / 'roots.d'


def _role(unit: str, command: str) -> str:
    if 'supervisor' in unit or ' supervisor run' in command:
        return 'supervisor'
    if 'github-webhook' in unit:
        return 'webhook-listener'
    if 'shared-refresh' in unit:
        return 'refresh-worker'
    if 'controller' in unit:
        return 'controller'
    if re.search(r'(?:/|\s|=)codex-waked(?:\s|;)' , command):
        return 'repository-monitor'
    return 'other'


def _number(value: str | None) -> int | None:
    try:
        parsed = int(value or '')
    except ValueError:
        return None
    # systemd uses uint64 max and [not set] for unavailable accounting.
    return parsed if 0 <= parsed < 2**64 - 1 else None


def inventory(registry_dir: Path) -> dict[str, Any]:
    """Inspect only service properties, explicit registration metadata and paths."""
    definitions: dict[str, str] = {}
    for line in _systemctl('list-unit-files', 'codex-wake*.service', '--type=service', '--no-legend').splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].startswith('codex-wake') and parts[0].endswith('.service'):
            definitions[parts[0]] = parts[1]
    names = set(definitions)
    for line in _systemctl('list-units', 'codex-wake*.service', '--type=service', '--all', '--plain', '--no-legend').splitlines():
        parts = line.split()
        if parts and parts[0].startswith('codex-wake') and parts[0].endswith('.service'):
            names.add(parts[0])
    raw = _systemctl('show', *sorted(names), '--property=' + ','.join(PROPERTIES)) if names else ''
    services = []
    registry = _canonical(str(registry_dir))
    for block in re.split(r'\n\s*\n', raw.strip()):
        props = dict(line.split('=', 1) for line in block.splitlines() if '=' in line)
        unit = props.get('Id', '')
        if unit not in names:
            continue
        command = props.get('ExecStart', '')
        role = _role(unit, command)
        workdir = props.get('WorkingDirectory', '').removeprefix('-') or None
        root = _canonical(_argument(command, 'wake-root'), workdir or str(Path.home()))
        active = props.get('ActiveState', 'unknown')
        state = props.get('UnitFileState') or definitions.get(unit, 'unknown')
        masked = state in ('masked', 'masked-runtime')
        missing_workdir = workdir is not None and not Path(workdir).expanduser().is_dir()
        classifications = []
        if masked:
            classifications.append('preserve_mask')
        if active != 'active':
            classifications.append('inactive_definition' if unit in definitions else 'inactive_loaded_unit')
        if missing_workdir:
            classifications.append('missing_working_directory_review_references')
        if props.get('ConditionResult') == 'no':
            classifications.append('condition_skipped')
        services.append({
            'unit': unit, 'role': role, 'active': active, 'enabled': state,
            'definition': unit in definitions, 'masked': masked,
            'pid': _number(props.get('MainPID')), 'restarts': _number(props.get('NRestarts')),
            'invocation_id': props.get('InvocationID') or None,
            'cpu_usage_nsec': _number(props.get('CPUUsageNSec')),
            'memory_bytes': _number(props.get('MemoryCurrent')),
            'working_directory': workdir,
            'working_directory_exists': None if workdir is None else not missing_workdir,
            'condition_result': props.get('ConditionResult', 'unknown'),
            'wake_root': root, 'wake_root_exists': None if root is None else Path(root).is_dir(),
            'interval': _argument(command, 'interval'),
            'registry_dir': (_canonical(_argument(command, 'registry-dir'), workdir or str(Path.home())) or _canonical(str(_default_registry()))) if role == 'supervisor' else None,
            'classification': classifications,
        })
    warnings = []
    missing = names - {row['unit'] for row in services}
    if missing:
        warnings.append(f'{len(missing)} listed service(s) had unavailable properties; counts and overlap may be incomplete')
    entries = []
    paths = sorted(registry_dir.expanduser().glob('*.json'))
    if len(paths) > 512:
        warnings.append('Registry exceeds 512-entry audit bound; overlap analysis is incomplete')
    for path in paths[:512]:
        try:
            if path.is_symlink() or path.stat().st_size > 262144:
                raise ValueError('registration exceeds safe read boundary')
            entry = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(entry, dict) or not isinstance(entry.get('wake_root'), str) or not entry['wake_root']:
                raise ValueError('invalid registration')
            entries.append({'root_id': entry.get('root_id', path.stem), 'wake_root': _canonical(entry['wake_root']),
                            'enabled': entry.get('enabled') is True, 'interval': entry.get('interval')})
        except (OSError, ValueError):
            warnings.append(f'Unreadable or malformed registration: {path.name}')
    owners: dict[str, list[str]] = {}
    for service in services:
        if service['active'] != 'active':
            continue
        if service['role'] == 'repository-monitor' and service['wake_root']:
            owners.setdefault(service['wake_root'], []).append(service['unit'])
        if service['role'] == 'supervisor' and service['registry_dir'] == registry:
            for entry in entries:
                if entry['enabled']:
                    owners.setdefault(entry['wake_root'], []).append(service['unit'] + ':' + str(entry['root_id']))
    return {
        'schema_version': 1,
        'observed_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'user systemd codex-wake*.service cgroups and selected explicit root registry; excludes standalone native/MCP processes',
        'registry_dir': registry,
        'summary': {'definitions': len(definitions), 'loaded_or_defined': len(services),
                    'active': sum(row['active'] == 'active' for row in services),
                    'enabled': sum(row['enabled'] in ('enabled', 'enabled-runtime') for row in services)},
        'services': sorted(services, key=lambda row: row['unit']),
        'roots': entries,
        'configured_overlap': [{'wake_root': root, 'owners': configured} for root, configured in sorted(owners.items()) if len(configured) > 1],
        'warnings': warnings,
        'limitations': ['Overlap is configuration evidence, not proof of duplicate delivery.',
                        'Missing working directories require reference/ownership review; retained wake roots are not deletion candidates.',
                        'ExecStart option extraction uses systemctl argv rendering; ambiguous/unavailable roots remain unclassified.'],
    }


def sample_resources(before: dict[str, Any], after: dict[str, Any], elapsed_seconds: float) -> dict[str, Any]:
    """Compare declared service-cgroup snapshots without treating missing data as zero."""
    if not math.isfinite(elapsed_seconds) or elapsed_seconds <= 0:
        raise ValueError('resource sample requires positive finite elapsed time')
    previous = {row['unit']: row for row in before['services']}
    current = {row['unit']: row for row in after['services']}
    rows = []
    for unit in sorted(set(previous) | set(current)):
        first = previous.get(unit)
        last = current.get(unit)
        if not ((first and first['active'] == 'active') or (last and last['active'] == 'active')):
            continue
        cpu = None
        status = 'unavailable'
        if not first or not last or first['active'] != 'active' or last['active'] != 'active':
            status = 'activity_changed'
        elif (first.get('pid') != last.get('pid') or first.get('restarts') != last.get('restarts')
              or first.get('invocation_id') != last.get('invocation_id')):
            status = 'process_changed'
        elif first.get('cpu_usage_nsec') is not None and last.get('cpu_usage_nsec') is not None:
            delta = last['cpu_usage_nsec'] - first['cpu_usage_nsec']
            if delta < 0:
                status = 'counter_reset'
            else:
                cpu = 100.0 * delta / (elapsed_seconds * 1_000_000_000)
                status = 'measured'
        memory = last.get('memory_bytes') if last and last['active'] == 'active' else None
        rows.append({'unit': unit, 'cpu_percent_one_core': cpu, 'cpu_status': status,
                     'memory_bytes': memory, 'memory_status': 'measured' if memory is not None else 'unavailable'})
    return {
        'elapsed_seconds': elapsed_seconds,
        'scope': 'listed user-service cgroups, including their children; excludes standalone native/MCP processes',
        'services': rows,
        'totals': {
            'cpu_percent_one_core_observed': sum(row['cpu_percent_one_core'] for row in rows if row['cpu_percent_one_core'] is not None),
            'cpu_complete': all(row['cpu_status'] == 'measured' for row in rows),
            'memory_bytes_observed': sum(row['memory_bytes'] for row in rows if row['memory_bytes'] is not None),
            'memory_complete': all(row['memory_bytes'] is not None for row in rows),
            'active_during_sample': len(rows),
        },
        'limitations': ['Short snapshot, not a long-term average or idle baseline.',
                        'Totals include measured values only; incomplete accounting is explicitly flagged.'],
    }


def _render(result: dict[str, Any]) -> str:
    counts = result['summary']
    lines = [f"{counts['definitions']} service definitions; {counts['active']} active; {counts['enabled']} enabled.",
             'UNIT  STATE  ROLE  NOTES']
    for row in result['services']:
        lines.append(f"{row['unit']}  {row['active']}  {row['role']}  {', '.join(row['classification']) or '—'}")
    overlaps = result['configured_overlap']
    lines.append(f'Configured polling overlap: {len(overlaps)} root(s). This does not prove duplicate delivery.')
    for row in overlaps:
        lines.append(f"  {row['wake_root']}: {', '.join(row['owners'])}")
    if 'resource_sample' in result:
        sample = result['resource_sample']
        total = sample['totals']
        lines.append(f"Resource sample: {sample['elapsed_seconds']:.3f}s; "
                     f"{total['cpu_percent_one_core_observed']:.2f}% of one CPU core observed; "
                     f"{total['memory_bytes_observed'] / 1048576:.2f} MiB observed.")
        lines.append(f"Accounting complete: CPU={total['cpu_complete']}, memory={total['memory_complete']}. Service cgroups only.")
        for row in sample['services']:
            cpu = 'unknown (' + row['cpu_status'] + ')' if row['cpu_percent_one_core'] is None else f"{row['cpu_percent_one_core']:.2f}%"
            memory = 'unknown' if row['memory_bytes'] is None else f"{row['memory_bytes'] / 1048576:.2f} MiB"
            lines.append(f"  {row['unit']}: {cpu}; {memory}")
        lines.append('Short snapshot; not a long-term average or idle baseline.')
    lines.append('Missing paths require reference review; preserve retained wake roots and masks.')
    lines.extend('Warning: ' + warning for warning in result['warnings'])
    return '\n'.join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry-dir', type=Path,
                        default=_default_registry())
    parser.add_argument('--json', action='store_true', dest='as_json')
    parser.add_argument('--sample-seconds', type=float, default=None, help='optional read-only cgroup sample, greater than zero and at most 60 seconds')
    args = parser.parse_args(argv)
    if args.sample_seconds is not None and (not math.isfinite(args.sample_seconds) or not 0 < args.sample_seconds <= 60):
        parser.error('--sample-seconds must be finite, greater than zero and at most 60')
    try:
        result = inventory(args.registry_dir)
        if args.sample_seconds is not None:
            started = time.monotonic()
            time.sleep(args.sample_seconds)
            final = inventory(args.registry_dir)
            elapsed = time.monotonic() - started
            final['resource_sample'] = sample_resources(result, final, elapsed)
            result = final
    except (AuditError, OSError, subprocess.TimeoutExpired) as exc:
        message = str(exc) if isinstance(exc, AuditError) else 'Service inventory unavailable (system command or filesystem error)'
        print(json.dumps({'error': message}) if args.as_json else 'Error: ' + message, file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True) if args.as_json else _render(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
