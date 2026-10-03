# Plan 0109 configured receipt observer verification

Parent: Plan 0101 / issue #181
Branch: feat/p63-receipt-authority
Baseline: ff37005b0271b631c5dffa2e1c630d241761826a
Outcome: explicit configured replay and no-dispatch process restart locally accepted.

PR #188 integrated the earlier exact restore/source guard and webhook fixture
repair after Python 3.11/3.12 release gates succeeded in run 37154989267,
head e107ee39d467244def698d9336208144eced3631. The original failed hosted
run 37148747612 is retained in verification 0100.

## Contract and executable evidence

The daemon only opens receipt authority when an explicit
`--a2a-receipt-authority FILE` is supplied. Private mode-0600 nonsecret JSON
pins one wake root and at most 100 independently configured exact source,
bus, actor-generation and message grants. A referenced private operator
capability delegates observation; no fabricated runtime metadata or actor
authentication is used. Mailbox reads validate operator authority and the
still-active actor generation inside SQLite query-only transactions.
No mailbox events, receipt rows or envelopes are created by observation.

The executable tracer first failed with the authority module absent. After
implementation, six new tests cover real temporary mailbox/signal journals:
three fresh daemon processes prove opt-in required, one firing with valid
authority, and no duplicate firing after another process restart. Config
removal and actor rotation fence already-created runners with cached signal
evidence. Writes through the observer connection fail; recipient permission
is refused. Invalid generation, missing capability, missing bus, wrong exact
message, oversized/public/symlinked/malformed/duplicate-member JSON and a
copied wake-root grant fail closed. No path is opened from an arm descriptor.
Private body text is absent from output and firing metadata.

The installed executable runs with `--once --no-dispatch` only. This is
synthetic configured process proof, not a live named-agent exchange, a long
suspension, an installed service restart, or a provider operation. Generic
receipt dispatch remains held as unqualified under the previously integrated
injector guard.

## Checks

- Python 3.12.13 focused authority/receipt/daemon modules: 47 tests in 3.226s.
- Python 3.11 new authority tests: six tests in 1.360s.
- Full local Python suite: 830 tests in 40.813s, no failures or retries.
- Source/test/hook compilation and diff hygiene passed.
- Isolated wheel built: codex_wake-0.6.0-py3-none-any.whl, SHA256
  e0ff6e0e16ea4bd326b1a3ad67cf6a2a4530570739563b809afc5ca1069e8f8f.
- Installed Python 3.12 authority tests: six tests in 1.251s. Imported module
  confirmed under /tmp/codex-wake-p63-authority-venv/lib/python3.12/site-packages.
  Executable explicitly selected from that same isolated environment; source
  PYTHONPATH excluded. Initialized FD census 5 -> 5; children 0 -> 0.

No global package, user service, production mailbox, enrollment or actual live
agent identity was changed. Temporary roots were cleaned by the tests.

## Remaining boundaries

Local acceptance does not establish hosted CI, integration, actual automatic
delivery, receipt arming CLI, or long agent suspension. Those gates retain
independent evidence requirements. The active-lane catalogue's old paused
checkpoint is a stale discovery projection; Git/PR/branch-local plans establish
current primary ownership, with no competing local worktree.

Memory disposition: unavailable. No applicable authorized repository group was
established by the bounded Graphiti atlas discovery; zero Graphiti writes.

## Targeted read-only boundary repair

The first published head d28c14580e13ee5c94fdcae57fd9939fa0f3ef72 passed
both hosted gates in run 37155906994. Before integration, a stricter callback
probe disabled PRAGMA query_only and attempted a mailbox UPDATE. It went red
with `OperationalError not raised` in 0.124s: query-only alone is reversible.
This consumed the packet's one targeted repair, not a new discovery allowance.

BusStore.connection now has an optional read_only mode; its existing ownership,
sidecar, schema and canonical-root checks still apply. The observer opens the
connection with SQLite URI mode=ro as well as query_only. The same real database
write is now refused even after changing the pragma. Default actor/operator
connections keep their existing mode=rw; no schema or capability migration.

Final checks after this source change:

- Python 3.12 focused authority/receipt/bus/daemon: 63 tests in 4.449s.
- Python 3.11 authority/bus: 22 tests in 1.534s.
- Full Python suite: 830 tests in 36.842s, passed without retry.
- Rebuilt isolated wheel SHA256:
  9cce809aeeb22d3c76e1545c2039ae06aaa0150cf548cbdf54eff3506e3941e8.
- Reinstalled final wheel: six tests in 1.143s; installed module path checked,
  initialized descriptors 5 -> 5 and children 0 -> 0 again.
- Source/test/hook compilation and diff hygiene passed.

The initial wheel/sample and initial hosted result above remain historical;
only final-head hosted gates can establish integration readiness.
