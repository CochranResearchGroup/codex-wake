# Proposed child graph for #444

Status: DRAFT — awaiting operator review; no child issues created.

## 1. Run a durable bounded upgrade job through deterministic staging

Blocked by: None.

Start and inspect one isolated release job through CLI/API/MCP; apply pinned patches, build/stage with existing primitives, preserve progress and cumulative budgets across restart, enforce owned-worker cancellation and disable fencing.

- [ ] A fixture release reaches staged or a truthful failed/held state through all three public surfaces.
- [ ] One-candidate, three-attempt, two-hour, two-compiler-job and 24 GiB limits are enforced and survive restart.
- [ ] Unresolved conflicts are detected independently of command exit code; deterministic failure preserves selection.
- [ ] Disable stops owned workers and fences later stages without affecting unrelated sessions.

## 2. Autonomously repair conflicting patches with independent behavioral review

Blocked by: 1.

A conflicting candidate invokes a bounded coding worker, obtains independently adjudicated review and returns a reviewed package candidate or a visible held result.

- [ ] Rewrites and patch retirement require demonstrated behavioral equivalence; required capabilities cannot be waived.
- [ ] Review binds candidate/test digests; subsequent changes invalidate affected approval.
- [ ] Generated bindings, schema and lockfile changes are included in build qualification.
- [ ] Rejected repairs and crashes consume the same job budget; no hidden fresh attempt.

## 3. Qualify exact candidates through disposable installed account and capability journeys

Blocked by: 1.

A staged package is installed and tested in disposable WSL with real launcher wiring, synthetic histories, designated authenticated test accounts and required capability checks.

- [ ] Immutable package/executable digests bind the qualification receipt.
- [ ] Metadata-only identity, account switching, restart and reconnect pass with zero model turns.
- [ ] Authentication-needed is explicit and never falls back to production credentials.
- [ ] Capabilities, session visibility, failure recovery and compatible rollback are exercised; teardown census records owned processes.

## 4. Promote qualified builds for future launches with compatible rollback

Blocked by: 1, 3.

A configured opt-in scope automatically selects a qualifying candidate while active sessions remain pinned; the public interface exposes selection and rollback outcomes.

- [ ] Revalidate enabled policy, scope, generations, review/qualification and package identity immediately before atomic selection.
- [ ] Disable/promotion races and uncertain commit results reconcile without false claims or repeated effects.
- [ ] Failed or incompatible candidates preserve the working build; incompatible rollback refuses without rewriting history.
- [ ] No live daemon replacement or account migration is triggered.

## 5. Discover stable releases persistently and coalesce the upgrade queue

Blocked by: 1.

An opt-in persistent watcher creates deduplicated upgrade jobs and processes the newest stable release after the current bounded attempt.

- [ ] Official provenance, stable-only filtering, lag and poll state are inspectable.
- [ ] Repeated polling/restarts cannot reset a failed release budget or duplicate accepted work.
- [ ] Newer releases coalesce predictably with retained skipped-release history.
- [ ] Disable prevents discovery dispatch; reenable does not silently renew exhausted jobs.

## 6. Expose upgrade progress and intervention notices to operator sessions

Blocked by: 1.

Durable CLI/API/MCP activity and attributable notices in registered operator sessions expose progress, held/failure reasons, promotion and disable outcomes.

- [ ] Notices identify job/release/target/reason without submitting model turns.
- [ ] Held, failed and promoted outcomes are delivered promptly with deduplication and durable delivery status.
- [ ] Absent recipients or delivery failures remain visible through public status.
- [ ] No external messaging channel is enabled.

## 7. Prove the complete autonomous 0.166 repair and future-launch upgrade

Blocked by: 2, 3, 4, 5, 6.

The assembled bot ports the complete real patch stack to official 0.166, independently reviews it, qualifies the exact package in disposable WSL and promotes only the disposable future-launch scope.

- [ ] Capture real baseline conflicts, actual repair changes and review dispositions; regenerate derived artifacts and build the complete package.
- [ ] Required native capabilities and real installed account/history/reconnect journeys pass with explicit evidence boundaries.
- [ ] Demonstrate failed-candidate preservation, disable, restart/budget continuity and compatible rollback.
- [ ] Record source/package hashes, applicable passing local checks, resource/cache usage, final process census and remaining #413/#380 gates.
- [ ] Source integration and test qualification are reported separately from production activation.
