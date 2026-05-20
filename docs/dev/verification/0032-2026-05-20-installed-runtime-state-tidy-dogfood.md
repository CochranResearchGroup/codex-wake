# Installed Runtime State Tidy Dogfood Verification

Date: 2026-05-20

## Scope

Dogfood the installed cleanup surface against the repo-local wake root after live-dispatch testing.

## Baseline

The initial installed command was stale:

```text
codex-wake v0.4.7
```

That surface rejected the planned JSON cleanup command:

```text
codex-wake: error: unrecognized arguments: --json
```

The installed tool was refreshed from the public release tag:

```text
uv tool install --force 'git+https://github.com/CochranResearchGroup/codex-wake.git@v0.4.8'
```

After refresh, `uv tool list` reported:

```text
codex-wake v0.4.8
```

The cleanup help included `--json`.

Baseline repo wake status before cleanup:

```json
{
  "active_total": 0,
  "archived_total": 2,
  "counts_by_status": {
    "archived": 2,
    "cancelled": 2,
    "expired": 0,
    "failed": 1,
    "firing": 0,
    "pending": 0,
    "submitted": 1
  },
  "earliest_next_attempt_at": "",
  "terminal_total": 4,
  "total": 6
}
```

## Cleanup

Ran the installed cleanup surface:

```text
codex-wake --wake-root .codex/wake cleanup --archive-terminal --json
```

Output:

```json
{
  "archive_terminal": true,
  "archived_terminal": [
    {
      "path": "/home/ecochran76/workspace.local/codex-wake/.codex/wake/archive/wake_20260519_030204_9085.json",
      "wake_id": "wake_20260519_030204_9085"
    },
    {
      "path": "/home/ecochran76/workspace.local/codex-wake/.codex/wake/archive/wake_20260519_031211_5457.json",
      "wake_id": "wake_20260519_031211_5457"
    },
    {
      "path": "/home/ecochran76/workspace.local/codex-wake/.codex/wake/archive/wake_20260519_033023_e611.json",
      "wake_id": "wake_20260519_033023_e611"
    },
    {
      "path": "/home/ecochran76/workspace.local/codex-wake/.codex/wake/archive/wake_20260519_104518_d191.json",
      "wake_id": "wake_20260519_104518_d191"
    }
  ],
  "archived_terminal_count": 4,
  "matched": [],
  "matched_count": 0,
  "mode": "dry-run",
  "older_than": "30d"
}
```

No archived records were deleted because `--delete` was not passed.

## Final State

Final `status --json` reported:

```json
{
  "active_total": 0,
  "archived_total": 6,
  "counts_by_status": {
    "archived": 6,
    "cancelled": 0,
    "expired": 0,
    "failed": 0,
    "firing": 0,
    "pending": 0,
    "submitted": 0
  },
  "earliest_next_attempt_at": "",
  "terminal_total": 0,
  "total": 6
}
```

The wake root now contains six archived wake JSON records and no non-archived terminal wake JSON records.

## Outcome

Pass after refreshing the installed tool. The current cleanup surface is sufficient for this repo-local tidy workflow: terminal records can be archived in one structured dry-run-safe command, archived evidence is retained, and `status --json` becomes concise again.

## Follow-Up

The product gap is installation freshness, not cleanup semantics. Future release closeout should verify the user-scoped `uv tool` installation is refreshed when a dogfood lane depends on newly released CLI flags.
