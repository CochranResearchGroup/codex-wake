# Runtime State Lifecycle

This document classifies Codex Wake runtime state and explains what operator
cleanup commands can and cannot remove.

## State Classes

| State class | Default location | Authority | Cleanup behavior |
| --- | --- | --- | --- |
| Active wake records | `.codex/wake/pending/`, `.codex/wake/firing/` | Authoritative. These records define work the daemon may still evaluate or dispatch. | Never deleted by `cleanup`. Cancel first when a wake should not fire. |
| Terminal wake records | `.codex/wake/submitted/`, `.codex/wake/failed/`, `.codex/wake/cancelled/`, `.codex/wake/expired/` | Authoritative outcome records until archived. | `archive <wake-id>` or `archive --all-terminal` moves them to `archive/`. `cleanup` never deletes them directly. |
| Archived wake records | `.codex/wake/archive/` | Durable historical evidence. | `cleanup` previews old archived records by default and deletes only with `--delete`. |
| Hook ack records | `.codex/wake/acks/` | Durable delivery evidence for Codex hook submission. | Not deleted by `cleanup`; retain or prune manually according to local evidence policy. |
| Wake logs and event logs | `.codex/wake/logs/`, `.codex/events/` | Ephemeral or operator-created evidence, depending on the workflow. | Not deleted by `cleanup`; preserve if referenced by a wake record or verification note. |
| Pane locks | `.codex/wake/locks/` | Ephemeral concurrency guard. | Removed by the daemon when stale; not a durable outcome record. |
| Monitor health | `~/.local/state/codex-wake/monitors/*.json` | Derived readiness evidence written by daemon/supervisor loops. | Recreated by active monitors. Stale or missing health is surfaced by `monitor check`, `supervisor status`, and `product-readiness`. |
| Supervisor registry entries | `~/.config/codex-wake/roots.d/*.json` | Authoritative list of wake roots the user supervisor should poll. | Removed by `codex-wake supervisor unenroll`; this does not delete wake records. |
| Service units and service logs | `~/.config/systemd/user/*.service`, `~/.local/state/codex-wake/*.log` | User-scoped runtime configuration and operational logs. | Managed by `service uninstall` or `supervisor uninstall`; logs are retained unless manually removed. |
| OpenClaw plugin materialized source | `~/.local/share/codex-wake/openclaw-plugins/<tag>/` | Derived install source for OpenClaw plugin installation. | Safe to replace with `openclaw-plugin update --refresh`; do not treat as wake state. |

Tracked repo files should contain schemas, docs, tests, and examples only.
Human-private prompts, raw transcripts, credentials, live wake records, and
tenant-specific logs stay in runtime locations.

## Command Effects

`codex-wake archive <wake-id>`:

- Requires a terminal wake status: `submitted`, `failed`, `cancelled`, or
  `expired`.
- Moves the record to `.codex/wake/archive/<wake-id>.json`.
- Sets `status=archived`, records `previous_status`, writes `archived_at`, and
  appends an `archived` event.
- Does not remove hook ack files, logs, monitor health, or supervisor registry
  entries.

`codex-wake archive --all-terminal`:

- Applies the same archive operation to all terminal wake records.
- Skips active `pending` and `firing` records.

`codex-wake cleanup --older-than <duration>`:

- Is dry-run by default.
- Scans only `.codex/wake/archive/`.
- Reports matching archived records with the retention timestamp that made them
  eligible.
- Does not delete anything unless `--delete` is present.

`codex-wake cleanup --archive-terminal --json`:

- Archives terminal wake records first.
- Then evaluates archived records against the retention window.
- Produces a structured preview containing `archived_terminal` and `matched`
  entries.

`codex-wake cleanup --delete`:

- Deletes only matched archived records.
- Never deletes active wake records, non-archived terminal records, ack files,
  logs, monitor health, or supervisor registry entries.

`codex-wake supervisor unenroll --root-id <id>` or
`codex-wake supervisor unenroll --wake-root <path>`:

- Removes the supervisor registry entry for that root.
- Stops the user supervisor from polling that wake root.
- Does not delete `.codex/wake/` records, archives, acks, logs, or monitor
  health files.

## Stale Roots

`codex-wake supervisor status --json` reports each registered root with
`health_status`:

- `ready`: recent monitor health exists.
- `stale`: prior health exists but is older than the readiness window.
- `missing`: no health has been observed for that registered root.

Each stale or missing root includes a `remediation` string. Use it to choose
between repairing the supervisor loop with `codex-wake supervisor run --once`
or removing obsolete registrations with `codex-wake supervisor unenroll`.

## Clean Closeout

For dogfood or release evidence, close a wake lane with:

```bash
codex-wake --wake-root .codex/wake cleanup --archive-terminal --json
codex-wake --wake-root .codex/wake status --json
```

The closeout target is:

- `active_total=0`
- `terminal_total=0`

Archived evidence may remain and is counted separately as `archived_total`.
