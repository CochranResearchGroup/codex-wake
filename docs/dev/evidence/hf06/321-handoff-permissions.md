# HF-06-B / issue321 source acceptance

Owner: worker /root/hf06_b; integration owner: primary.
Worktree: codex-wake-hf06-b / feat/321-handoff-permissions.
Base0597a2a; primary host adapter hook1520816 is present as cherry-picke3f1df3.
Primary-owned core patch8afa70a was temporarily applied for focused tests and
must not be included in this worker's implementation commit. Integration already
owns that core contract, including default task-approval transfer, owner completion
and verified ancestry. No installed runtime or provider effect was exercised.

## Behavior and acceptance

- Common-policy admission reuses a matching task approval for the exact native
  self and configured manual/context_limit/update/resource_warning trigger.
  Automatic triggers must appear in the host continuation's handoff_triggers.
- Public MCP invokes a bounded private child; tool roles, predecessor claims,
  caller registry paths and trust flags are not agent arguments. CLI uses the
  existing bus operator/actor capability. No copied caller UUID grants.
- Current policy is revalidated before owned successor spawn, native/tmux input,
  successor goal preparation and monitor activation. Existing continuation
  counters, pinned brief, original deadline and allowance remain unchanged.
- Verified succession provenance is written to the existing private lifecycle
  receipt only after exact native successor/goal/brief preflight. Its chain must
  retain all same-task links; missing, changed, cyclic, ambiguous or overlong
  lineage refuses. No additional inventory or grant store is introduced.
- Only applicable task approvals transfer. Original-session-only approvals do
  not transfer, expiry/completed tasks terminate reuse, and current successor
  restrictions still win. Task-brief/owner lookup uses the common permission
  root; execution journals remain on their owned execution root.
- Revocation blocks queued/subsequent effects. A repeated authenticated exact
  uncertain intent may read its original source/successor observations without
  replaying I/O, restoring a goal, deleting uncertainty or renewing resources.
  Independent resource-stop and emergency behavior remain separate.

## Validation receipts

Initial RED: `PYTHONPATH=src <integration-venv-python> -m unittest discover -s
 tests -p test_handoff_permissions.py -v` failed with missing permission_handoff.
Exact log: /tmp/hf06-b-red.log.

Focused GREEN: same command, five tests pass (log /tmp/hf06-b-policy.log).
Includes actual public-MCP bounded child admission, denial, spoof prevention,
read-only uncertain retry, transitive approval chain, expiry/task completion and
independent monitor revocation with zero activation effects.

Public CLI/native/PTYS GREEN: `... -m unittest discover -s tests -p
 test_agent_handoff_preflight.py -k common_policy -v`, one test passes
(/tmp/hf06-b-common-cli.log). A pinned approved task plus configured context_limit
trigger reaches a verified successor despite empty caller grants; no allowance
is added and the task pin remains the original admitted revision.

Compatibility: task-brief lifecycle four tests pass. Existing handoff-preflight
50 tests passed before adding the new common-policy scenario. Final full module GREEN: 51 tests in70.840s, no skips/failures
(/tmp/hf06-b-final-handoff.log), with isolated XDG configuration/state and stable-time
configuration disabled.
Pinned Ruff F821/F822/F823 and git diff --check pass.

## Scope limits

No new native lifecycle capability. Missing qualification remains unsupported or
held by existing accounting/ownership/preflight guards. #318 scoped MCP refresh
and #319 observation-stop recovery are not implemented or closed by this slice.
Source evidence is not main integration, release, deployment or live acceptance.
Broad review invocation and the final TDD findings-remediation pass remain reserved
for the primary after ticket closure. Memory disposition: forbidden (no explicit
user request for memory write).
