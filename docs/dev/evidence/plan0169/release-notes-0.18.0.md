# Codex Wake0.18.0 — prepared, unpublished

Native callers can self-enroll into host-delegated fixed objective allocations
without per-session UUID grants. The private native MCP connection binds the
actual session/turn/call independently of model arguments. Version2host policies
name objective allocations; version1explicit caller grants remain compatible.
This trusts the local host gateway, not arbitrary HTTP or hostile same-UID code.

Fresh input plus output is the default token basis, excluding cached input.
Legacy enrolled receipts retain their prior basis until explicitly converted;
re-evaluation preserves historical accounting and does not clear stop latches.
Successors share cumulative unique-response spending and the original deadline.
Self enrollment can tighten limits but cannot create or renew an allowance.
Explicit host renewals preserve finalized prior charges and exact response
anchors; changed retry boundaries hold for reconciliation.

Checkpoint/grace pauses the campaign and interrupts only captured work turns.
Later operator replies remain usable. Shared stop/grace state survives successors
and retries. No shared executor termination or exact token-overshoot guarantee.

Local qualification:1372Python tests pass with1skip under isolated XDGstate/config
and fixture clock settings;12plugin tests pass; actual native public enrollment
original/successor charges20then40fresh tokens with the original deadline and
unchanged unrelated control. Full failed host-contaminated runs are retained.
This note is not a published release, remote matrix-CI result or production
installation/provisioning receipt.

Host policy may import a qualified pre-existing operator renewal boundary for
first deployment, preserving its original deadline and post-renewal spend.
Version2policies can retain exact legacy caller grants beside delegated
allocations. A mismatched allocation selection holds instead of using another
allowance. Native import/continuation qualification charges10then30fresh after
its boundary with an unchanged unrelated control.
