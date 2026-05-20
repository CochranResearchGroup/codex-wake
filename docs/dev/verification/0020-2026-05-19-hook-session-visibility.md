# Hook Session Visibility

Date: 2026-05-19
Lane: P21

## Scope

Validate hook diagnostics that separate repo-local hook config from runtime ack evidence.

## Source Validation

Commands:

```bash
python -m compileall -q src tests .codex/hooks
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
```

Outcome:

- `68` tests passed.
- Compileall passed.

Coverage added:

- Hook runtime evidence reports `unknown_without_ack` when no ack files exist.
- Hook runtime evidence reports `observed_ack` when a submitted ack exists.
- Latest ack wake id, submitted timestamp, session id, and path are surfaced.
- `hook check` prints runtime ack evidence.
- `doctor` prints runtime ack evidence.

## Source CLI Smoke

Commands:

```bash
ROOT=/tmp/codex-wake-p21-source
PYTHONPATH=src python -m codex_wake.cli --wake-root "$ROOT/wake" hook install --repo-root "$ROOT/repo"
PYTHONPATH=src python -m codex_wake.cli --wake-root "$ROOT/wake" hook check --repo-root "$ROOT/repo"
printf '{"wake_id":"wake_seen","submitted_at":"2026-05-19T21:30:00Z","session_id":"session_seen"}\n' > "$ROOT/wake/acks/wake_seen.submitted"
PYTHONPATH=src python -m codex_wake.cli --wake-root "$ROOT/wake" hook check --repo-root "$ROOT/repo"
PYTHONPATH=src python -m codex_wake.cli --wake-root "$ROOT/wake" doctor --repo-root "$ROOT/repo"
```

Outcome:

```text
hook_ack_count=0
hook_active_session_loaded=unknown_without_ack
hook_ack_count=1
hook_active_session_loaded=observed_ack
hook_latest_ack_wake_id=wake_seen
hook_latest_ack_session_id=session_seen
hook_loaded_note=ack evidence proves a hook ran only after a wake prompt was submitted
```

## Installed-Wheel Smoke

Commands:

```bash
python -m venv /tmp/codex-wake-p21-build
/tmp/codex-wake-p21-build/bin/python -m pip install --upgrade pip build
/tmp/codex-wake-p21-build/bin/python -m build
python -m venv /tmp/codex-wake-p21-install
/tmp/codex-wake-p21-install/bin/python -m pip install --upgrade pip
/tmp/codex-wake-p21-install/bin/python -m pip install dist/*.whl
ROOT=/tmp/codex-wake-p21-installed
/tmp/codex-wake-p21-install/bin/codex-wake --wake-root "$ROOT/wake" hook install --repo-root "$ROOT/repo"
/tmp/codex-wake-p21-install/bin/codex-wake --wake-root "$ROOT/wake" hook check --repo-root "$ROOT/repo"
printf '{"wake_id":"wake_seen","submitted_at":"2026-05-19T21:30:00Z","session_id":"session_seen"}\n' > "$ROOT/wake/acks/wake_seen.submitted"
/tmp/codex-wake-p21-install/bin/codex-wake --wake-root "$ROOT/wake" hook check --repo-root "$ROOT/repo"
/tmp/codex-wake-p21-install/bin/codex-wake --wake-root "$ROOT/wake" doctor --repo-root "$ROOT/repo"
```

Outcome:

```text
hook_ack_count=1
hook_active_session_loaded=observed_ack
hook_latest_ack_path=/tmp/codex-wake-p21-installed/wake/acks/wake_seen.submitted
hook_latest_ack_submitted_at=2026-05-19T21:30:00Z
hook_latest_ack_wake_id=wake_seen
hook_latest_ack_session_id=session_seen
```

## Known Limits

- Ack evidence proves the hook ran after a wake prompt was submitted. It cannot prove a future prompt will run the hook.
- No ack means active-session hook state is unknown, not that tmux injection failed.
- The command does not scrape or introspect the active TUI `/hooks` screen.

## Result

Pass. P21 is closed.
