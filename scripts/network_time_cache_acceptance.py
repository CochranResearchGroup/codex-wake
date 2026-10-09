"""Opt-in Windows collector cache controls in owned temporary host state."""
import argparse
import base64
import json
from pathlib import Path
import subprocess

from codex_wake.time_inspection import POWERSHELL


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).parents[1].joinpath('src/codex_wake/time_collect.ps1').read_text()
    reports = []
    for fault in ('corruption', 'frequency_changed', 'counter_regressed'):
        prefix = r'''
$probeRoot = Join-Path ([IO.Path]::GetTempPath()) ([Guid]::NewGuid().ToString())
$env:LOCALAPPDATA = $probeRoot
$probeCache = Join-Path $probeRoot 'codex-wake\time-inspection'
[IO.Directory]::CreateDirectory($probeCache) | Out-Null
$probePath = Join-Path $probeCache 'cache.json'
'''
        if fault == 'corruption':
            prefix += "[IO.File]::WriteAllText($probePath, '{malformed')\n"
        else:
            prefix += r'''
$probeBoot = (Get-CimInstance Win32_OperatingSystem -OperationTimeoutSec 3).LastBootUpTime.ToUniversalTime().Ticks.ToString()
$probeFrequency = [Diagnostics.Stopwatch]::Frequency
$probeAttempt = [Diagnostics.Stopwatch]::GetTimestamp()
'''
            prefix += ('$probeFrequency += 1\n' if fault == 'frequency_changed' else '$probeAttempt += $probeFrequency * 1000\n')
            prefix += "[IO.File]::WriteAllText($probePath, (@{host_boot=$probeBoot;frequency=$probeFrequency;attempt=$probeAttempt;generation='fixture';guest_boot='fixture';replies=@()} | ConvertTo-Json -Compress))\n"
        script = prefix + '\ntry {\n' + source + '\n} finally { Remove-Item -LiteralPath $probeRoot -Recurse -Force }'
        completed = subprocess.run([POWERSHELL, '-NoProfile', '-NonInteractive', '-EncodedCommand',
                                   base64.b64encode(script.encode('utf-16-le')).decode()],
                                  input=json.dumps(dict(hosts=['time.cloudflare.com','time.nist.gov'],request_id=fault,guest_boot='fixture')),
                                  text=True,capture_output=True,timeout=25)
        if fault == 'corruption':
            assert completed.returncode == 0, completed.stderr
            report = json.loads(completed.stdout.lstrip('\ufeff'))
            assert all(r['error'] == 'cache_invalid_backoff' for r in report['replies']), report
            reports.append(dict(fault=fault,status='passed',observation=report))
        else:
            assert completed.returncode != 0 and 'elapsed_authority_changed' in completed.stderr, completed.stdout+completed.stderr
            reports.append(dict(fault=fault,status='passed',exit_code=completed.returncode,error='elapsed_authority_changed'))
    args.output.write_text(json.dumps(dict(status='passed',network_acquisitions=0,controls=reports),indent=2)+'\n')
    print('Three owned Windows cache controls passed; no network acquisition')


if __name__ == '__main__':
    main()
