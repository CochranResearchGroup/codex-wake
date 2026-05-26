# OpenClaw Codex Wake Plugin

This package registers `codex_wake_schedule`, an OpenClaw agent tool that
writes durable `codex-wake` `openclaw_gateway` wake records for the current
live OpenClaw session.

The plugin captures trusted runtime context from OpenClaw:

- `agentId`
- `sessionKey`
- workspace directory
- channel/account/thread delivery metadata when available

It rejects missing or placeholder session keys. The model supplies only the
trigger and the idempotent wake prompt.

The plugin does not run shell commands. It writes schema-versioned wake JSON
directly so OpenClaw can install it without unsafe-code overrides.

By default, the plugin requires recent persistent `codex-wake` monitor health
for the selected wake root before it writes a record. This prevents OpenClaw
agents from claiming an unattended wake is scheduled when no daemon or
supervisor is polling that root.

Channel/account/thread metadata is evidence by default. The plugin does not
infer Gateway reply overrides from Slack delivery context; `replyChannel`,
`replyTo`, and `replyAccountId` are written only when explicitly configured.

## Install From Codex Wake

```bash
codex-wake openclaw-plugin install --tag <codex-wake-tag> --prune-linked-path
openclaw gateway restart
openclaw plugins inspect codex-wake --runtime --json
```

The `codex-wake` helper materializes the plugin from the selected public repo
tag into user state and then runs OpenClaw's normal plugin installer against
that copy. This is the productized path because it does not depend on the
current repo checkout after install.

Use `--prune-linked-path` when migrating from a previous linked development
install. It removes only linked `plugins.load.paths` entries whose manifest id
is `codex-wake`, writes an OpenClaw config backup, and refreshes OpenClaw's
generated plugin registry.

Update to a newer tag:

```bash
codex-wake openclaw-plugin update --tag <codex-wake-tag> --prune-linked-path
openclaw gateway restart
openclaw plugins inspect codex-wake --runtime --json
```

Build and install a local package artifact for release-candidate validation:

```bash
codex-wake openclaw-plugin pack --output-dir dist/openclaw-plugin
openclaw plugins install --force npm-pack:dist/openclaw-plugin/<tarball>.tgz
openclaw gateway restart
```

Use a linked local path only while developing the plugin:

```bash
openclaw plugins install --link ./plugins/openclaw-codex-wake
```

Rollback:

```bash
openclaw plugins uninstall codex-wake
codex-wake openclaw-plugin install --tag <previous-codex-wake-tag>
openclaw gateway restart
```

Verify the live tool catalog:

```bash
openclaw gateway call tools.catalog --json \
  --params '{"agentId":"main","includePlugins":true}' | rg 'codex_wake_schedule|codex-wake'
```

Also verify installed product readiness from the workspace wake root:

```bash
codex-wake --wake-root .codex/wake monitor check --json
codex-wake --wake-root .codex/wake product-readiness --json
```

Do not treat a linked local plugin path, placeholder session key, or
`--no-dispatch` smoke as durable OpenClaw delivery evidence.

## Tool Example

```json
{
  "trigger": "after",
  "delay": "20m",
  "requireMonitor": true,
  "prompt": "Wake idempotently. First inspect the wake record and any referenced logs, then continue only if the work is incomplete."
}
```

The returned JSON includes the wake id plus validation commands:

- `codex-wake --wake-root <root> show <wake-id>`
- `codex-wake --wake-root <root> status --json`
- `codex-waked --wake-root <root> --once --ack-timeout 20`

The wake root defaults to `.codex/wake` under the active OpenClaw workspace.
Use plugin config or the tool's `wakeRoot` parameter when a shared daemon
monitors a different root.

If the root is not monitored, either enroll it with the supervisor or explicitly
set `requireMonitor=false` for a manual `codex-waked --once` flow:

```bash
codex-wake supervisor install
codex-wake supervisor enroll --wake-root "$PWD/.codex/wake" --repo-root "$PWD"
codex-wake supervisor status --all
```

If OpenClaw Gateway auth depends on environment variables, import them into the
user systemd manager before relying on supervisor delivery:

```bash
systemctl --user import-environment OPENCLAW_GATEWAY_TOKEN OPENCLAW_GATEWAY_PASSWORD
systemctl --user restart codex-wake-supervisor.service
```

## Validation

```bash
npm test
node --check index.js
node --check lib/scheduler.js
```

For a live smoke, ask the target OpenClaw agent to call
`codex_wake_schedule`, then run:

```bash
codex-waked --wake-root <root> --once --ack-timeout 30
codex-wake --wake-root <root> show <wake-id>
openclaw message read --channel slack --account default --target channel:<id> --limit 20 --json
```

For release-level OpenClaw Gateway smoke through the installed CLI, use the
matrix in `docs/product-smoke-matrix.md` and pass real
`--live-openclaw-agent` plus `--live-openclaw-session-key` values to
`scripts/product_smoke.py`. A `--no-dispatch` smoke is not delivery proof.
