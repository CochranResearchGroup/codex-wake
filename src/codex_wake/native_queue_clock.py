"""Host-owned Stable Time reader for native bounded queue admission.

Invoke as an absolute pinned interpreter/module pair with an explicit config.
This process is independent of the Wake watcher and never accepts sender time.
Native must bound process execution and account for elapsed time after sampling.
"""
import argparse
import json
import math
import os
from pathlib import Path

from .native_clock import snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    held = dict(contract_version=1, state='held', reason='stable_time_unavailable')
    if not args.config.is_absolute():
        print(json.dumps(held))
        return 0
    # A required nonempty override prevents snapshot's optional NTP fallback.
    os.environ['CODEX_WAKE_STABLE_TIME_CONFIG'] = str(args.config)
    value = snapshot()
    utc, counter = value.get('utc'), value.get('counter')
    if (not isinstance(utc, dict) or utc.get('status') != 'network'
            or not isinstance(counter, dict) or value.get('reason') != 'authenticated_utc'
            or any(type(utc.get(k)) not in (int, float) or not math.isfinite(utc[k])
                   for k in ('lower', 'upper'))
            or utc['lower'] > utc['upper']):
        print(json.dumps(held))
        return 0
    print(json.dumps(dict(contract_version=1, state='qualified',
                         lower=utc['lower'], upper=utc['upper'], counter=counter)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
