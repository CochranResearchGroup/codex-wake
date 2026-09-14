# Wake Record Schema

Default write schema version: `1`

Supported read schema versions: `1`, `2`

Wake records are durable runtime records stored as JSON. They are operational state, not source artifacts. Schema version `1` remains the default for the existing timer, file, process, CLI, and plugin writers. Schema version `2` is reserved for capability-gated signal records backed by the root-local signal journal. A schema-v1 record whose predicate claims `type: signal`, an unknown version, or a malformed schema-v2 record is held rather than evaluated through the legacy predicate path.

## Signal Record Version 2

A signal record adds the required top-level fields `arm_id`, `journal_uuid`,
and `record_revision`. Its predicate has `type: signal`, contract version `1`,
the same `arm_id`, source and source-instance routing, occurrence or state
semantics, bounded `eq`/`in` clauses, verification policy, and its durable
registration anchor. IDs use the runtime's restricted safe identifier grammar;
path separators and dot segments are invalid.

The journal lives at `signals/journal.sqlite3` beneath the resolved wake root.
Registration commits a prepared arm and exact JSON outbox payload, durably
publishes and verifies revision 1 under `pending/`, and only then marks the arm
published. A match reservation and exact revision-2 firing payload commit in
one SQLite transaction. Publication uses a unique temporary file, file and
directory synchronization, atomic replacement, and pending-directory
synchronization after removal.

Revision 2 firing records include a bounded `trigger_match` with the stable
match token, receipt identity and local sequence, sanitized evidence reference
and attributes, verification state and method, match time, and evidence digest.
Dispatch revalidates the complete record against the applied outbox payload,
published arm, journal identity, lifecycle, and reservation before any target
transport is called.

Signal publication requires a recent managed-reader capability bound to the
exact root, process ID, process start identity, boot ID, reader generation, and
schema support. Static schema output describes binary support but is not
runtime authority. Missing, corrupt, mismatched, stale, or unsupported
authority fails closed. Opening a missing journal for daemon polling or CLI
inspection does not create it.

Cancellation and dispatch share a root-and-wake lifecycle lock. Terminal
tombstones prevent stale pending or firing copies from restoring eligibility;
archived signal evidence is deleted only after durable terminal fencing and
pin release. Startup reconciliation is bounded and may repair exact outbox
payloads, but never derives live authority from JSON alone.

## Required Top-Level Fields

- `schema_version`: integer schema version.
- `id`: stable wake id.
- `created_at`: UTC timestamp.
- `updated_at`: UTC timestamp.
- `cwd`: creating working directory.
- `target`: dispatch target object.
- `predicate`: trigger predicate object.
- `prompt`: wake instruction text.
- `status`: wake status.
- `attempts`: dispatch attempt count.
- `max_attempts`: bounded retry limit. Schema-v2 signal registrations default
  to `3`; supported callers may select an integer from `1` through `100`, and
  the selected value participates in idempotency identity.
- `ack_timeout_seconds`: ack wait limit.
- `next_attempt_at`: UTC timestamp for the next dispatch attempt or predicate check.
- `events`: ordered audit events.

## Status Vocabulary

Active statuses:

- `pending`
- `firing`

Terminal statuses:

- `submitted`
- `failed`
- `cancelled`
- `expired`

Archived status:

- `archived`

Status directory names match these values, except archived records live in `archive/`.

## Target Variants

Tmux target:

```json
{
  "transport": "tmux",
  "tmux_socket": "/tmp/tmux-1000/default",
  "pane": "%11"
}
```

App-server target:

```json
{
  "transport": "app-server",
  "endpoint": "stdio://",
  "thread_id": "thread_abc",
  "codex_cmd": "/home/you/.local/bin/codex",
  "retry_active_writer": true
}
```

Only `stdio://` app-server dispatch is implemented in schema version `1`.
`codex_cmd` is optional and may be absent. When present, it is a validated
Codex CLI command or absolute path used by the daemon to launch local stdio
app-server dispatch. Generated service and supervisor configuration preserves
stable symlink spellings and rejects paths tied to version-managed Node
installations.

`retry_active_writer` is an optional boolean. Missing or `false` means an
active writer causes terminal wake failure after preflight. `true` permits
bounded requeue under the record's `max_attempts` and app-server backoff
schedule. Neither policy permits `turn/start` while the thread is active.

OpenClaw Gateway target:

```json
{
  "transport": "openclaw_gateway",
  "gateway": {
    "url": "ws://127.0.0.1:18789",
    "token_env": "OPENCLAW_GATEWAY_TOKEN"
  },
  "openclaw": {
    "agent_id": "main",
    "session_key": "agent:main:slack:channel:c0ahqqcg7j4",
    "channel": {
      "provider": "slack",
      "workspace": "default",
      "channel_id": "C0AHQQCG7J4",
      "thread_ts": "1779729958.218239"
    }
  },
  "dispatch": {
    "deliver": false,
    "timeout_seconds": 120,
    "gateway_timeout_ms": 180000
  },
  "openclaw_cmd": "/home/you/.local/bin/openclaw"
}
```

