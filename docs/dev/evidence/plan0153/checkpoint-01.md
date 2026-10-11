# Checkpoint01 — Retention and counter fallback

Progress: outcome_progress. Primary owns fix/issue243-intent-recovery in
codex-wake-issue243; root's StableTime rollout/dirty documentation unchanged.
Goal: resolve #243 using Matt's process, stop before 2M tokens or 6h; first
readback133098 tokens /1581 seconds, well below 1.9M/5h45m checkpoint ceiling.

Installed reproduction:0.13.0-stable-time-01 actual CLI, injected unavailable
acquisition, exit2 and zero records. Fifteen installed baseline tests PASS.
Source TDD:5 tests PASS after observed missing-retention, missing elapsed
recovery, unsupported new intent key, None-expiry dispatch and stop-bypass reds.
Counter due fixture initially used a quantization boundary; corrected to a
worked 3h+10ms sample, preserving not-before outward rounding.

Implemented in owned worktree: schema6 pending intent, fsync publication,
metadata inventory, automatic poll recovery, authenticated elapsed-only mode,
explicit stable idempotency key, deadline-aware tolerance and absolute-stop
fields, same-epoch/rate bounds, exact native transport reuse, fresh temporal
gates before queue admission and original uncertain-submission reconciliation.
No production wake/notification/turn, service restart or Windows clock mutation.

Fresh authenticated service read initially stillunavailable/uncertainty_exceeded
with no UTC estimate, but native counter/epoch/ratepolicy present. Later adapter
read qualified UTC plus counter: outage recovered without a consumer repair;
actual prior error magnitude remains unknown. Do not infer incident cause.

Next: origin recovery when no initial clock exists, UTC continuity fallback,
malformed/boundary/suspend/expiry/cancel/retry tests, installed isolated monitor
chain proof, serial review. Setup default label choice pending; concrete draft
exists privately. Read-only dependency overlay hash receipt preserves Plan0152's
no-commit/push boundary. Source integration/deployment not yet qualified.
