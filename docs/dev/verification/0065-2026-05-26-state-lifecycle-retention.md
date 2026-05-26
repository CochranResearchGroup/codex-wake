# State Lifecycle And Retention

Date: 2026-05-26

Plan: `docs/dev/plans/0043-2026-05-26-productization-completion.md`

## Scope

Verify P43 Slice 3: runtime state classes, cleanup/archive/unenroll command
effects, stale supervisor-root remediation, and dry-run cleanup behavior.

## Documentation

Added `docs/runtime-state-lifecycle.md`.

The document classifies:

- active wake records
- terminal wake records
- archived wake records
- hook ack records
- wake/event logs
- pane locks
- monitor health
- supervisor registry entries
- service units/logs
- OpenClaw plugin materialized source

It also documents the effects of:

- `codex-wake archive <wake-id>`
- `codex-wake archive --all-terminal`
- `codex-wake cleanup --older-than <duration>`
- `codex-wake cleanup --archive-terminal --json`
- `codex-wake cleanup --delete`
- `codex-wake supervisor unenroll --root-id <id>`
- `codex-wake supervisor unenroll --wake-root <path>`

Updated README and the `codex-wake` skill to point operators to cleanup,
state lifecycle, and stale-root remediation behavior.

## Stale Root Visibility

`codex-wake supervisor status --json` now reports each root with:

- `health_status`: `ready`, `stale`, or `missing`
- `health_recent`
- `remediation`

Live status for this repo:

```json
{
  "service": {
    "active": "active",
    "enabled": "enabled",
    "name": "codex-wake-supervisor.service"
  },
  "root_count": 1,
  "roots": [
    {
      "root_id": "codex-wake-98975473",
      "health_status": "ready",
      "health_recent": true,
      "remediation": "",
      "wake_root": "/home/ecochran76/workspace.local/codex-wake/.codex/wake"
    }
  ]
}
```

Unit tests cover stale and missing health remediation strings.

## Cleanup Dogfood

Disposable wake-root dogfood:

```bash
root="$(mktemp -d)/wake"
wake=$(PYTHONPATH=src python -m codex_wake.cli --wake-root "$root" \
  after --app-server-thread-id thread_cleanup 1m -- 'P43 Slice 3 cleanup dogfood' | awk '{print $1}')
PYTHONPATH=src python -m codex_wake.cli --wake-root "$root" cancel "$wake"
PYTHONPATH=src python -m codex_wake.cli --wake-root "$root" cleanup --archive-terminal --older-than 30d --json
```

The first cleanup pass archived the terminal wake and matched no archived
records under the 30-day window:

```json
{
  "mode": "dry-run",
  "archive_terminal": true,
  "archived_terminal_count": 1,
  "matched_count": 0
}
```

After setting the archived record's retention timestamp to
`2026-04-01T00:00:00Z`, dry-run cleanup showed the deletion candidate without
removing it:

```json
{
  "mode": "dry-run",
  "matched_count": 1,
  "matched": [
    {
      "deleted": false,
      "retention_at": "2026-04-01T00:00:00Z"
    }
  ]
}
```

The delete pass removed the same archived record only after `--delete`:

```json
{
  "mode": "delete",
  "matched_count": 1,
  "matched": [
    {
      "deleted": true,
      "retention_at": "2026-04-01T00:00:00Z"
    }
  ]
}
```

Final status for the disposable wake root:

```json
{
  "active_total": 0,
  "terminal_total": 0,
  "archived_total": 0,
  "counts_by_status": {
    "archived": 0,
    "cancelled": 0,
    "expired": 0,
    "failed": 0,
    "firing": 0,
    "pending": 0,
    "submitted": 0
  }
}
```

## Source Validation

Focused validation:

```bash
PYTHONPATH=src python -m unittest tests.test_supervisor tests.test_cli
```

Outcome: passed, 49 tests.

## Known Gap

This verifies P43 Slice 3. The broader P43 DOD remains open: cross-runtime
smoke harness, operator-doc consolidation, and the productization release are
not complete.