`openclaw_gateway` targets require a durable `agent:<agent_id>:...`
`session_key`. Channel fields are evidence and validation aids, not a
substitute for the session key. Gateway auth fields name environment variables;
they must not store token or password values. Dispatch sends a short
`WAKE_TRIGGER_ID=...` handoff prompt that points the OpenClaw agent back to the
durable wake record instead of embedding the original prompt text.

## Predicate Variants

Wall-clock predicate:

```json
{
  "type": "not_before",
  "due_at": "2026-05-18T21:15:00Z"
}
```

File-exists predicate:

```json
{
  "type": "file_exists",
  "path": ".codex/events/pytest.done"
}
```

File-changed predicate:

```json
{
  "type": "file_changed",
  "path": ".codex/events/build.log",
  "registered_exists": true,
  "registered_mtime_ns": 123,
  "registered_size": 456
}
```

Process-done predicate:

```json
{
  "type": "process_done",
  "pid": 12345,
  "registered_start_time_ticks": 987654,
  "registered_boot_id": "optional-linux-boot-id"
}
```

For `process_done`, `registered_start_time_ticks` and `registered_boot_id` are optional best-effort identity fields. Older PID-only records remain valid and fall back to PID liveness.

## Optional Fields

Current optional fields include:

- `context_paths`: paths the resumed agent should inspect.
- `evidence_paths`: log, marker, or evidence paths related to the wake.
- `last_error`: terminal failure detail.
- `previous_status`: status before archival.
- `archived_at`: archive timestamp.
- `dispatch_result`: accepted app-server `thread_id` and `turn_id` metadata
  when returned; for OpenClaw Gateway dispatch, sanitized Gateway metadata
  such as `run_id`, `status`, `summary`, `session_id`, provider/model, payload
  counts, and text summaries. It must not store raw assistant transcript text.
- `visibility_result`: sanitized tmux operator-visibility evidence when checked.
- app-server target `codex_cmd`: optional command path for launching local
  stdio app-server dispatch.
- app-server target `retry_active_writer`: optional boolean enabling bounded
  retry when preflight observes an active writer; absence means fail-fast.
- OpenClaw Gateway target `openclaw_cmd`: optional command path for launching
  local Gateway dispatch through the OpenClaw CLI.

Event objects may also include extra metadata such as accepted app-server turn
identifiers or `created_by` provenance. The OpenClaw plugin uses
`created_by: "openclaw-plugin:codex-wake"` on the initial `created` event.

## Tmux Visibility Result

Tmux-submitted records may include a `visibility_result` object:

```json
{
  "transport": "tmux",
  "pane": "%11",
  "checked_at": "2026-05-23T16:30:00Z",
  "privacy": "raw_pane_text_not_stored",
  "classification": "visible_prompt_observed",
  "pre_capture": {
    "line_count": 45,
    "wake_marker_present": false
  },
  "post_capture": {
    "line_count": 46,
    "wake_marker_present": true
  },
  "post_marker_new": true
}
```

Classification values:

- `visible_prompt_observed`: the wake marker was absent before dispatch and
  present after ack.
- `ack_observed_visibility_unproven`: the hook ack was observed, but pane
  marker evidence did not prove a new visible prompt.
- `visibility_check_failed`: ack was observed, but post-ack tmux capture failed.

`visibility_result` deliberately stores counts, booleans, and classification
only. It must not store raw pane text or transcript content.

## Derived Ack Files

Ack files under `.codex/wake/acks/*.submitted` are derived evidence written by the Codex hook. They are not authoritative wake records and do not change the wake record schema version.

Ack files currently include:

- `wake_id`
- `submitted_at`
- `turn_id`
- `session_id`

## Compatibility Policy

Schema version `1` allows additive optional fields. A schema bump is not required for:

- adding optional top-level metadata
- adding optional predicate metadata with a fallback path
- adding event metadata
- adding derived diagnostic output outside the wake record
- adding CLI commands that read existing records without changing required fields

A schema bump is required for:

- renaming or removing required fields
- changing existing field meaning incompatibly
- making an optional field required for existing predicate records
- changing the status vocabulary or status directory layout incompatibly
- changing target transport semantics incompatibly
- changing predicate semantics so existing records would fire or fail differently without an explicit migration

Any schema bump must include a release note, validation evidence, and a migration or compatibility plan.

Schema version `2` does not replace or migrate ordinary schema-v1 records.
Mixed roots continue to evaluate valid v1 predicates when signal authority is
unavailable. Existing writers, including the OpenClaw plugin, remain on v1.
Managed downgrade must refuse active or recoverable v2 state; this contract
does not claim that an arbitrary unmanaged legacy process can be prevented
from reading files outside the managed-runtime boundary.
