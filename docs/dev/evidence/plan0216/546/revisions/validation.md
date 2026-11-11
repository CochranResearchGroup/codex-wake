# Trusted producer revisions and selective formatting

Base source `e5beb4c7`, branch `fix/observer-projection-cost-546`.
No production process, monitor, native formatting or provider was changed.

The qualified pre-change steady profiles excluded startup. Ten idle ticks spent
0.065 seconds in display-key construction; ten active ticks spent 0.078 seconds
there, projected 1,020 resources and performed 80 native format batches. The
selected exact profile data and source artifact hashes are in steady-before.json.
These profiled timings are diagnostic, not resource-gate measurements.

## Shared producer contract

Agreed with the lifecycle producer owner and primary owner before implementation:

- A daemon-origin snapshot and each resource may carry projection_revision, a
  bounded opaque string (1..128 characters). It includes qualified physical/source
  identity, display-relevant evidence, source availability and epochs. Equivalent
  inventory and quiet sample-clock changes preserve it.
- projection_valid_until is an optional finite wall-clock boundary for the next
  display qualification change. Intermittent error/health evidence can expire;
  continuously qualified native activity has no age expiry. The producer
  recomputes its token on expiry. The consumer also rejects an expired boundary
  even if an old producer token is supplied.
- evidence_revision changes independently when retained diagnostic observations
  change without changing display semantics. Sparse evidence changes refresh
  redacted inspection details without repainting identical options.
- Public monitor status strips tokens when it downgrades persisted observations
  after owner/source loss. Source gaps change availability/epoch revisions.
- Missing tokens and manual/legacy observations use the existing bounded semantic
  fingerprint path. Tokens are accepted only at this internal trusted daemon
  observation seam, not as new remote operation arguments or authority.

## Consumer change

The formatter accepts the whole producer token without traversing 100 resources
on every idle tick. Its existing local memo still includes external formatting
state identity, source configuration and live socket inode/mode/UID. Policy,
pause, rollback, resume, socket replacement or changed source tokens invalidate
it immediately.

A window render is reused only when its producer token, effective-policy digest,
exact saved panes and valid display boundary match. Evidence-only changes update
its retained details; changed windows render once and still read native options
before effects. Failed effects do not advance the window's saved render token.
Original baselines remain durable before first native writes.

Five-second quiet shared-lease renewal now checks managed native session custody
and the live socket without re-inventorying/reprojecting all 100 windows. It
requires a prior qualified namespace and exact unchanged whole source/config/state
identity. Missing records, uncertain sources, identity changes, expired evidence
or a due 60-second window custody audit fall back to full qualification. No audit
or manual override protection is suppressed. One existing monitor and one existing
shared lease remain the owners; no per-tab process or journal was added.

## Validation and remaining gate

A new public native test failed before the change because a quiet trusted lease
renewal reran list-panes and server discovery. It now renews through at most two
managed session metadata operations without physical window inventory. Additional
public native tests prove a due custody audit preserves manual formatting and an
expired held producer token removes ERR while retaining redacted inspect evidence.
All existing preset, source-loss, rollback, reenable, process-budget and explicit
manual-resume tests remain in the affected selection.

Commands:

- `PYTHONPATH=src /tmp/wake216-py311/bin/python -m unittest discover -s tests -p 'test_tab_format*.py' -q`: 61 passed, 17.488 seconds.
- Same selection with `/tmp/wake216-py312/bin/python`: 61 passed, 17.776 seconds.
- Undefined-name lint on changed formatting modules and focused tests: passed.
- `git diff --check`: passed.

Hosted CI was skipped under repository cost policy. This is focused functional
validation, not a full-suite claim, installed-package proof or a passing resource
acceptance claim. Actual public-service before/after measurements must combine
this consumer with the separately qualified producer revision change and remain
with the primary/acceptance owner. Existing 1%/5% CPU caps are unchanged; the
resource gate remains open until those exact service/package checks pass.

No broad review, tracker closure, merge, deployment or memory write was performed.
The primary owns the final single closeout memory disposition.
