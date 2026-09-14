# Verification 0073: Installed Filesystem Wake Canary

Date: 2026-09-14
Plan: `docs/dev/plans/0057-2026-09-14-installed-filesystem-canary.md`
Issue: CochranResearchGroup/codex-wake#30
Candidate: `86291bf8782759dfd6d4bd19e1429392e8f77279`

## Result

PASS after one bounded post-submit projection repair. One installed
schema-v2 `file.created` wake crossed a controlled service restart, matched a
real disposable filesystem transition, dispatched exactly once to the captured
Codex tmux pane, received the hook acknowledgement, and recorded
`visible_prompt_observed`. The canary also exposed a stale revision-1 pending
projection after submission; the receipt branch adds a regression test and a
journal-aware prevention/recovery repair before closeout.

## Candidate Identity

- Clean source commit:
  `86291bf8782759dfd6d4bd19e1429392e8f77279`.
- Wheel:
  `/tmp/codex-wake-p49-build-20260914/codex_wake-0.5.2-py3-none-any.whl`.
- Wheel SHA-256:
  `956846a82cd9007c423f11ee19400e0cd1ec4a9a79659befd638d869f80b6b75`.
- Candidate executable:
  `/home/ecochran76/.local/state/codex-wake/p49-canary-20260914/venv/bin/codex-wake`.
- Named service: `codex-wake-p49-canary.service` with exact canary wake,
  working-directory, daemon, log, and drop-in paths.
- Unit-specific state:
  `/home/ecochran76/.local/state/codex-wake/p49-canary-20260914/xdg-state`.
- Initial service PID `3287811`; controlled restart PID `3292411`.

The global uv-tool remained `codex-wake 0.5.2`. Its preflight executable
SHA-256 values were
`e04c4dc59c1feb4bfb824012e4cefce3ab70342e1f56d19b4a63b72cc164ecea`
for `codex-wake` and
`209507af842573172a3a08c57b2b50467562fe433a3e0254b61d88e9fda9514a`
for `codex-waked`.

## Registration And Restart

- Wake ID: `wake_9dbc51cc5a2d405d8ef4f1d2623d9c0d`.
- Idempotency key: `p49-installed-filesystem-canary-v1`.
- Registration cwd: exact canary runtime root.
- Predicate: `file.created` for `path:events/created.marker`.
- Baseline: `exists: false`, recovery `state_recheck`.
- Target: tmux socket `/tmp/tmux-1000/default`, pane `%36`.
- Persisted delivery bound: `attempts: 0`, `max_attempts: 1`.
- The controlled service restart changed PID `3287811` to `3292411`; the same
  wake remained pending, the marker remained absent, and source plus monitor
  readiness were current before the trigger was scheduled.

## Live Outcome

The named transient timer created the zero-byte marker at
`2026-09-14 17:38:54.220280307 -0500`. The terminal record proves:

- one `predicate_matched` event at `2026-09-14T22:38:54Z`;
- verification state `verified`, method `filesystem_state_recheck`;
- evidence digest
  `193ad75814e0011aa1849093fda51bfdfec506cc8a54fa176cbd795488aff872`;
- one and only one `dispatch_attempt`, with `attempts: 1` and
  `max_attempts: 1`;
- one `ack_observed` event;
- acknowledgement session `01a0a02b-522a-7423-b7ee-e4d5f3a81efe` and turn
  `01a0a212-3bf4-7320-b088-b07771fe2abb`;
- visibility classification `visible_prompt_observed`, with the wake marker
  absent before paste and newly present afterward; raw pane text was not
  stored.

The archived record SHA-256 is
`b5f7f2ef132533a864aa5194eb8cd3bc436471337b8a6b05ddb1fd636fbc7751`.
The bounded support artifact was 2,710 bytes with SHA-256
`c92fc7f3b2171c29946cb4dac1c81b0bb094a9ab70e182db190fadb6499e8173`.

## Canary Finding And Repair

On the first post-submit poll, the old candidate reapplied the already-applied
revision-1 registration outbox before retiring the revision-2 submitted
record. That recreated a stale `pending` file for the same wake ID. Journal
state remained authoritative at desired/applied `submitted`, the arm was
tombstoned, and no second dispatch occurred; the daemon counted the duplicate
as one stale active projection.

The receipt branch repair:

1. prevents revision-1 publication once lifecycle authority has advanced;
2. preserves idempotent registration replay after a match;
3. removes only a lower-or-equal-revision pending projection when an
   authoritative terminal record for the same wake and journal exists; and
4. retries that cleanup during terminal retirement, making crash recovery
   convergent.

Negative cleanup tests prove a newer pending revision or a foreign journal
identity is preserved.

The regression test recreates the exact submitted-plus-stale-pending state and
proves the next poll preserves the terminal record and removes the pending
projection. After the validated repair was applied to the stopped canary root,
status returned exactly one submitted record, zero active records, and one
`visible_prompt_observed` classification. The wake then archived normally.

## Validation

- Pre-change reproducer failed because the stale pending file remained.
- The focused regression passed after repair.
- 168 signal, store, daemon, record, injector, filesystem, and CLI tests passed
  on Python 3.12 after repair.
- Full Python 3.11 and Python 3.12 suites passed with 312 tests each.
- All 12 plugin tests and both JavaScript entrypoint syntax checks passed.
- Planning and goal audit results are recorded at closeout.

## Rollback

The submitted wake was archived before teardown. Final readback proved:

- `codex-wake-p49-canary.service` is `not-found/inactive` with PID `0`;
- both `codex-wake-p49-marker-20260914` transient units are
  `not-found/inactive`;
- initial and restarted PIDs `3287811` and `3292411` no longer exist;
- the exact service unit and XDG drop-in are absent;
- the exact canary runtime and build directories are absent after being moved
  to trash, so the deletion remains recoverable;
- the normal repo wake root remains at zero active and 23 archived wakes;
- the user supervisor remains active and pane `%36` remains live; and
- global version and both executable hashes exactly match preflight.
