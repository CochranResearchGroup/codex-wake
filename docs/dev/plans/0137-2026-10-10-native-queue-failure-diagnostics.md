# Plan0137 — Preserve safe native queue failure diagnostics

State: OPEN
Workflow: IN_PROGRESS
Owner: primary
Lane: P67
Branch: fix/native-queue-diagnostics
Target: origin/main
Integration: squash_pr
Work-Item: docs/dev/plans/0137-2026-10-10-native-queue-failure-diagnostics.md

## Scope and contract

Diagnose the confirmed loss of queue-command failure evidence, not LitScout's
unrecoverable original submission cause. Public scheduler and persisted record
inspection are the behavior seams. Keep uncertain state, original intent and
attempts1 through later read-only reconciliation; never automatically resend.

Persist bounded structured evidence: failure phase/reason, exit code or timeout,
exception class, observed output lengths and allowlisted stderr hints. Arbitrary
stdout/stderr, prompt echoes, argv, exception text and unknown error bodies stay
withheld. Hints are untrusted observations, not authoritative error diagnoses.
Unknown errors retain their failure classification without a verbatim excerpt.

## Execution and acceptance

One small slice: reproduce actual rejected subprocess with a deterministic test,
fix retention, then test timeout and unconfirmed stdout. Run affected native
coverage and installed wheel controls; review Standards and Spec separately.
Commit/publish coherent source with receipts. No new time policy, provider,
transport, live replay, schema migration or unrelated worker rollout. Installed
upgrade and release require separate version/provenance readback if performed.
Final hosted CI wait is waived under the operator's existing instruction.

## Current state

Started at main2a8a945; LitScout repair and v0.10.0 native deadlines retained.
No effect has been retried. Acceptance pending.
