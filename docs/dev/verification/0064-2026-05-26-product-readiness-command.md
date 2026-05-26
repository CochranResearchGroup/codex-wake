# Product Readiness Command

Date: 2026-05-26

Plan: `docs/dev/plans/0043-2026-05-26-productization-completion.md`

## Scope

Verify P43 Slice 2: a single installed-readiness surface that reports CLI,
hook, skill, service, supervisor, monitor, app-server, OpenClaw Gateway,
OpenClaw plugin, and tmux readiness without exposing secret values.

## Implemented Surface

Command:

```bash
codex-wake --wake-root .codex/wake product-readiness --json
```

The report uses this status vocabulary:

- `ready`
- `warning`
- `manual_only`
- `blocked`

The JSON report includes:

- CLI version and command paths
- hook source status plus runtime ack evidence
- standard user-scope skill install paths
- repo-scoped service status
- user supervisor status and enrolled roots
- monitor health for the selected wake root
- app-server dispatch command readiness
- OpenClaw Gateway auth/RPC readiness
- OpenClaw plugin readiness and `codex_wake_schedule` visibility
- tmux command/current-pane availability

Gateway auth is reduced to variable names, source type, and presence booleans.
Raw token/password values are not emitted.

## Source Validation

Focused validation:

```bash
PYTHONPATH=src python -m unittest tests.test_product_readiness tests.test_cli
```

Outcome: passed, 52 tests.

Targeted cases covered:

- missing supervisor service
- stale monitor health
- missing OpenClaw plugin
- missing OpenClaw Gateway auth environment
- app-server command drift where only the interactive shell can resolve Codex
- no Gateway secret value leakage in the report
- CLI JSON and text output for `product-readiness`

Compile validation:

```bash
python -m compileall -q src tests .codex/hooks
```

Outcome: passed.

Full validation after documentation updates:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
npm --prefix plugins/openclaw-codex-wake test
node --check plugins/openclaw-codex-wake/index.js
node --check plugins/openclaw-codex-wake/lib/scheduler.js
git diff --check
uv build
```

Outcome: passed, 153 Python tests and 12 plugin tests. Package build created
`dist/codex_wake-0.4.15.tar.gz` and
`dist/codex_wake-0.4.15-py3-none-any.whl`.

Installed-wheel smoke:

```bash
python -m venv "$tmp/venv"
"$tmp/venv/bin/pip" install dist/codex_wake-0.4.15-py3-none-any.whl
"$tmp/venv/bin/codex-wake" product-readiness --help
```

Outcome: passed.

## Live Workstation Smoke

Command:

```bash
PYTHONPATH=src python -m codex_wake.cli --wake-root .codex/wake product-readiness --json
```

Summarized outcome:

```json
{
  "overall_status": "warning",
  "cli": "ready",
  "hooks": "warning",
  "skills": "ready",
  "repo_service": "warning",
  "supervisor": "ready",
  "monitor": "ready",
  "app_server": "ready",
  "openclaw_gateway": "ready",
  "openclaw_plugin": "ready",
  "tmux": "ready",
  "missing_gateway_env": []
}
```

Expected warnings:

- `hooks=warning` because both project and user hook sources are installed.
- `repo_service=warning` because this repo is currently monitored by the
  user-scoped supervisor rather than the repo-scoped service.

Readiness evidence:

- CLI version: `0.4.15`
- supervisor: `ready`, root count `1`, current root enrolled `true`
- monitor: `ready`, source `supervisor`, persistent loop health recent
- app-server: `ready`, source `unit_environment`
- OpenClaw plugin: `ready`, source
  `/home/ecochran76/.openclaw/extensions/codex-wake/index.js`,
  tool `codex_wake_schedule`, diagnostic count `0`
- tmux: `ready`, current shell has `TMUX` and `TMUX_PANE`

Secret-leak check:

```bash
python - <<'PY'
import os, pathlib
text = pathlib.Path('/tmp/codex-wake-product-readiness.json').read_text()
leaks = []
for key in ('OPENCLAW_GATEWAY_TOKEN', 'OPENCLAW_GATEWAY_PASSWORD'):
    value = os.environ.get(key)
    if value and value in text:
        leaks.append(key)
if leaks:
    raise SystemExit('secret values leaked for: ' + ','.join(leaks))
print('no configured gateway secret values found in product-readiness output')
PY
```

Outcome: no configured Gateway secret values were found in the report.

## Skill Sync

Synced the updated `codex-wake` skill to:

- `/home/ecochran76/.agents/skills/codex-wake`
- `/home/ecochran76/.codex/shared/skills/codex-wake`
- `/home/ecochran76/.openclaw/skills/codex-wake`

`diff -qr` reported no differences after sync.

## Known Gap

This verifies P43 Slice 2. The broader P43 DOD remains open: state lifecycle
docs/validation, cross-runtime smoke harness, operator-doc consolidation, and
the productization release are not complete.
