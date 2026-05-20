# Live Dispatch Dogfood Verification

Date: 2026-05-20

## Scope

Verify one controlled live tmux dispatch from the installed `codex-wake` and `codex-waked` runtime against the active Codex TUI pane.

## Wake

- Wake id: `wake_20260520_214519_1ee0`
- Wake root: `.codex/wake`
- Target transport: `tmux`
- Target pane: `%202`
- Predicate: `not_before`
- Due at: `2026-05-20T21:46:04Z`

## Commands And Evidence

Created the wake:

```text
codex-wake --wake-root .codex/wake after 45s -- 'P27 live-dispatch dogfood. First verify whether this wake has already been handled. Inspect .codex/wake, status --json, and ack evidence. Record outcome and stop.'
```

Scheduled the one-shot dispatcher:

```text
systemd-run --user --unit=codex-wake-p27-live-wake_20260520_214519_1ee0 --on-active=55s /home/ecochran76/.local/bin/codex-waked --wake-root /home/ecochran76/workspace.local/codex-wake/.codex/wake --once --ack-timeout 15
```

Pre-dispatch `status --json` reported:

```json
{
  "active_total": 1,
  "counts_by_status": {
    "pending": 1
  },
  "earliest_next_attempt_at": "2026-05-20T21:46:04Z"
}
```

The wake-triggered turn verified that the current time was after the due predicate:

```text
2026-05-20T21:46:37Z
```

The submitted wake record included these events:

```json
[
  {
    "at": "2026-05-20T21:46:18Z",
    "message": "not_before due_at 2026-05-20T21:46:04Z matched",
    "type": "predicate_matched"
  },
  {
    "at": "2026-05-20T21:46:18Z",
    "attempt": 1,
    "message": "Pasting canonical wake prompt into tmux pane %202",
    "type": "dispatch_attempt"
  },
  {
    "at": "2026-05-20T21:46:18Z",
    "message": "Wake prompt submission ack observed",
    "type": "ack_observed"
  }
]
```

The hook ack file `.codex/wake/acks/wake_20260520_214519_1ee0.submitted` reported:

```json
{
  "session_id": "019e3c37-6dbf-70a0-bbaf-0668ed98ecc3",
  "submitted_at": "2026-05-20T21:46:18Z",
  "turn_id": "019e475a-9211-7a82-a3f7-14536ba24806",
  "wake_id": "wake_20260520_214519_1ee0"
}
```

The user journal for the transient dispatcher reported:

```text
checked=1 fired=1 failed=0 pending=0 dispatched=1 submitted=1 requeued=0
```

After archiving the submitted dogfood wake, `status --json` reported:

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
  "earliest_next_attempt_at": ""
}
```

The archived record is `.codex/wake/archive/wake_20260520_214519_1ee0.json` with `previous_status` set to `submitted`.

## Outcome

Pass. The installed runtime registered a durable wake, the one-shot daemon evaluated the due predicate, pasted the canonical prompt into the live tmux pane, observed the hook ack, moved the record to `submitted`, and the operator archived it with no active dogfood wake left behind.

## Gaps

- The transient systemd service was collected by the time `systemctl status` was queried, so journal evidence is the durable service outcome captured here.
- This verifies one live tmux path only. App-server-backed dispatch remains a separate future lane.
