# Modern native bridge port and managed deployment

State: OPEN
Owner: primary / ecochran76
Work items: 318, 310, 343, 345, 346
Branch: `fix/native-managed-activation`; native branch: `fix/wake-native-0.164`
Target: origin/main through PR359, with the native dependency pinned by source, patch and artifact.
Authority: operator approved Q1, preserving modern managed updates, plus standing merge/deploy authorization.

## Current State

Source and private package qualification are complete. Final native source is
`fbfe287f4d738946ed3b158da9d9081db01ed039`; the complete package CLI is
`31b27c12fb4639b4568002cde21a6ab75d76f29cab8c32d0e1f137bb2c7c640b`.
Every file and mode matches the package that passed actual installed Wake dev1,
paginated stock-TUI replay/control and modern managed rollback acceptance.
Scoped Clippy and final formatting pass; only unchanged upstream warnings remain.

Live activation remains open. The shared daemon is still stock, the goal-limit
service is masked, and this requesting caller lacks a host refresh grant.
A validated current-connection-only proposal and current dev1 service override
are prepared privately, not applied. Preserve all stopped budgets and unrelated
active work. Actual requesting-session acceptance is still required for 318/310.
See [final qualification](../../evidence/plan0173/modern-native-tui-qualification.md).

## Scope and current state

Port only scoped MCP reload/runtime inspection and bounded, idempotent notices that
start no model turn. The matching modern source already supplies authentic usage,
root-turn lineage and MCP caller metadata; do not carry the obsolete June backports.
CLI lifecycle and accounting implementation remain upstream behavior.

Official `rust-v0.164.0` resolves to
`6aaac694803004a63c6f393d153c96d22521a6b9`. The official archive SHA256 is
`90dd0b03b28afcb7fa733a4f73b413db2916a47347efd43fb669cc1c774ee8e4`;
its binary matches installed stock `b93f6811…7f306` byte for byte.
Native commits `6be3e676`, `1808af42` and `ea929042` normalize the release lockfile,
port scoped operations and carry the notice implementation, respectively.
Lockfile normalization changes 166 workspace versions, with external dependencies unchanged.

The complete GNU package built successfully in 1353.666 seconds using Rust 1.99.1,
two jobs and the upstream package builder. Source:
`ea92904281f99180c24773c2fb597e60891213af`.
Immutable candidate: `~/.local/share/codex-wake/native/modern-0164-ea92904281-candidate1`.
CLI SHA256: `37d750ff09e3b47d1ceb0745c9f0b88adc2e4b21d67e27230a4055e28adcdcf5`.
Helper SHA256: `8838d6e3846bd2edd665d8f284b3f1ef50013e911ea990f1b177f0c0660c4ba2`.
The package includes the matching manifest, helper, verified rg and bwrap.
No live activation has occurred.

Stable and experimental protocol exports and the official Python SDK are generated.
Protocol unit validation: 317 passed, one ignored. Frozen SDK dependencies were
installed without lockfile changes after the initial offline setup failure.
The initial failure log was accidentally overwritten by the successful followup;
its original receipt and transcript remain, and no replacement log was fabricated.
Receipts and package provenance live outside Git under
`~/.local/state/codex-wake/native-modern-0164/`.

## Final source checkpoint

Native source is frozen at `3ab07eac61e3247524e66afcb3f9271a87725482`.
Focused validation found and repaired a real modern paginated-history bug:
notices now persist the canonical ItemCompleted form, with the legacy form
retained for old conversations. All four remediation cases passed with retries
disabled, covering both history modes, restart/readback, deduplication,
pending-response retention and scoped MCP reload. Both connection-reuse modes
and modern hook warmup passed in the original selection.

The final complete package is rebuilding from this checkpoint. The first broad
source review had no findings; the later runtime failure and bounded repair are
recorded in the source-review evidence. Final caller-metadata/Clippy checks,
managed package qualification, paginated TUI/accounting journey and live handover
remain open. The TUI runner now supports an explicit paginated-history mode.

## Acceptance and execution graph

Stock runtime baselines failed with native unknown-method errors for scoped reload
and both notice RPCs. These are actual private runtime reproductions, not mocks.
The new package must pass positive runtime acceptance before deployment.

1. Generate protocol/SDK exports and run protocol unit tests: complete.
2. In parallel, run the private modern stock → candidate → stock package roundtrip
   and focused native integration tests. One compiler owns the shared cache.
