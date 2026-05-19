# Event Predicates

Date: 2026-05-19
Lane: P17

## Scope

Validate `file_changed` and `process_done` predicates without live tmux dispatch.

## Source Validation

Commands:

```bash
python -m compileall -q src tests .codex/hooks
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
```

Outcome:

- `51` tests passed.

Coverage added:

- `codex-wake changed <path>` stores registration-time mtime/size when the path exists.
- `codex-wake changed <path>` can register a missing path and fire when it is created.
- `codex-wake pid <pid>` stores a `process_done` predicate for a live PID.
- `file_changed` stays pending until mtime or size differs.
- `file_changed` fires when a missing watched file is created.
- `process_done` stays pending while a process exists.
- `process_done` fires after the process exits.
- Invalid `process_done` predicates fail with `last_error`.

## CLI Smoke

Commands:

```bash
ROOT=/tmp/codex-wake-p17-smoke
rm -rf "$ROOT"
mkdir -p "$ROOT/repo/.codex/events" "$ROOT/wake"
cd "$ROOT/repo"
export PYTHONPATH=/home/ecochran76/workspace.local/codex-wake/src
export TMUX_PANE='%11'
export TMUX='/tmp/tmux-1000/default,123,0'

printf before > .codex/events/build.log
python -m codex_wake.cli --wake-root "$ROOT/wake" changed .codex/events/build.log -- 'Build log changed'
python -m codex_wake.daemon --wake-root "$ROOT/wake" --once --no-dispatch
printf after-value > .codex/events/build.log
python -m codex_wake.daemon --wake-root "$ROOT/wake" --once --no-dispatch
python -m codex_wake.cli --wake-root "$ROOT/wake" list

sleep 5 &
PID=$!
python -m codex_wake.cli --wake-root "$ROOT/wake" pid "$PID" -- 'Process done'
python -m codex_wake.daemon --wake-root "$ROOT/wake" --once --no-dispatch
kill "$PID"
wait "$PID" 2>/dev/null || true
python -m codex_wake.daemon --wake-root "$ROOT/wake" --once --no-dispatch
python -m codex_wake.cli --wake-root "$ROOT/wake" list
```

Outcome:

```text
checked=1 fired=0 failed=0 pending=1 dispatched=0 submitted=0 requeued=0
checked=1 fired=1 failed=0 pending=0 dispatched=0 submitted=0 requeued=0
ID                                  STATUS  PREDICATE      NEXT
wake_20260519_150257_9188           firing  file_changed   2026-05-19T15:02:57Z

checked=1 fired=0 failed=0 pending=1 dispatched=0 submitted=0 requeued=0
checked=1 fired=1 failed=0 pending=0 dispatched=0 submitted=0 requeued=0
ID                                  STATUS  PREDICATE      NEXT
wake_20260519_150257_9188           firing  file_changed   2026-05-19T15:02:57Z
wake_20260519_150258_32a8           firing  process_done   2026-05-19T15:02:58Z
```

## Known Limits

- `process_done` checks PID liveness only and does not yet guard against PID reuse.
- `file_changed` uses mtime/size polling rather than inotify.
- Live tmux dispatch was intentionally not part of this predicate validation.

## Result

Pass. P17 is closed.
