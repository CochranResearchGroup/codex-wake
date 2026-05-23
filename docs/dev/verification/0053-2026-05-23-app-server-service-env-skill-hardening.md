# App-Server Service Environment Skill Hardening Verification

Date: 2026-05-23

Plan: [App-Server Service Environment Skill Hardening](../plans/0037-2026-05-23-app-server-service-env-skill-hardening.md)

Handoff source: [Ragmail App-Server Service Environment Handoff](0052-2026-05-23-ragmail-app-server-service-env-handoff.md)

## Change

Updated the `codex-wake` skill source so app-server wake workflows now teach
agents to distinguish:

- interactive-shell app-server protocol checks
- repo-scoped user-systemd service-fired app-server dispatch
- service environment failures such as `No such file or directory: 'codex'`

The skill now instructs agents to inspect:

```text
systemctl --user show-environment | rg '^(PATH|CODEX_)='
systemctl --user status codex-wake-<repo>.service --no-pager
codex-wake --wake-root .codex/wake service status
codex-wake --wake-root .codex/wake service logs --lines 80
```

It also documents the immediate workstation recovery pattern:

```text
systemctl --user import-environment PATH CODEX_CI CODEX_MANAGED_BY_NPM CODEX_MANAGED_PACKAGE_ROOT CODEX_PROFILES_CONFIG CODEX_PROFILES_REPO
systemctl --user restart codex-wake-<repo>.service
```

The recovery path is explicitly described as workstation runtime repair, not a
portable product fix.

## Installed Skill Sync

Synced the updated skill to:

```text
/home/ecochran76/.codex/shared/skills/codex-wake
/home/ecochran76/.agents/skills/codex-wake
```

Verified installed copies match source:

```text
diff -qr skills/codex-wake /home/ecochran76/.codex/shared/skills/codex-wake
diff -qr skills/codex-wake /home/ecochran76/.agents/skills/codex-wake
```

## Validation

Lightweight skill assertion:

```text
skill_service_env_guidance_ok
```

Full source test gate:

```text
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
Ran 93 tests in 0.804s
OK

python -m compileall -q src tests
git diff --check
```

Wake root after validation:

```json
{
  "active_total": 0,
  "terminal_total": 0
}
```

## Deferred Product Work

The skill now guides agents around the service environment failure mode, but the
product hardening from the handoff remains open: service install should persist
or configure the Codex CLI environment more durably, and `doctor` should surface
whether the active service can resolve `codex app-server`.