3. Validate the matching helper, sandbox and genuine local Responses goal/TUI journey.
4. Run affected Clippy checks, final formatting and one independent modern-port review.
   Address accepted findings with one bounded TDD pass; do not repeat legacy reviews.
5. Publish final source/patch custody, qualify the final package and merge PR359.
6. Coordinate live handover, deploy through supported update, and verify the actual
   requesting connection and goal controls.

The roundtrip must preserve conversations, goals, history and resource state.
Scoped reload must affect only the selected loaded thread; runtime-only inspection
must never discover a global client. Notices must be bounded, durable, idempotent,
retained while a model response is pending, and truthful about confirmed delivery.
Use loopback fixtures for model accounting; no external provider charges.

Primary owns integration, source authority and deployment. `combined_native` owns
focused native validation and generated exports. `modern_package_path` owns the
opt-in modern managed qualifier and its evidence report in a separate Wake worktree.
At most three implementation lanes, no nested agents, and two compiler jobs.

## Build and resource controls

Reuse GNU/dev-small, the verified V8 archive/binding pair and the same bwrap hash:
`8b6679d62120e60335aac2bfe141f60237710ff0897e658113d1e039987a78db`.
Do not strip bwrap after hashing. Initial build bound was 1800 seconds with a
64 GiB free-space reserve; final free space was 139252117504 bytes.
Only the unused 36 GiB legacy derived cache was reclaimed, after process/lock
checks and matching hashes for all three retained immutable legacy binaries.
Stock rollback remains at `~/.local/share/codex-wake/native/stock-0164-b93f6811`.

## Deployment gates and definition of done

Use the complete package's `codex app-server daemon update --from-cli --yes`.
Upstream deliberately pins that selected package and stops its updater; ordinary
`daemon update` restores production updates. Preserve a complete stock rollback.
Do not replace live links or kill the daemon outside supported handover.

The last operational preflight found 132 loaded threads, nine active and three
with system errors. Refresh this census before cutover and coordinate active work.
The goal-limit service is masked/inactive and still selects the older 0.21.1 prefix.
Prepare its exact 0.22 prefix while masked. Preserve all eight historical receipts,
counters, allowances and latches; do not implicitly unmask, renew or resume goals.
Three stored skill proof hashes are stale and the current caller binding is unproven.
Refresh proofs from installed files and authentic client readback, then demonstrate
an authorized current-connection canary with an unchanged peer.

Done means the final qualified package is installed through the modern mechanism,
process/package/capability readbacks match, resource invariants hold, and actual
requesting-session goal controls work. Keep issues 318 and 310 open until those
outcomes are proved. CI remains skipped by operator instruction.

## Replay repair and concurrent mainline reconciliation

The `3ab07eac61` package passed the complete modern managed roundtrip, selected
MCP isolation, canonical paginated notice reads and stock rollback. Genuine TUI
acceptance then passed enrollment/accounting, live cards, exact interruption
and watcher replacement, but failed cold replay: notice items had no matching
turn metadata and stock TUI omitted them. This package is not ready for activation.

Read-only source tracing and the fixture database confirm orphan notice items.
The bounded repair will use upstream's existing ItemCompleted plus TurnComplete
representation for a completed display container, without TurnStarted, provider
usage or session completion-handler effects. Preserve real work/goal state and
legacy history. Require public turn/item association and actual stock TUI cold
replay before accepting the successor package. Actual persisted task_started IDs,
not response counts or display-container IDs, establish model-turn absence.

Concurrent main now includes PR358 (`1a31564`, governor controls) and PR361
(`02b68e8`, future-wake repair). Both are merged into this branch without conflicts.
The live Wake CLI/MCP/refresh monitor selects the newer 166-module `1a31564`
prefix. Earlier ce1ad 162-module private proofs remain historical baseline evidence;
do not call them current host qualification or overwrite the newer deployment.
The old proposed ce1ad goal-limit unit prefix is superseded without applying it.
Re-anchor the final Wake acceptance target after this reconciliation.


Current Wake acceptance target is now frozen at merged main
`e58d3a9701a34e39f7d1ded2668a4f15a1cc18d4` (PR362, install identity).
Merge `09afeaa` includes that exact parent. Live commands select
`0.22.0.dev1-e58d3a9`; all 166 installed Python files match this branch and the
private candidate. Use this target for the next native/TUI journey; the earlier
ce1ad baseline is not current host evidence. No installed service was changed by
this reconciliation.
