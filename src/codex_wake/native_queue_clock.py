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
from .host_counter import counter_socket


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    held = dict(contract_version=1, state='held', reason='stable_time_client_configuration_invalid')
    if not args.config.is_absolute():
        print(json.dumps(held))
        return 0
    # A required nonempty override prevents snapshot's optional NTP fallback.
    os.environ['CODEX_WAKE_STABLE_TIME_CONFIG'] = str(args.config)
    value = snapshot()
    reason = value.get('reason', '')
    held['reason'] = reason if reason.startswith('stable_time_client_') or reason in (
        'stable_time_configuration_required', 'stable_time_response_invalid') else 'stable_time_utc_unqualified'
    utc, counter = value.get('utc'), value.get('counter')
    valid_for_ns = value.get('valid_for_ns')
    if (not isinstance(utc, dict) or utc.get('status') != 'network'
            or not isinstance(counter, dict) or value.get('reason') != 'authenticated_utc'
            or type(valid_for_ns) is not int or not 0 < valid_for_ns <= 300000000000
            or any(type(utc.get(k)) not in (int, float) or not math.isfinite(utc[k])
                   for k in ('lower', 'upper'))
            or utc['lower'] > utc['upper']):
        print(json.dumps(held))
        return 0
    print(json.dumps(dict(contract_version=1, state='qualified',
                         lower=math.nextafter(utc['lower'] - 0.000001, -math.inf),
                         upper=math.nextafter(utc['upper'] + 0.000001, math.inf),
                         counter=counter, valid_for_ns=valid_for_ns,
                         counter_source=dict(kind='windows_qpc_private_bridge',
                                             socket=str(counter_socket())))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
