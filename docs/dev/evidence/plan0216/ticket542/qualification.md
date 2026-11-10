# Ticket 542 native passive feed qualification

Source branch: `feat/observer-native-542`, base `5de58e5`.
Scope: new NativeStatusFeed adapter and its public-protocol tests only. No live
Codex endpoints, provider calls, client ownership, deployment, or production
formatting were changed.

The adapter keeps one bounded WebSocket connection to an existing owned Unix
socket. Socket ownership, SO_PEERCRED UID, peer PID birth/boot identity, physical
socket identity and locator target are checked. Initial metadata permits only
initialize, initialized notification, loaded-thread listing and history-excluding
thread reads. Status broadcasts are the only accepted update event. No server
approval/input request is answered. Metadata and status are explicitly allowlisted;
thread turns, preview text and unrelated notifications never enter events.

Disconnect/protocol/identity failures discard an incomplete batch and emit
unavailable. Reconnect is exponentially backed off, creates a new epoch, and emits
a complete bounded baseline before updates. Bootstrap has a whole-operation
monotonic timeout; population, frame, transport queue and event batch sizes are
bounded. Closed feeds never reconnect. The only close target is the owned client
connection. A reliable ordered WebSocket supplies ordering within a connection;
there is no invented upstream sequence or claim to detect silent server-side loss.

## Focused checks

- Initial red: `PYTHONPATH=src /tmp/wake542-py312/bin/python -m unittest discover -s tests -p test_tab_native_feed.py` failed with missing `codex_wake.tab_native_feed` before implementation. Earlier environment failures (missing stale virtualenv, then missing websockets) were setup failures and are not behavior reds.
- Green Python 3.11.15: `PYTHONPATH=src /tmp/wake216-py311/bin/python -m unittest discover -s tests -p test_tab_native_feed.py`; three tests, zero failures/errors.
- Green Python 3.12.13: equivalent `/tmp/wake216-py312/bin/python`; three tests, zero failures/errors.
- `ruff check --select F821,F822,F823` on the two new Python files and `git diff --check` passed.
- Machine-readable focused receipts in `python311.json` and `python312.json` record measured 100-event burst p95, test count and elapsed time. These are real private Unix WebSocket fixture measurements, not installed-host acceptance.

Coverage includes content allowlisting, rejected different-UID boundary before
initialization, passive update, unanswered server approval request, ordering,
disconnect/backoff/new-epoch baseline, 100-event burst latency, malformed status
invalidation without content retention, bounded non-socket failure and owned close.

## Boundaries and remaining integration

The public-host index supplied structural discovery; this isolated worktree has
no CodeGraph index. Existing SharedAppServerReader was inspected but unchanged.
The historical qualification virtualenvs no longer existed following reboot;
new shared 3.11/3.12 environments were created with project MCP/dev dependencies.

This ticket proves the adapter and private protocol behavior. Ticket 544 owns
persistent lifecycle/scheduler integration and unknown-thread fallback binding;
ticket 547 owns exact installed surfaces, host observation and resource gates.
No claim is made here about installed native broadcast availability or end-to-end
public projection latency. Root closes the issue only after integration checks.

Memory disposition: forbidden; no explicit memory-write request exists, and
higher-priority memory instructions require one. No memory write attempted.
