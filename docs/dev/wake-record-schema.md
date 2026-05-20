# Wake Record Schema

Current schema version: `1`

Wake records are durable runtime records stored as JSON. They are operational state, not source artifacts. Schema version `1` is an additive object contract: readers must tolerate unknown fields, and optional fields may be absent.

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
- `max_attempts`: bounded retry limit.
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
  "thread_id": "thread_abc"
}
```

Only `stdio://` app-server dispatch is implemented in schema version `1`.

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
- `dispatch_result`: accepted app-server `thread_id` and `turn_id` metadata when returned.

Event objects may also include extra metadata such as accepted app-server turn identifiers.

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
