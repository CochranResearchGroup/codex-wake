# Session discovery qualification

State: ACCEPTED_LOCAL_PENDING_HOSTED
Plan: 0100 / P62, dependency of Plan 0101 / P63
Work item: https://github.com/CochranResearchGroup/codex-wake/issues/181

## Evidence and limits

The installed CLI queried the existing Codex 0.160.0 daemon through its supported
read-only `app-server daemon version` locator. Qualified tab selectors 17:wake
and 7:mail-receipts resolved to distinct exact identities; the duplicate name
mapocock failed ambiguous. These metadata reads caused no lifecycle operation.

The actual tool environment inherits TMUX_PANE=%1 from the daemon launcher.
Current-thread validation rejected this conflicting pane instead of attaching
it to the invoking thread. Identity enrollment must preserve that distinction;
metadata match is not runtime attestation.

Installed provider-free Unix WebSocket smoke exercised all five verbs, root
filtering, bounded pinned watch, and unsupported attestation. Eighteen client
connections all closed. Captured methods were initialize (18), initialized (18),
thread/loaded/list (18), and thread/read (36); includeTurns was always false.
Private preview/transcript fixture fields never appeared in CLI output. Ten
sequential reads in one installed client process retained five descriptors and
one thread before and after. The fixture server's descriptor lifetime is not
the client resource measurement. No existing runtime was restarted.

Commands: installed `scripts/session_discovery_smoke.py --cli .../codex-wake`;
focused `test_sessions.py`, `test_shared_app_server.py`, `test_cli.py`; full
`PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'`.
Comprehensive run passed 740 tests in 33.667 seconds, with no retries, before
the final invalid-selector/timeout tests. Latest focused session run: 16 pass;
shared reader: 10 pass. New smoke is included in the hosted installed-wheel gate.
Planning audit reports ok; diff whitespace check passes.

Read-only method restrictions, pagination failures, exact metadata collision,
headless selection, source loss, unknown/unloaded provider state, parent-pane
conflict, process reuse, and watch replacement are deterministic fixture risks.
Default locator supports owned Codex control symlinks; arbitrary explicit
symlinks are rejected. Exact headless identity requires the daemon source;
optional missing tmux remains visible, while tab selection requires both.

Hosted CI and canonical integration remain pending. No mailbox, delivery,
production enrollment, installed service change, or release is claimed.
