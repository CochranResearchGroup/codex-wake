# Ticket0144 — Ship and activate qualified native live submission

State: OPEN
Workflow: IN_PROGRESS
Owner: primary
Lane: P71
Branch: docs/a2a-completion-stream
Target: origin/main
Integration: governed_by_plan0141
Work-Item: docs/dev/plans/0144-2026-10-10-release-native-live-submission.md
Parent: docs/dev/plans/0141-2026-10-10-a2a-completion-stream.md
Depends-On: Plan0143

## What it delivers

The normal installed CLI runs the qualified repair from a published release with source/artifact parity, rollback targets and clean repository custody.

## Blocked by

[0143](0143-2026-10-10-native-live-safety-and-round-trip.md)

## Acceptance criteria

- [ ] Serial Standards and Spec reviews pin source and adjudicate findings; one consolidated remediation pass followed by relevant invalidated checks.
- [ ] Merge exact reviewed head through normal PR path; build wheel/sdist from merge SHA and compare every tracked package file with the tested candidate/final installation.
- [ ] Publish/download release assets and verify hashes/tag target; activate CLI links retaining prior immutable prefix and rollback targets.
- [ ] Verify installed command/version and service PID/state snapshots; no unrelated restart. Hosted CI waiting stays user-waived and is never reported PASS.
- [ ] Root is clean published main; clean merged owned worktree closes after exact remote custody and CWD-owner readback; owned test tabs closed.

## Test seam and bound

Released CLI readback, asset hashes and full package-file parity. Reuse byte-identical installed controls; rerun only invalidated conditions.

## Owned write surface

Release notes/evidence, version, packaging and catalog closeout; immutable installations and reversible CLI links.

## Execution and terminal condition

One primary owner; obey Plan0141 authority, evidence and no-replay rules. Before
implementation, register the actual branch/checkpoint and update this header.
READY means refined and unblocked, not implemented. DONE requires all acceptance
checks, attributable source/evidence, integration or explicit non-code completion,
and owned cleanup. BLOCKED records a missing dependency/evidence, not approval
inferred from elapsed time. Planning alone does not satisfy a behavior criterion.
