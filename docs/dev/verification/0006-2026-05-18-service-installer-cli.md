# Service Installer CLI Verification

Date: 2026-05-18
Branch: `main`

## Implementation

Added `codex_wake.service` with:

- user systemd unit rendering
- repo-specific service naming
- user unit path and log path resolution
- install/start verification
- status, logs, stop, and uninstall helpers

Added CLI commands:

```bash
codex-wake service install
codex-wake service status
codex-wake service logs
codex-wake service stop
codex-wake service uninstall
```

Package version was bumped to `0.2.0`.

## Source Validation

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
python -m compileall -q src tests .codex/hooks
python /home/ecochran76/workspace.local/agent-policies/repo-policy-selector/scripts/audit_planning_contract.py --repo-root /home/ecochran76/workspace.local/codex-wake --json
```

Observed:

```text
Ran 36 tests in 0.147s
OK
planning audit ok: true
```

## Installed Command Validation

Built and installed the package:

```bash
uv build
uv tool install --force --reinstall .
```

Verified installed source contains the corrected systemd unit renderer and active-start check:

```text
WorkingDirectory={config.repo_root}
service did not become active
```

Verified service command help:

```bash
codex-wake service --help
codex-wake service install --help
```

## Service Lifecycle Smoke

Used a temporary service name, wake root, and log file:

```bash
NAME=codex-wake-p13-smoke
ROOT=/tmp/codex-wake-p13-runtime
LOG=/tmp/codex-wake-p13.log
```

Installed and started:

```bash
codex-wake --wake-root "$ROOT" service install --name "$NAME" --repo-root /home/ecochran76/workspace.local/codex-wake --log-path "$LOG" --interval 1
```

Observed:

```text
installed and started codex-wake-p13-smoke.service
unit=/home/ecochran76/.config/systemd/user/codex-wake-p13-smoke.service
log=/tmp/codex-wake-p13.log
```

Status:

```text
name=codex-wake-p13-smoke.service
active=active
enabled=enabled
unit=/home/ecochran76/.config/systemd/user/codex-wake-p13-smoke.service
log=/tmp/codex-wake-p13.log
```

Logs command:

```bash
codex-wake --wake-root "$ROOT" service logs --name "$NAME" --repo-root /home/ecochran76/workspace.local/codex-wake --log-path "$LOG" --lines 5
```

Observed at least the log path:

```text
log=/tmp/codex-wake-p13.log
```

Stopped and uninstalled:

```bash
codex-wake --wake-root "$ROOT" service stop --name "$NAME" --repo-root /home/ecochran76/workspace.local/codex-wake --log-path "$LOG" --interval 1
codex-wake --wake-root "$ROOT" service uninstall --name "$NAME" --repo-root /home/ecochran76/workspace.local/codex-wake --log-path "$LOG" --interval 1
systemctl --user is-active "$NAME.service"
test ! -f "$HOME/.config/systemd/user/$NAME.service"
```

Observed:

```text
stopped codex-wake-p13-smoke.service
uninstalled codex-wake-p13-smoke.service
removed=/home/ecochran76/.config/systemd/user/codex-wake-p13-smoke.service
inactive
```

## Service Log Activity Smoke

Created a wake with an intentionally missing tmux pane so the daemon could log activity without targeting a live pane:

```bash
TMUX_PANE="%999999" TMUX="/tmp/tmux-1000/default,0,0" codex-wake --wake-root "$ROOT" after 1s -- "P13 log smoke with intentionally missing pane."
sleep 3
codex-wake --wake-root "$ROOT" service logs --name "$NAME" --repo-root /home/ecochran76/workspace.local/codex-wake --log-path "$LOG" --lines 20
```

Observed service logs:

```text
checked=1 fired=1 failed=0 pending=0 dispatched=1 submitted=0 requeued=1
checked=1 fired=1 failed=0 pending=0 dispatched=1 submitted=0 requeued=1
checked=1 fired=1 failed=1 pending=0 dispatched=1 submitted=0 requeued=0
```

Observed terminal failed wake:

```text
ID	STATUS	PREDICATE	NEXT
wake_20260519_023447_343b	failed	not_before	2026-05-19T02:39:49Z
```

The temporary service was uninstalled after the smoke.
