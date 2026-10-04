# Multiroot mailbox resource and restart qualification

State: CLOSED
Lane: P63
Owner: primary
Parent: Plan 0101 / issue #181
Branch: feat/p63-resource-qualification
Target: origin/main
Integration: squash_pr

## Current State

Main 0049a2a includes receipt arming and delivery provenance. Operations/resource
acceptance remains open; live disposable scope is pending. This packet qualifies
synthetic multiroot policy, restart identity, durability and bounded resources.
It does not substitute for the installed two-agent or service/release gates.

## Scope and authority

One serialized provider-free harness creates its own temporary private buses,
two explicitly enrolled temporary roots, and clearly synthetic actor identities.
No real thread enrollment, runtime daemon, notification or provider effect.
Write surface: one reproducible qualification script, installed CI gate,
verification, parent and runbook. No runtime implementation unless a specific invariant fails.

## Bounds and acceptance

Set before measurement: 100 requests, 20 replies, 10 fresh process reopen checks;
15-second subprocess timeout; 30-second total; 10 MiB store ceiling; parent FD
increase at most two and residual children zero. Fake clock advances seven seconds
per admission to respect the unmodified ten-per-minute production limit; this is
bounded workload qualification, not real-time soak. Keep default mailbox limits.
All FIFO pages and correlated replies must survive fresh process checks;
identical send retries return the original identity. Explicit cross-root deny
and enabled allow are both exercised. Copied-root activation must be refused.
Fail with attributable evidence; do not retry to erase a failed resource result.
Two implementation attempts, one targeted repair; inherited allowances retained.
Current goal stop before 500k, working checkpoint 450k.

## Definition of done and non-goals

Installed wheel and source run produce bounded JSON verdicts with declared
thresholds, observed metrics and no residual processes. Mark only these axes
accepted; full campaign, live delivery/suspension, production retention-pin
acknowledgement, physical compaction and release remain open.

## Closeout

The bounded synthetic workload passed source Python 3.12 and 3.11 and isolated
installed-wheel runs. FIFO, reply correlation, cross-root refusal/allowance and
fresh-process durability held; descriptors stayed five, residual children zero,
zero dispatch attempts. First failure was a harness assertion expecting the wrong
error code; runtime correctly refused copied-root activation. Verification 0104
preserves the failure and final metrics. Hosted installed CI remains a separate
gate. No runtime code changed or inherited discovery-review allowance reset.
Progress classification: outcome_progress on operations/resource axes only.
