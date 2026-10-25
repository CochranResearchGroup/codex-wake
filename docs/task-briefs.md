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

Workspace checks apply to the exact selected or pinned revision, including
retries. Inspection rejects a task history containing any revision outside the
worker workspace; it does not return partial history. Revision selection and
authorization share the task transaction.

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

## Compact delegated dispatch

New `sessions spawn` assignments, including plain `--task` instructions, deliver
one `BOUNDED_ASSIGNMENT` JSON packet to a fresh native thread. The packet includes
the objective, authority references, workspace/non-goals, acceptance, evidence
locators, original expiry and configured limits, stop conditions and a compact
return contract. A parent objective is a separate allowance reference; it does
not replace the delegated objective. No parent transcript, identity or capability
is copied. A brief supplies the approved task-specific acceptance and scope;
plain instructions use conservative report/partial-result defaults.

The optional `dispatch` field in a proposed brief supports:

```json
{
  "stop_conditions": ["Return partial evidence after one attempt"],
  "evidence_summaries": [{
    "path": "/approved/workspace/raw-evidence.json",
    "summary": "Two qualified observations",
    "observed_at": "2026-10-25T12:00:00Z",
    "coverage": "Only the named fixture",
    "ambiguity": "Other inputs remain unreviewed"
  }]
}
```

Each summary must name an existing `context` reference. Its observation time,
coverage and ambiguity are required, and raw evidence remains at the pinned
path/digest. Packets also carry the original admission's source status and time;
these are snapshots, including optional changed/unavailable sources, rather than
claims of current freshness. Sources should be rechecked before use.

Full-history context is an explicit exception: set
`dispatch.history` to `{"mode":"full_history","path":"/approved/workspace/history.json","reason":"Task-specific continuity need"}`.
The reason must be nonempty and the path must identify a required, digest-pinned
`context` source. It is recorded with the immutable approved revision and dispatch
receipt. The packet supplies its locator; it never automatically ingests that
file or copies it inline. Default mode is `compact`.

Packets are bounded to 64 KiB of rendered UTF-8. The lifecycle receipt's
`dispatch` exposes exact `input_bytes`, `input_sha256`, context mode and any
history reason. Exact native turn reconciliation adds `execution.output_summary`:
aggregate agent-message text bytes/count and up to 16 item locators, with explicit
coverage/truncation and the native thread/turn source. Bodies remain retrievable
from that native source. These are byte counts, not token or allocation savings.
Native completion still does not establish acceptance of the work.

The packet references existing allowance and control authority; it does not
renew resources or attest that a governor is active. If current governor state
is unavailable in the dispatch context it is explicitly `unknown`, with a
requirement to inspect through the authorized public operator interface. Existing
operator choices remain authoritative. Legacy expiry-only profiles remain
explicitly identified and acquire no token containment guarantee. Previously
admitted lifecycle intents retain their original task bytes and fingerprint on
retry, rather than being rewritten into a new format.
