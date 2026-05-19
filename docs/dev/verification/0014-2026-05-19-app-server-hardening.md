# App-Server Hardening

Date: 2026-05-19
Lane: P18

## Scope

Validate explicit app-server wake creation and accepted turn metadata capture without requiring a live app-server thread.

## Source Validation

Commands:

```bash
python -m compileall -q src tests .codex/hooks
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
```

Outcome:

- `53` tests passed.

Coverage added:

- `codex-wake app after <thread-id> <duration> -- <prompt>` creates an app-server target without tmux environment.
- `codex-wake app after --endpoint ws://...` rejects non-stdio endpoints.
- App-server dispatch writes a `dispatch_attempt` event before request execution.
- App-server dispatch preserves accepted `thread_id` and `turn_id` in `dispatch_result` when returned by `thread/resume` and `turn/start`.
- App-server `ack_observed` event includes accepted turn metadata.

## CLI Smoke

Commands:

```bash
ROOT=/tmp/codex-wake-p18-smoke
rm -rf "$ROOT"
mkdir -p "$ROOT/wake"
PYTHONPATH=src python -m codex_wake.cli --wake-root "$ROOT/wake" app after thread_smoke 1m -- 'App smoke after'
PYTHONPATH=src python -m codex_wake.cli --wake-root "$ROOT/wake" app at thread_smoke '2026-05-19T17:30:00-05:00' -- 'App smoke at'
PYTHONPATH=src python -m codex_wake.cli --wake-root "$ROOT/wake" list --json
```

Outcome:

- Both commands created `pending` records.
- Both records used target:

```json
{
  "transport": "app-server",
  "endpoint": "stdio://",
  "thread_id": "thread_smoke"
}
```

- The `app after` wake stored a relative `not_before` predicate.
- The `app at` wake stored an absolute UTC `not_before` predicate.

## Known Limits

- Validation uses a fake app-server client for accepted turn metadata rather than a live Codex app-server thread.
- Non-stdio app-server endpoints remain intentionally unsupported.
- CI does not exercise live app-server dispatch.

## Result

Pass. P18 is closed.
