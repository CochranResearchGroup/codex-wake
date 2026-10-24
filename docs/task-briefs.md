# Revisioned task briefs

Task briefs declare the approved objective, phase, non-goals, acceptance conditions
and bounded evidence for an assignment. They reference existing allocation and
permission authority; they do not create either authority or verify acceptance.

The `task-briefs` command family provides `propose`, `approve`, `inspect`, `admit`
and `pin`. CLI and MCP caller adapters use the same task-brief owner. A trusted
native/host adapter may supply exact worker/controller authority; the CLI also
accepts existing private A2A operator or actor capabilities. There is no model
argument for choosing an authority role. An A2A actor has worker operations only
within its enrolled workspace and cannot approve a brief. A host-delegated
controller must name its exact task scope.

A brief contains `objective`, `phase`, `non_goals`, `acceptance`, `workspace`,
`allocation_ref`, `permission_ref` and `context`. Non-goals and acceptance are
nonempty lists. Context is a list of `{path, sha256, required}` references to
canonical paths within the declared workspace. Up to 16 references and 64 KiB of
brief data are accepted; each required evidence file must be a regular file of
at most 1 MiB and match its digest at new assignment admission. Optional missing
or changed context is visible in the admission receipt. No transcript ingestion,
remote fetch, credential copying or model call occurs.

For example, with an existing private operator capability:

```sh
codex-wake --wake-root /owned/wake task-briefs propose \
  --task-id my-task --brief-file /owned/brief.json \
  --bus-root /owned/bus --operator-capability /owned/bus/operator.json
codex-wake --wake-root /owned/wake task-briefs approve \
  --task-id my-task --revision 1 \
  --bus-root /owned/bus --operator-capability /owned/bus/operator.json
codex-wake --wake-root /owned/wake task-briefs admit \
  --task-id my-task --assignment-id instruction-1 \
  --bus-root /owned/bus --operator-capability /owned/bus/operator.json
```

Inline `--brief-json` is an alternative to `--brief-file`. Caller adapters should
pass argument vectors directly, not interpolate JSON into shell commands.

Proposals and approvals are separate. An unapproved proposal cannot admit work;
copying approval prose is insufficient. Approval retains its actor and exact
revision. Assignment admission chooses the highest approved revision unless an
explicit approved revision is requested, then pins its task ID, revision, digest
and approval. A retry with the same assignment intent returns its original pin,
even after another revision is approved. Reusing an assignment key with changed
revision intent or actor is refused. Later instructions receive later approved
revisions; urgent stop/steer remains an explicit existing lifecycle operation.

Private version-1 state is kept beneath the configured Wake root in `task-briefs`,
independent of temporary worktrees. Per-task locking serializes proposal,
approval and admission. Atomic writes and directory sync preserve restart
recovery. Unknown state versions and unsafe/public state files hold. A managed
conversation ID is not required to name a task. Old assignments without brief
pins keep their existing semantics; missing pins never become retrospective
approval.

`TaskBriefStore.assignment_pin` returns the small exact link for assignment and
checkpoint projections. `validate_pin` checks a carried link against the durable
original admission and immutable approved revision. It does not broaden the
successor's authority or refresh resource counters. Existing lifecycle/checkpoint
integration is owned by the coordinator for this feature.
