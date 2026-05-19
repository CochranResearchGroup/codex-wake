# PID Reuse Safety

Date: 2026-05-19
Lane: P19

## Scope

Validate PID identity capture and `process_done` daemon behavior without requiring live tmux dispatch.

## Source Validation

Commands:

```bash
python -m compileall -q src tests .codex/hooks
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
```

Outcome:

- `61` tests passed.
- Compileall passed.

Coverage added:

- Linux `/proc/<pid>/stat` start-time parsing.
- Boot id capture from `/proc/sys/kernel/random/boot_id`.
- `codex-wake pid <pid>` records `registered_start_time_ticks` and `registered_boot_id` when available.
- `codex-wake pid <pid>` keeps the PID-only fallback when identity is unavailable.
- Existing PID-only `process_done` records still use liveness fallback.
- Matching process identity stays pending.
- Mismatched process identity moves to `firing`.
- Boot id mismatch moves to `firing`.
- Invalid registered identity moves to `failed` with `last_error`.

## Source CLI Smoke

Commands:

```bash
ROOT=/tmp/codex-wake-p19-smoke
sleep 30 &
PID=$!
PYTHONPATH=src python -m codex_wake.cli --wake-root "$ROOT/wake" pid "$PID" -- 'P19 process done smoke'
PYTHONPATH=src python -m codex_wake.cli --wake-root "$ROOT/wake" list --json
PYTHONPATH=src python -m codex_wake.daemon --wake-root "$ROOT/wake" --once --no-dispatch
kill "$PID"
wait "$PID" 2>/dev/null || true
PYTHONPATH=src python -m codex_wake.daemon --wake-root "$ROOT/wake" --once --no-dispatch
PYTHONPATH=src python -m codex_wake.cli --wake-root "$ROOT/wake" list
```

Outcome:

```text
identity_recorded=true
boot_id_recorded=true
checked=1 fired=0 failed=0 pending=1 dispatched=0 submitted=0 requeued=0
checked=1 fired=1 failed=0 pending=0 dispatched=0 submitted=0 requeued=0
wake_20260519_220112_ae37 firing process_done
```

## Installed-Wheel Smoke

Commands:

```bash
python -m venv /tmp/codex-wake-p19-build
/tmp/codex-wake-p19-build/bin/python -m pip install --upgrade pip build
/tmp/codex-wake-p19-build/bin/python -m build
python -m venv /tmp/codex-wake-p19-install
/tmp/codex-wake-p19-install/bin/python -m pip install --upgrade pip
/tmp/codex-wake-p19-install/bin/python -m pip install dist/*.whl
ROOT=/tmp/codex-wake-p19-installed-smoke
sleep 30 &
PID=$!
/tmp/codex-wake-p19-install/bin/codex-wake --wake-root "$ROOT/wake" pid "$PID" -- 'Installed P19 process done smoke'
/tmp/codex-wake-p19-install/bin/codex-wake --wake-root "$ROOT/wake" list --json
/tmp/codex-wake-p19-install/bin/codex-waked --wake-root "$ROOT/wake" --once --no-dispatch
kill "$PID"
wait "$PID" 2>/dev/null || true
/tmp/codex-wake-p19-install/bin/codex-waked --wake-root "$ROOT/wake" --once --no-dispatch
/tmp/codex-wake-p19-install/bin/codex-wake --wake-root "$ROOT/wake" list
```

Outcome:

```text
installed_identity_recorded=true
installed_boot_id_recorded=true
checked=1 fired=0 failed=0 pending=1 dispatched=0 submitted=0 requeued=0
checked=1 fired=1 failed=0 pending=0 dispatched=0 submitted=0 requeued=0
wake_20260519_220139_36b0 firing process_done
```

## Known Limits

- PID identity capture is best-effort. Non-Linux platforms and restricted `/proc` surfaces fall back to PID liveness.
- The smoke validates identity capture and normal process exit on this host; synthetic unit tests cover reused-PID identity mismatch.
- CI does not force a real PID reuse event.

## Result

Pass. P19 is closed.
