# LOCAL-P212 diagnosis and source fix

The missing capability error was real. The shared global MCP entry supplied no
actor wiring, and mailbox identity is deliberately separate from native identity.
My earlier diagnosis stopped at that boundary and left the integration absent.

## Feedback loop and root cause

Installed read-only command, already run:
`python ~/.local/state/codex-wake/a2a-setup-diagnosis/repro.py`
returned RED: native caller has no host-supplied mailbox actor capability.
Current MCP reproduced `authorization_denied` with the same exact missing-issued-
capability diagnostic. Changing only the bus to an absent path produced
store_unavailable rather than recovery. Credentials never appeared in output.

The minimized regression uses CommandRunner, a shared host operator delegation,
an already enrolled/migrated private bus and two callers. It first failed at the
unsupported new host option, then after interface plumbing at the actual original
`authorization_denied: explicit issued actor capability is required` (red.log).
One preliminary fixture lacked mailbox migration and failed at unsupported schema;
that was fixture setup, corrected before trusting the red signal.

Ranked predictions: missing host actor wiring (confirmed); fixed credential cannot
serve distinct callers (two-actor workflow protects this); bus selection alone
cannot issue authority (confirmed). The application had no automatic bridge from
approved project scope and verified native context to a participant actor.

## Fix

`codex-wake-mcp --bus-root PATH --mailbox-operator-capability FILE --app-server unix://SOCKET`
opts a host into caller-specific actor provisioning. Project root enrollment is
still the existing one-time operator action, without a --thread argument.
Workers first poll inbox to establish their actor before peers send to them.

The private host capability stays outside tool parameters/results. Native call
metadata must match the claim; exact runtime metadata supplies namespace/cwd.
The most specific existing enrolled root is selected. No root is auto-enrolled,
no revoked actor is restored, and current rotated credentials are reused. Missing
credentials fail rather than reissue. A five-second bounded cross-process lock
serializes concurrent first use. Caller-local launch context is immutable; the
shared runner's fixed capability field never changes. CLI authentication rechecks
the identity and uses the caller's verified working directory. Explicit fixed-
actor mode remains available and cannot be combined with host operator mode.

## Verification

```sh
PYTHONPATH=src:tests /tmp/codex-wake-p210-py312/bin/python -m unittest test_native_mailbox_bootstrap test_a2a_mcp test_a2a_cli test_messages_cli -q
PYTHONPATH=src:tests /tmp/codex-wake-p210-py311/bin/python -m unittest test_native_mailbox_bootstrap test_a2a_cli test_messages_cli -q
env -u PYTHONPATH /tmp/native-mailbox-bootstrap-installed/bin/python scripts/native_mailbox_bootstrap_acceptance.py --output /tmp/native-mailbox-public-installed.json
```

23PASS3.12/25.652s;21PASS3.11/15.760s. Eight new checks cover distinct/reused actors,
question/claim/correlated reply, missing/contradictory metadata, unenrolled/revoked
actors, rotation, invalid operator before native lookup, disabled enrollment and
concurrent first use. The two existing stdio checks were selected on3.12 only.
The final source/installed public fixture checks use real stdio SDK, real CLI
subprocesses and real mailbox storage; only native metadata is a private websocket
fixture. Its first attempts corrected fixture SDK TypedDict/is_error spelling;
those were not product failures. No live FigureLabs T06 acceptance is claimed.

Source freeze bd79923; wheel SHA256:
`53f2a3ef358d16bf1fee7dcb05598170e8a0631b4435313d7817340131acc3c0`.
All305 package members (303Python+2data) equal frozen source/wheel/private install.
Existing production dependency constraints reused; no dependency upgrade. Build
command: `SOURCE_DATE_EPOCH=1794261600 /tmp/wake534-builder/bin/pip wheel --no-deps --no-build-isolation --wheel-dir /tmp/native-mailbox-bootstrap-wheel .`.

Generated reference check, policy wiring, compileall, undefined-name lint and
whitespace pass. Planning audit accepts20 historical baseline findings. Local
focused tier only; no paid hosted CI, full suite or actual Windows harness run.
Private fixture state is removed by TemporaryDirectory; stdio subprocesses and
websocket worker are joined/closed. No debug instrumentation or production config
change. The prior diagnostic loop remains explicitly under user-state diagnosis.

## Delivery boundary

Source fix and private installed acceptance complete. The working MCP still uses
the prior release/config until integration and host-mode activation. No live
credentials minted, no native model prompt sent, no service changed, and no claim
that the original live setup has turned green. Preserved unrelated .codex/config.toml.
Memory disposition forbidden: no explicit memory-write request.
