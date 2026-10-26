# Modern native bridge port and managed deployment

State: OPEN  
Owner: primary / ecochran76  
Work items: 318, 310, 343, 345, 346  
Branch: `fix/native-managed-activation`; native branch: `fix/wake-native-0.164`  
Target: origin/main through PR359, with the native dependency pinned by source, patch and artifact.  
Authority: operator approved Q1, preserving modern managed updates, plus standing merge/deploy authorization.

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
