# Ragmail App-Server Service Environment Handoff

Date: 2026-05-23

Request: leave a handoff note for Codex Wake about skill hardening after a
Ragmail app-server wake smoke exposed a user-systemd service environment gap.

## Summary

Ragmail's repo-scoped wake daemon was installed and active, and app-server
status checks worked from the interactive shell. A real app-server wake still
failed at first because `codex-waked` was running under a user-systemd manager
environment whose `PATH` did not include the npm-installed `codex` binary.

After importing the current shell environment into user-systemd and restarting
only `codex-wake-ragmail.service`, the same wake record dispatched
successfully through app-server and recorded `ack_observed`.

This is not a Ragmail product bug. It is a Codex Wake runtime ergonomics and
skill-hardening issue:

- the skill should teach agents to check the daemon's environment, not just the
  interactive shell;
- `service install` and app-server dispatch should avoid depending on ambient
  `PATH` where practical;
- `doctor` should make this failure mode obvious before a real wake is queued.

## Live Evidence

Repo wake root:

```text
/home/ecochran76/workspace.local/ragmail/.codex/wake
```

Thread selected from app-server candidate discovery:

```text
019e54ea-d411-7310-99bb-fc75668f66ea
```

Interactive-shell status checks worked:

```text
codex-wake --wake-root .codex/wake app status --json 019e54ea-d411-7310-99bb-fc75668f66ea
```

reported `status_type=notLoaded`, and:

```text
codex-wake --wake-root .codex/wake app status --json --resume 019e54ea-d411-7310-99bb-fc75668f66ea
```

reported `status_type=idle`.

Dogfood wake:

```text
wake_20260523_180552_881f
```

The wake reached `firing` and recorded repeated `dispatch_attempt` events, but
the repo service log showed:

```text
FileNotFoundError: [Errno 2] No such file or directory: 'codex'
```

The installed user service was active:

```text
codex-wake-ragmail.service
```

but the user-systemd manager environment initially had a minimal `PATH` that
could not resolve the npm Codex CLI. The interactive shell could resolve it:

```text
/home/ecochran76/.nvm/versions/node/v24.14.0/bin/codex
codex-cli 0.133.0
```

Runtime workaround used:

```text
systemctl --user import-environment PATH CODEX_CI CODEX_MANAGED_BY_NPM CODEX_MANAGED_PACKAGE_ROOT CODEX_PROFILES_CONFIG CODEX_PROFILES_REPO
systemctl --user restart codex-wake-ragmail.service
```

After the restart, the same wake record recorded:

```text
app_server_preflight.status.type=idle
dispatch_result.turn_id=019e5604-6349-72b0-a336-ddd4b80c9448
event=ack_observed
status=submitted
```

The dogfood wake was archived afterward, and the Ragmail wake root ended with:

```json
{
  "active_total": 0,
  "counts_by_status": {
    "archived": 5,
    "cancelled": 1,
    "expired": 0,
    "failed": 0,
    "firing": 0,
    "pending": 0,
    "submitted": 0
  }
}
```

## Skill Hardening Recommendations

Update `skills/codex-wake/SKILL.md` and
`skills/codex-wake/references/use-cases.md` so app-server wake workflows say:

- app-server dispatch is executed by the daemon process, so `command -v codex`
  in the current shell is insufficient evidence when a user-systemd service
  will do the dispatch;
- before relying on a repo-scoped service for app-server wakes, inspect the
  service environment:

```text
systemctl --user show-environment | rg '^(PATH|CODEX_)='
systemctl --user status codex-wake-<repo>.service --no-pager
codex-wake --wake-root .codex/wake service status
codex-wake --wake-root .codex/wake service logs --lines 80
```

- if the service log contains `No such file or directory: 'codex'`, classify
  the wake as a service-environment failure, not an app-server protocol
  failure;
- for immediate recovery, import the current shell environment and restart the
  affected repo service, then re-check the same wake record before creating a
  duplicate wake;
- for one-off validation, prefer running `codex-waked --wake-root .codex/wake
  --once` from the current shell when specifically testing app-server protocol
  behavior rather than service environment behavior;
- after app-server dogfood, inspect `codex-wake show <wake-id>` for
  `app_server_preflight`, `dispatch_result.turn_id`, and `ack_observed`.

## Product Hardening Recommendations

Open a bounded follow-on plan for app-server service environment hardening.
Candidate acceptance criteria:

- `codex-wake service install` can persist enough environment for the daemon to
  launch `codex app-server` after a user-systemd manager restart.
- App-server wake creation or dispatch can optionally use a configured absolute
  Codex CLI path instead of the hard-coded `["codex", "app-server", "--listen",
  "stdio://"]`.
- `doctor` or `doctor --json` reports whether the active user service can
  resolve the Codex CLI needed for app-server dispatch.
- The failure signature is covered by tests: when the service or dispatcher
  cannot find `codex`, records preserve an explicit operator-facing error and
  do not look like app-server thread-status failures.
- Validation includes an installed-service app-server dogfood where the wake is
  fired by the repo-scoped user service, not by the interactive shell.

## Notes

The workaround above imported private workstation environment into user-systemd
runtime state. It should not be treated as a portable product behavior. The
portable product behavior should either install a durable service environment
or resolve/configure the app-server command explicitly.
