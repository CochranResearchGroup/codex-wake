# Plan 0053: Restart-Correct Filesystem Wakes

Status: CLOSED

Issue: `CochranResearchGroup/codex-wake#6`

Branch: `feat/issue-6-filesystem-wakes`

## Outcome

Deliver portable file-created, file-exists, and observed-file-changed signal
recipes whose durable fingerprints and reconciliation remain correct across
restart, watcher loss, overflow, rename, delete/recreate, and coalesced writes.

## Scope and acceptance

- Keep watcher notifications as optional latency hints; bounded fingerprint
  reconciliation is correctness authority.
- Normalize safe path subjects and bounded evidence without retaining file
  content or accepting arbitrary callbacks.
- Preserve pre-registration baselines for `becomes` and change semantics.
- Expose baseline, observed fingerprint, and coalescing evidence through the
  existing bounded inspection surface.
- Prove provider-free registration, persistence, restart, match, and
  no-dispatch firing, plus Python 3.11/3.12 and plugin regression gates.

## Non-goals

No live target dispatch, installed service mutation, deploy, release, GitHub
provider work, or guarantee that every physical write occurrence is retained.

## Execution

Use `gpt-5.6-sol` high for implementation. The primary owns shared signal and
CLI contracts; one `gpt-5.6-luna` medium read-only review follows green tests.

## Implementation outcome

Implemented on `feat/issue-6-filesystem-wakes` for primary review:

- `FilesystemSignalAdapter` exposes root-confined `created`, `exists`, and
  `changed` recipes with normalized relative subjects and content-free
  structural fingerprint anchors.
- `FilesystemSignalRunner` always reconciles the current fingerprint. Optional
  notification counts, startup recovery, watcher loss, and overflow affect
  bounded coalescing evidence only; they never become match authority.
- A provider-neutral `SignalSourceRunner` protocol lets `poll_once` execute
  bounded injected runners before schema-v2 evaluation without teaching the
  daemon filesystem-specific behavior.
- `codex-wake filesystem created|exists|changed` arms schema-v2 records through
  the managed-reader capability gate while the existing schema-v1 `file` and
  `changed` behavior remains unchanged.
- `show --signal-state` exposes the filesystem registration baseline and the
  latest bounded observed fingerprint/coalescing evidence without file content.

Provider-free tests cover registration baselines, persistence, restart,
startup recovery, watcher overflow, rename, delete/recreate, rapid notification
coalescing, path-escape degradation, bounded evidence, and persistence through
no-dispatch firing.

Pre-review validation on 2026-09-14:

- focused affected tier: 126 tests passed;
- Python 3.11 comprehensive tier: 272 tests passed;
- Python 3.12 comprehensive tier: 272 tests passed;
- OpenClaw plugin tier: 12 tests passed;
- `python3.12 -m compileall -q src tests`: passed;
- `git diff --check`: passed.

The bounded review repair groups arms by source instance, samples once, and
commits one checkpoint plus at most one observation per distinct matching kind
in one ingest. Unchanged samples advance the source checkpoint with an empty
batch, repeated changed-state samples quiesce, and same-kind arms fan out from
one durable receipt. Primary reconciliation also replaced subclass/equality
trust at the request boundary with exact request and clause validation.

Post-rebase final validation on 2026-09-14: the focused filesystem and CLI
tier passed 64 tests on Python 3.11 and 3.12; the comprehensive tier passed 289
tests on each runtime; and the OpenClaw plugin tier passed 12 tests. Both
Python versions passed `-m compileall -q src tests`; `git diff --check` passed.

The portable contract does not select or ship a native watcher backend. A
long-lived source runner may feed notification hints, while periodic/startup
reconciliation remains sufficient for correctness and is the acceptance
authority. Default installed-runner construction and readiness packaging remain
owned by the later productization lane.
