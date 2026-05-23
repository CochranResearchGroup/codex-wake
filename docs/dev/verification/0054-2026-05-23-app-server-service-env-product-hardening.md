# App-Server Service Environment Product Hardening

Date: 2026-05-23

Plan: [App-Server Service Environment Product Hardening](../plans/0038-2026-05-23-app-server-service-env-product-hardening.md)

Handoff source: [Ragmail App-Server Service Environment Handoff](0052-2026-05-23-ragmail-app-server-service-env-handoff.md)

## Summary

Implemented product hardening for service-fired app-server wakes:

- app-server dispatch resolves the Codex CLI from optional `target.codex_cmd`,
  `CODEX_WAKE_CODEX_CMD`, or daemon `PATH`;
- missing app-server command launch now becomes an explicit wake `last_error`;
- `service install` can persist `CODEX_WAKE_CODEX_CMD` in the user unit;
- app-server wake creation/status/candidate validation accept `--codex-path`;
- `doctor` and `doctor --json` report service-side app-server Codex readiness;
- the tracked and installed `codex-wake` skill copies now point agents at the
  new `doctor` and `--codex-path` paths.

## Source Validation

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
python -m compileall -q src tests
git diff --check
```

Result:

```text
Ran 100 tests in 0.826s
OK
```

`compileall` and `git diff --check` passed with no output.

## Source CLI Smokes

Doctor readiness smoke:

```bash
PYTHONPATH=src python -m codex_wake.cli --wake-root .codex/wake doctor --json \
  > /tmp/codex-wake-p38-doctor.json
jq '{codex: .commands.codex, service_app_server: .service_app_server, service: .service}' \
  /tmp/codex-wake-p38-doctor.json
```

Result showed:

```json
{
  "service_app_server": {
    "codex_cmd_ready": true,
    "codex_cmd_source": "user_manager_path",
    "message": "user-systemd manager PATH can resolve codex"
  },
  "service": {
    "active": "inactive",
    "enabled": "disabled",
    "name": "codex-wake-codex-wake.service"
  }
}
```

App-server target command smoke:

```bash
PYTHONPATH=src python -m codex_wake.cli --wake-root "$tmp/wake" \
  app after --codex-path "$(command -v codex)" thread_doc 1m -- \
  "P38 codex cmd target smoke"
```

Resulting target contained:

```json
{
  "codex_cmd": "/home/ecochran76/.nvm/versions/node/v24.14.0/lib/node_modules/@openai/codex/bin/codex.js",
  "endpoint": "stdio://",
  "thread_id": "thread_doc",
  "transport": "app-server"
}
```

Temporary no-start service unit smoke:

```bash
XDG_CONFIG_HOME="$tmp/config" XDG_STATE_HOME="$tmp/state" \
PYTHONPATH=src python -m codex_wake.cli --wake-root "$tmp/wake" \
  service install --no-start --name codex-wake-p38-nosmoke \
  --repo-root "$PWD" --daemon-path "$(command -v codex-waked)" \
  --codex-path "$(command -v codex)" --log-path "$tmp/state/service.log"
```

Rendered unit included:

```text
Environment="CODEX_WAKE_CODEX_CMD=/home/ecochran76/.nvm/versions/node/v24.14.0/lib/node_modules/@openai/codex/bin/codex.js"
ExecStart="/home/ecochran76/.local/share/uv/tools/codex-wake/bin/codex-waked" --wake-root ".../wake" --interval 1
```

## Installed Runtime

Refreshed the installed uv tool:

```bash
uv tool install --force --reinstall --no-cache .
```

Result:

```text
Installed 3 executables: codex-wake, codex-wake-hook, codex-waked
```

Installed help exposes `--codex-path` on:

```bash
codex-wake app after --help
codex-wake app status --help
codex-wake service install --help
```

Installed `doctor --json` reports:

```json
{
  "service_app_server": {
    "codex_cmd_ready": true,
    "codex_cmd_source": "user_manager_path",
    "message": "user-systemd manager PATH can resolve codex"
  },
  "service": {
    "active": "inactive",
    "enabled": "disabled",
    "name": "codex-wake-codex-wake.service"
  }
}
```

## Installed Service App-Server Dogfood

Used a temporary user service and temporary wake root:

```text
service=codex-wake-p38-service-app.service
wake=wake_20260523_183616_fb5a
thread=019e3c37-6dbf-70a0-bbaf-0668ed98ecc3
```

The temporary service installed and started with:

```text
app_server_codex_cmd=/home/ecochran76/.nvm/versions/node/v24.14.0/lib/node_modules/@openai/codex/bin/codex.js
```

The wake reached `submitted`:

```json
{
  "status": "submitted",
  "app_server_preflight": {
    "status": {
      "type": "idle"
    },
    "thread_id": "019e3c37-6dbf-70a0-bbaf-0668ed98ecc3"
  },
  "dispatch_result": {
    "thread_id": "019e3c37-6dbf-70a0-bbaf-0668ed98ecc3",
    "turn_id": "019e561f-c418-7213-8846-3fd1839cc5ad"
  },
  "events": [
    "created",
    "predicate_matched",
    "dispatch_attempt",
    "app_server_preflight",
    "ack_observed"
  ]
}
```

Service log tail:

```text
checked=1 fired=0 failed=0 pending=1 dispatched=0 submitted=0 requeued=0
checked=1 fired=1 failed=0 pending=0 dispatched=1 submitted=1 requeued=0
```

Cleanup verification:

```text
uninstalled codex-wake-p38-service-app.service
inactive
not-found
unit_removed
```

The repo wake root remained clean:

```json
{
  "active_total": 0,
  "terminal_total": 0,
  "archived_total": 13
}
```

The repo service state remained:

```text
inactive
disabled
```

## Installed Skill Sync

Synced tracked skill files to both installed user skill roots:

```bash
diff -qr skills/codex-wake /home/ecochran76/.codex/shared/skills/codex-wake
diff -qr skills/codex-wake /home/ecochran76/.agents/skills/codex-wake
```

Both diffs passed with no output.

## Result

Pass. The product now has a durable service-side Codex CLI command path for
app-server dispatch, doctor visibility for service readiness, explicit
missing-command errors, and an installed-service app-server smoke that fired
through user-systemd rather than the interactive shell.
