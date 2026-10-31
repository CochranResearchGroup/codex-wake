"""Run repository check tiers through the source-bound candidate runner."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--profile', type=Path, default=Path(__file__).with_name('local_validation_profile.json'))
    parser.add_argument('--tier', choices=['focused', 'presubmit', 'comprehensive'], default='presubmit')
    parser.add_argument('--timeout', type=float, default=300)
    args = parser.parse_args()
    repo, receipt = args.repo.resolve(), args.receipt.resolve()
    if receipt.is_relative_to(repo) or receipt.exists():
        parser.error('receipt must be new and outside candidate')
    profile = args.profile.resolve()
    try:
        selection = json.loads(profile.read_text())['tiers'][args.tier]
        with tempfile.TemporaryDirectory(prefix='wake-validation-', dir=receipt.parent) as temp:
            state = Path(temp)
            env = {key: os.environ[key] for key in ('PATH', 'LANG', 'LC_ALL', 'SYSTEMROOT') if key in os.environ}
            for key in ('HOME', 'XDG_CONFIG_HOME', 'XDG_STATE_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'XDG_RUNTIME_DIR', 'CODEX_HOME', 'TMPDIR', 'PYTHONPYCACHEPREFIX'):
                directory = state / key.lower()
                directory.mkdir(mode=0o700)
                env[key] = str(directory)
            env.update(PYTHONPATH=str(repo / 'src'), PYTHONDONTWRITEBYTECODE='1', CODEX_WAKE_STABLE_TIME_CONFIG='')
            checks = []
            for row in selection:
                checks.append({**row, 'argv': [part.replace('{artifacts}', str(state / 'artifacts')) for part in row['argv']]})
            manifest = state / 'manifest.json'
            manifest.write_text(json.dumps(dict(checks=checks, on_success=[], runtime_files=[str(profile)],
                                                profile=dict(path=str(profile), tier=args.tier,
                                                             hosted_differences=['local selected Python; no hosted Actions', 'no OpenClaw/plugin, provider, installed-wheel or live acceptance', 'external build snapshot; no dependency downloads during checks']))))
            return subprocess.run([sys.executable, str(Path(__file__).with_name('validate_candidate.py')),
                                   '--repo', str(repo), '--runtime', str(args.runtime.absolute()),
                                   '--manifest', str(manifest), '--receipt', str(receipt),
                                   '--timeout', str(args.timeout)], env=env).returncode
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'local validation setup: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
