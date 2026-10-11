# Plan0153 — Standalone source and installed fixture acceptance

Verdict: accepted for source integration and isolated installed consumer behavior.
Production activation, issue closure and Matt configuration are not asserted.

Original installed0.13.0-stable-time-01 reproduction used the real CLI entrypoint,
an isolated root and an explicitly injected unavailable acquisition: exit2,
zero records. The actual incident's error magnitude remains unknown. No failed
production wake was replayed.

Final standalone0.13.1 source passed1063 standard-library tests in104.487s with
declared dependencies installed. First broad run preserved17 missing-WebSocket
environment errors and two obsolete schema-version assertions; assertions were
updated and the proper environment passed. A subsequent source regression and
compatible-monitor option passed the final complete run. No flake/retry claim.
Policy wiring, compile checks and active planning audit pass; the latter carries
20 explicitly accepted historical baseline findings. Hosted CI waiting waived.

Commands:

```sh
CODEX_WAKE_STABLE_TIME_CONFIG='' PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
python scripts/check_policy_wiring.py
python -m compileall -q src tests scripts/native_intent_qualification.py
python .codex/skills/repo-policy-selector/scripts/audit_planning_contract.py --repo-root . --active-only --json
uv build --wheel
python scripts/native_intent_qualification.py --prefix ISOLATED_PREFIX --legacy-python PREVIOUS_PREFIX/bin/python --receipt PRIVATE_RECEIPT
```

Installed fixture acceptance: two concurrent creators retained one original ID.
Six fresh worker processes prove outage hold, counter recovery, no duplicate
successor, live schema6 capability and owned loop shutdown. The monitoring chain
produced exactlyone fixture successor. A separate request accepted once before
its worker was killed ahead of acceptance publication; its fresh worker retained
the durable uncertain nonce, attempts1, and did not resend during clock outage.
The previous installed worker held schema6 byte-for-byte without dispatch.
No global install changes, production roots/turns, notifications or test tabs.
Derived worker state uses isolated XDG directories and owned processes are stopped.

Wheel-source parity:85 package files match source, no private StableTime overlay.
Wheel SHA2563571d93eed09e1c38bade319669ad33f17bd890983345c8a44614bad412096a0.
See wheel-source-parity.json and installed-fixture.json for bounded readbacks.
Readiness/queue fixtures are injected boundaries, not completed native model turns.

Activation gate: publishing/deploying the root's retained StableTime adapter is
outside its Plan0152 no-commit/push scope. A clean0.13.1 install would otherwise
remove that private adapter for other consumers. Preserve it and obtain a scoped
publication decision before a global release/worker upgrade. Matt setup draft
also awaits the required default-label preference and draft confirmation.
