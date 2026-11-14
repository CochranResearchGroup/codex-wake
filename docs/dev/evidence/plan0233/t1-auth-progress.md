# P233 T1 authentication progress

Ticket #629 remains OPEN. This is a partial implementation, not account or
inference acceptance.

The official credential file can be inspected through sanitized public status.
A private command-auth bearer path uses the configured StableTime service and
conservative expiry bound, takes the persistent native advisory lock without
breaking a holder, checks its inode/device, and rereads the credential file.
Expired, missing-expiry, ambiguous, insecure and missing sessions hold. API keys
are not adopted implicitly. No native credentials or live provider calls were
used for this progress check.

Focused local checks at this slice:

- `PYTHONPATH=src python -m unittest discover -s tests -p test_grok_provider_auth.py`
  initially RED: new public module absent. Then GREEN: two tests.
- `PYTHONPATH=src /home/ecochran76/workspace.local/codex-wake/.venv/bin/python -m unittest discover -s tests -p test_grok_provider_auth.py`
  GREEN, two tests.
- Same interpreter and PYTHONPATH, `-m codex_wake grok auth --help`: PASS.

The default shell interpreter lacks websockets; initial CLI invocation failed
before parser construction. The existing project virtual environment provides
the declared dependencies. `uv` is not on this shell's PATH. These failures were
not product passes and were not erased by the corrected environment check.

Remaining T1 acceptance: registered account binding, official login initiation,
qualified native refresh/rotation interoperability, public generated controls,
and operational readiness. Entitlement and inference remain unverified.
