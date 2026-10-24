# HF-06 review and bounded remediation

One broad review invocation covered fixed base
`588ff39215f4b4e2c04f72bc771a364fab766470` through frozen tip
`b0cead5bd96ede9ac4eb08599618892ce695b8b6`.
Read-only reviewers: `/root/hf06_review_standards` and `/root/hf06_review_spec`.
No second broad review was invoked. One bounded TDD remediation pass follows.

## Standards

- P3 fixed future approval expiry in the new convergence test:
  `nonblocking_backlog`, accepted and fixed in the bounded pass. Positive and
  negative expiry fixtures now derive from one declared UTC reference with a
  one-year margin; the public subprocess still uses its real clock.
- No blocking Standards findings or further accepted cleanup.

## Spec

- P1 enforcement continuation discarded task/operation context: `blocking`,
  accepted and fixed. The existing independent-controller regression now
  enrolls a task-bearing caller and revokes only that assignment. RED returned
  `armed` instead of `held`; GREEN holds without interrupting, retains original
  charges/deadline, isolates the peer and still performs the original safety
  stop at exhaustion. The private admission decision retains operation context.
- P2 public inspection omitted verified task/operation context and approval
  scope: `blocking`, accepted and fixed. The public CommandRunner regression
  first returned `invalid_argument`; GREEN explains a verified assignment's
  task approval and rejects a task claim without its admission. CLI and MCP
  share the evaluator's approval scope/issuer and operation output. Host task
  delegation stays private; native arguments cannot manufacture a role.
- No additional confirmed Spec findings.

## TDD seams and receipts

The existing public enrollment plus independent poll seam catches revoked
assignment authority and original safety behavior; it does not prove installed
native recovery. The actual MCP CommandRunner seam catches schema, private
child routing, verified assignment admission and explanation; it does not
establish native capability for refresh or recovery.

User-scoped evidence directory:
`/home/ecochran76/.local/state/codex-wake-hf06-publication/`.
Commands used the source worktree's Python 3.12 interpreter, isolated XDG roots,
empty `CODEX_WAKE_STABLE_TIME_CONFIG`, and `PYTHONPATH=src:tests`:

- `python -m unittest test_enforcement_permissions.EnforcementPermissionTests.test_controller_rechecks_revocation_without_interrupting_or_disabling_safety`
  — `tdd-p1-red.log` FAIL; `tdd-p1-green.log` PASS.
- `python -m unittest test_enforcement_permissions.EnforcementPermissionTests.test_native_adapter_reuses_only_its_verified_assignment_approval`
  — `tdd-p2-red.log` FAIL; `tdd-p2-green.log` PASS.
- `python -m unittest test_session_permissions test_enforcement_permissions test_permission_convergence test_handoff_permissions test_permission_migration`
  — `tdd-focused.log`, 32 PASS in13.746seconds.

Final comprehensive Python3.11/3.12 validation and isolated wheel receipts are
recorded in the execution ledger after completion. This is source acceptance;
#318/#319 and installed acceptance #310 remain open. Production stays0.20.1.

Memory disposition: `forbidden`; developer instructions require an explicit
user request before a memory write, and this task supplies none.
