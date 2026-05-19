# Clean Fresh Install Smoke

Date: 2026-05-18
Branch: `main`

## Install Boundary

Used an isolated `uv tool` install path and cache under `/tmp`:

```bash
BASE=/tmp/codex-wake-clean-v030
rm -rf "$BASE"
mkdir -p "$BASE/tool" "$BASE/bin" "$BASE/cache" "$BASE/repo" "$BASE/runtime" "$BASE/state"
export UV_TOOL_DIR="$BASE/tool"
export UV_TOOL_BIN_DIR="$BASE/bin"
export UV_CACHE_DIR="$BASE/cache"
uv tool install --force --reinstall 'git+https://github.com/CochranResearchGroup/codex-wake.git@v0.3.0'
```

Observed:

```text
Updated https://github.com/CochranResearchGroup/codex-wake.git (e97451129ba18e90453f55f8c160c296ce0597fe)
Installed 1 package in 3ms
+ codex-wake==0.3.0
Installed 3 executables: codex-wake, codex-wake-hook, codex-waked
```

## Command Smoke

Verified installed commands from the isolated bin directory:

```bash
"$BASE/bin/codex-wake" --help
"$BASE/bin/codex-waked" --once --no-dispatch --wake-root "$BASE/runtime/empty"
printf '{"prompt":"hello","cwd":"%s"}' "$BASE/repo" | "$BASE/bin/codex-wake-hook"
```

Observed:

```text
checked=0 fired=0 failed=0 pending=0 dispatched=0 submitted=0 requeued=0
0 /tmp/codex-wake-clean-hook.out
```

The hook command returned zero bytes for a non-wake prompt, as expected.

## Hook Install And Check

```bash
"$BASE/bin/codex-wake" --wake-root "$BASE/runtime/wake" hook install --repo-root "$BASE/repo"
"$BASE/bin/codex-wake" --wake-root "$BASE/runtime/wake" hook check --repo-root "$BASE/repo"
```

Observed:

```text
installed hook config: /tmp/codex-wake-clean-v030/repo/.codex/hooks.json
command=codex-wake-hook
note=Codex may still require /hooks review before this hook can run.
path=/tmp/codex-wake-clean-v030/repo/.codex/hooks.json
exists=true
valid_json=true
installed=true
command=codex-wake-hook
message=installed
trust=Codex may require /hooks review before this hook can run.
```

Installed hook config:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "command": "codex-wake-hook",
            "statusMessage": "Checking wake trigger",
            "timeout": 5,
            "type": "command"
          }
        ]
      }
    ]
  }
}
```

## Doctor

The first doctor run found the existing user PATH commands because the isolated binaries were invoked by absolute path. Re-ran with the isolated bin directory at the front of `PATH`:

```bash
export PATH="$BASE/bin:$PATH"
"$BASE/bin/codex-wake" --wake-root "$BASE/runtime/wake" doctor \
  --repo-root "$BASE/repo" \
  --name codex-wake-clean-v030 \
  --log-path "$BASE/state/service.log" \
  --interval 1
```

Observed:

```text
repo_root=/tmp/codex-wake-clean-v030/repo
wake_root=/tmp/codex-wake-clean-v030/runtime/wake
codex_wake=/tmp/codex-wake-clean-v030/bin/codex-wake
codex_waked=/tmp/codex-wake-clean-v030/bin/codex-waked
codex_wake_hook=/tmp/codex-wake-clean-v030/bin/codex-wake-hook
tmux=/usr/bin/tmux
hook_config=/tmp/codex-wake-clean-v030/repo/.codex/hooks.json
hook_config_exists=true
hook_config_valid_json=true
hook_config_installed=true
hook_command=codex-wake-hook
service_name=codex-wake-clean-v030.service
service_active=inactive
service_enabled=not-found
service_unit=/home/ecochran76/.config/systemd/user/codex-wake-clean-v030.service
service_log=/tmp/codex-wake-clean-v030/state/service.log
trust=Codex may require /hooks review before this hook can run.
```

## Temporary Service Lifecycle

Verified service commands from the clean install:

```bash
"$BASE/bin/codex-wake" --wake-root "$BASE/runtime/service-wake" service install \
  --name codex-wake-clean-v030 \
  --repo-root "$BASE/repo" \
  --log-path "$BASE/state/service.log" \
  --interval 1
"$BASE/bin/codex-wake" --wake-root "$BASE/runtime/service-wake" service status \
  --name codex-wake-clean-v030 \
  --repo-root "$BASE/repo" \
  --log-path "$BASE/state/service.log" \
  --interval 1
"$BASE/bin/codex-wake" --wake-root "$BASE/runtime/service-wake" service logs \
  --name codex-wake-clean-v030 \
  --repo-root "$BASE/repo" \
  --log-path "$BASE/state/service.log" \
  --lines 5
"$BASE/bin/codex-wake" --wake-root "$BASE/runtime/service-wake" service uninstall \
  --name codex-wake-clean-v030 \
  --repo-root "$BASE/repo" \
  --log-path "$BASE/state/service.log" \
  --interval 1
```

Observed:

```text
installed and started codex-wake-clean-v030.service
unit=/home/ecochran76/.config/systemd/user/codex-wake-clean-v030.service
log=/tmp/codex-wake-clean-v030/state/service.log
name=codex-wake-clean-v030.service
active=active
enabled=enabled
unit=/home/ecochran76/.config/systemd/user/codex-wake-clean-v030.service
log=/tmp/codex-wake-clean-v030/state/service.log
log=/tmp/codex-wake-clean-v030/state/service.log
uninstalled codex-wake-clean-v030.service
removed=/home/ecochran76/.config/systemd/user/codex-wake-clean-v030.service
inactive
```

The temporary unit file was removed after uninstall.
