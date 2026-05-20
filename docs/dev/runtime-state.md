# Runtime State

Codex Wake runtime state lives under `.codex/wake/` by default. This directory is ignored by git and is not a source-controlled product artifact.

Wake records use the schema contract documented in [Wake Record Schema](wake-record-schema.md). The installed CLI reports the active schema with:

```bash
codex-wake schema
codex-wake schema --json
```

## Directory Classes

- `pending/`: authoritative active wake records awaiting predicate match.
- `firing/`: authoritative active wake records currently being dispatched or awaiting ack.
- `submitted/`: terminal wake records with observed hook ack.
- `failed/`: terminal wake records that could not be completed.
- `cancelled/`: terminal wake records cancelled by an operator.
- `expired/`: terminal wake records that exceeded an expiry policy.
- `acks/`: derived ack files written by the Codex hook.
- `logs/`: ephemeral operational logs.
- `locks/`: ephemeral pane lock files.
- `archive/`: retained terminal wake records moved out of active status directories.

## Retention Rules

- Active records in `pending/` and `firing/` must not be archived.
- Terminal records in `submitted/`, `failed/`, `cancelled/`, and `expired/` may be archived.
- Archiving preserves the JSON record, appends an `archived` event, sets `previous_status`, and moves the record to `archive/`.
- Cleanup prunes only records already under `archive/`.
- Cleanup is dry-run by default and requires `--delete` before removing archived records.
- Cleanup uses `archived_at`, then `updated_at`, then `created_at` as the retention timestamp.
- `acks/` are derived evidence. They may be retained while debugging, but the authoritative wake outcome is the wake record.
- Ack files are the only local proof that `UserPromptSubmit` ran after a wake prompt was submitted. Absence of an ack means hook execution is unknown, not that tmux injection failed.
- `logs/` and `locks/` are operational artifacts and should not be treated as durable source of truth.

## Safety Rules

Wake records must not contain:

- raw credentials or API keys
- raw private transcripts
- shell commands to execute
- broad dumps of private user data

Use paths and short task context instead of embedding large private content. A wake should point the resumed agent at logs, event files, or review artifacts that are already appropriate for the workspace.

## Commands

List active wakes:

```bash
codex-wake list
```

List active and archived wakes:

```bash
codex-wake list --archived
```

Archive one terminal wake:

```bash
codex-wake archive wake_20260518_153000_9f3a
```

Archive all terminal wakes:

```bash
codex-wake archive --all-terminal
```

Preview archived records older than the default retention window:

```bash
codex-wake cleanup
```

Delete archived records older than a retention window:

```bash
codex-wake cleanup --older-than 30d --delete
```

Archive terminal records before cleanup evaluation:

```bash
codex-wake cleanup --archive-terminal --older-than 30d
```
