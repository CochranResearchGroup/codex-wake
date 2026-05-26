# OpenClaw Plugin Productized Install

Date: 2026-05-26

Plan: `docs/dev/plans/0043-2026-05-26-productization-completion.md`

## Scope

Verify P43 Slice 1: a non-linked OpenClaw plugin install/update path that can
survive Gateway restart without depending on the current repo checkout.

## Source Validation

```bash
PYTHONPATH=src python -m unittest tests.test_openclaw_plugin tests.test_cli
```

Outcome: passed, 52 tests.

Full source validation:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
python -m compileall -q src tests .codex/hooks
npm --prefix plugins/openclaw-codex-wake test
node --check plugins/openclaw-codex-wake/index.js
node --check plugins/openclaw-codex-wake/lib/scheduler.js
git diff --check
```

Outcome: passed, 143 Python tests and 12 plugin tests.

Plugin shell scan:

```bash
rg -n "node:child_process|from ['\"]child_process['\"]|require\\(['\"]child_process['\"]\\)|\\bspawn\\s*\\(|\\bexecFile\\s*\\(" plugins/openclaw-codex-wake
```

Outcome: no unsafe `child_process`, `spawn`, or `execFile` matches.

Package build and installed-wheel smoke:

```bash
uv build
python -m venv "$tmp/venv"
"$tmp/venv/bin/pip" install dist/codex_wake-0.4.15-py3-none-any.whl
"$tmp/venv/bin/codex-wake" openclaw-plugin --help
"$tmp/venv/bin/codex-wake" openclaw-plugin pack --source-dir plugins/openclaw-codex-wake --output-dir "$tmp/plugin-dist" --json
```

Outcome: package build succeeded and installed wheel exposed the
`openclaw-plugin` command.

```bash
PYTHONPATH=src python -m codex_wake.cli openclaw-plugin pack --output-dir dist/openclaw-plugin --json
```

Outcome: created
`dist/openclaw-plugin/cochranresearchgroup-openclaw-codex-wake-0.1.1.tgz`.

## Live Install Smoke

Command:

```bash
PYTHONPATH=src python -m codex_wake.cli openclaw-plugin install \
  --tag v0.4.15 \
  --force \
  --refresh \
  --prune-linked-path \
  --json
```

Outcome:

- Materialized public tag source:
  `/home/ecochran76/.local/share/codex-wake/openclaw-plugins/v0.4.15`
- Installed OpenClaw extension:
  `/home/ecochran76/.openclaw/extensions/codex-wake`
- Removed stale linked development path:
  `/home/ecochran76/workspace.local/codex-wake/plugins/openclaw-codex-wake`
- Wrote config backup:
  `/home/ecochran76/.openclaw/openclaw.json.codex-wake-backup-20260526T121635Z`

The initial install completed while the stale linked path was still selected,
so OpenClaw emitted duplicate-plugin warnings. After the config prune,
`openclaw plugins registry --refresh --json` rebuilt the generated plugin
registry from current config and install records.

## Runtime Inspection

Command:

```bash
openclaw plugins inspect codex-wake --runtime --json
```

Final inspected state:

- plugin id: `codex-wake`
- plugin version: `0.1.1`
- source: `/home/ecochran76/.openclaw/extensions/codex-wake/index.js`
- root: `/home/ecochran76/.openclaw/extensions/codex-wake`
- origin: `global`
- status: `loaded`
- activated: `true`
- tool names: `codex_wake_schedule`
- config schema: present
- diagnostics: none
- install source path:
  `/home/ecochran76/.local/share/codex-wake/openclaw-plugins/v0.4.15`

Tool catalog check:

```bash
openclaw gateway call tools.catalog --json \
  --params '{"agentId":"main","includePlugins":true}'
```

Outcome: returned both `plugin:codex-wake` and `codex_wake_schedule` from
source `plugin`.

Repo-linked path check:

```bash
rg -uuu -n --fixed-strings \
  '/home/ecochran76/workspace.local/codex-wake/plugins/openclaw-codex-wake' \
  /home/ecochran76/.openclaw/plugins/installs.json \
  /home/ecochran76/.openclaw/openclaw.json
```

Outcome: no matches.

## Gateway Restart Evidence

Command:

```bash
systemctl --user restart openclaw-gateway.service
systemctl --user is-active openclaw-gateway.service
openclaw gateway status --require-rpc --json --timeout 180000
```

Outcome:

- service state: `active`
- Gateway RPC readiness: `ok: true`
- URL: `ws://127.0.0.1:18789`

Post-restart logs since `2026-05-26 07:18:44 CDT` showed
`http server listening` and `ready`, with no `codex-wake` duplicate-plugin
warnings.

## Known Gap

This verifies P43 Slice 1 on the workstation. The broader P43 DOD remains open:
unified readiness doctor, state lifecycle docs, cross-runtime smoke harness,
operator-doc closeout, and the productization release are not complete.
