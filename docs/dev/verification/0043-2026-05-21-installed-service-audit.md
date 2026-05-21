# Installed Service Audit

Date: 2026-05-21

## Scope

Audit the repo-scoped installed `codex-waked` user service after the `v0.4.12` release sequence.

## Initial State

Git:

```text
## main...origin/main
```

Repo wake root:

```text
active_total=0
terminal_total=0
archived_total=8
counts_by_target_transport=app-server:2,tmux:6
```

Systemd unit:

```text
Id=codex-wake-codex-wake.service
LoadState=loaded
ActiveState=inactive
SubState=dead
UnitFileState=disabled
ExecStart=/home/ecochran76/.local/share/uv/tools/codex-wake/bin/codex-waked --wake-root /home/ecochran76/workspace.local/codex-wake/.codex/wake --interval 1
```

Installed runtime before refresh:

```text
codex-wake package metadata: 0.4.11
```

The installed CLI already exposed `app candidates --validate`, but package metadata lagged the public release.

## Runtime Refresh

Refreshed the installed uv tool from the public release tag:

```text
uv tool install --force 'git+https://github.com/CochranResearchGroup/codex-wake.git@v0.4.12'
```

Result:

```text
Installed 3 executables: codex-wake, codex-wake-hook, codex-waked
codex-wake==0.4.12
```

Verified installed package metadata:

```text
0.4.12
```

Verified installed `app candidates --help` exposes:

```text
--validate
--only-idle
```

## Service Smoke

Reloaded user systemd and started the repo-scoped service without enabling it:

```text
systemctl --user daemon-reload
systemctl --user start codex-wake-codex-wake.service
```

Start status:

```text
Id=codex-wake-codex-wake.service
LoadState=loaded
ActiveState=active
SubState=running
UnitFileState=disabled
Result=success
NRestarts=0
ExecMainStatus=0
```

Stopped the service to restore the pre-audit state:

```text
systemctl --user stop codex-wake-codex-wake.service
```

Final status:

```text
Id=codex-wake-codex-wake.service
LoadState=loaded
ActiveState=inactive
SubState=dead
UnitFileState=disabled
Result=success
NRestarts=0
ExecMainStatus=0
```

Journal evidence:

```text
Started codex-wake-codex-wake.service - Codex Wake daemon for one repository.
Stopping codex-wake-codex-wake.service - Codex Wake daemon for one repository...
Stopped codex-wake-codex-wake.service - Codex Wake daemon for one repository.
```

Final wake-root status:

```text
active_total=0
terminal_total=0
archived_total=8
```

## Result

Pass. The repo-scoped user service unit is installed, starts cleanly from the refreshed `0.4.12` uv tool runtime, and was returned to its original inactive/disabled state. No active wake records were introduced by the audit.
