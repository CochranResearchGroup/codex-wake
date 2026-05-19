# Hook Setup And Doctor CLI Verification

Date: 2026-05-18
Branch: `main`

## Implementation

Added hook setup and readiness commands:

```bash
codex-wake hook install
codex-wake hook check
codex-wake doctor
```

`hook install` writes or updates repo-local `.codex/hooks.json` with:

```json
{
  "type": "command",
  "command": "codex-wake-hook",
  "timeout": 5,
  "statusMessage": "Checking wake trigger"
}
```

`hook check` reports config path, JSON validity, whether the expected command is present, and the Codex `/hooks` trust reminder.

`doctor` reports:

- repo root
- wake root
- installed `codex-wake`, `codex-waked`, and `codex-wake-hook` paths
- tmux path
- hook config status
- expected hook command
- user service status, unit path, and log path
- Codex `/hooks` trust reminder

Package version was bumped to `0.3.0`.

## Source Validation

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
python -m compileall -q src tests .codex/hooks
python /home/ecochran76/workspace.local/agent-policies/repo-policy-selector/scripts/audit_planning_contract.py --repo-root /home/ecochran76/workspace.local/codex-wake --json
```

Observed:

```text
Ran 41 tests in 0.157s
OK
planning audit ok: true
```

## Source Doctor Smoke

```bash
PYTHONPATH=src python -m codex_wake.cli doctor
```

Observed:

```text
repo_root=/home/ecochran76/workspace.local/codex-wake
wake_root=/home/ecochran76/workspace.local/codex-wake/.codex/wake
codex_wake=/home/ecochran76/.local/bin/codex-wake
codex_waked=/home/ecochran76/.local/bin/codex-waked
codex_wake_hook=/home/ecochran76/.local/bin/codex-wake-hook
tmux=/usr/bin/tmux
hook_config=/home/ecochran76/workspace.local/codex-wake/.codex/hooks.json
hook_config_exists=true
hook_config_valid_json=true
hook_config_installed=true
hook_command=codex-wake-hook
service_name=codex-wake-codex-wake.service
service_active=inactive
service_enabled=disabled
trust=Codex may require /hooks review before this hook can run.
```

## Installed Command Validation

```bash
uv build
uv tool install --force --reinstall .
codex-wake hook install --repo-root /tmp/codex-wake-hook-smoke
codex-wake hook check --repo-root /tmp/codex-wake-hook-smoke
codex-wake doctor
codex-waked --once --no-dispatch --wake-root /tmp/codex-wake-p14-empty
```

Observed build and install:

```text
Successfully built dist/codex_wake-0.3.0.tar.gz
Successfully built dist/codex_wake-0.3.0-py3-none-any.whl
Installed 3 executables: codex-wake, codex-wake-hook, codex-waked
```

Observed hook install/check:

```text
installed hook config: /tmp/codex-wake-hook-smoke/.codex/hooks.json
command=codex-wake-hook
note=Codex may still require /hooks review before this hook can run.
path=/tmp/codex-wake-hook-smoke/.codex/hooks.json
exists=true
valid_json=true
installed=true
command=codex-wake-hook
message=installed
trust=Codex may require /hooks review before this hook can run.
```

Observed installed doctor:

```text
repo_root=/home/ecochran76/workspace.local/codex-wake
wake_root=/home/ecochran76/workspace.local/codex-wake/.codex/wake
codex_wake=/home/ecochran76/.local/bin/codex-wake
codex_waked=/home/ecochran76/.local/bin/codex-waked
codex_wake_hook=/home/ecochran76/.local/bin/codex-wake-hook
tmux=/usr/bin/tmux
hook_config=/home/ecochran76/workspace.local/codex-wake/.codex/hooks.json
hook_config_exists=true
hook_config_valid_json=true
hook_config_installed=true
hook_command=codex-wake-hook
service_name=codex-wake-codex-wake.service
service_active=inactive
service_enabled=disabled
trust=Codex may require /hooks review before this hook can run.
```

Observed daemon smoke:

```text
checked=0 fired=0 failed=0 pending=0 dispatched=0 submitted=0 requeued=0
```
