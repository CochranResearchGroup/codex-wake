# Wake Monitor Readiness And User Supervisor Verification

Date: 2026-05-26

Plan: `docs/dev/plans/0042-2026-05-25-wake-monitor-readiness-user-supervisor.md`

## Scope

Validation record for P42 monitor-readiness gates, user-scoped supervisor
registry/service behavior, OpenClaw plugin enforcement, installed executable
checks, and live wake dogfood.

## Source Validation

Passed:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
# Ran 128 tests in 1.088s - OK

python -m compileall -q src tests .codex/hooks

npm --prefix plugins/openclaw-codex-wake test
# tests 12, pass 12

node --check plugins/openclaw-codex-wake/index.js
node --check plugins/openclaw-codex-wake/lib/scheduler.js

git diff --check
```

The OpenClaw plugin no-shell scan also passed:

```bash
rg -n "node:child_process|from ['\"]child_process['\"]|require\(['\"]child_process['\"]\)|\bspawn\s*\(|\bexecFile\s*\(" plugins/openclaw-codex-wake
# no unsafe child_process imports or spawn/execFile calls found
```

Build artifacts were regenerated with `uv build`:

```text
dist/codex_wake-0.4.15.tar.gz
dist/codex_wake-0.4.15-py3-none-any.whl
```

A throwaway virtualenv installed the built wheel and verified:

- installed package version `0.4.15`;
- `codex-wake --help` exposes `monitor` and `supervisor`;
- `codex-wake --wake-root <tmp>/wake monitor check --json` runs from the
  wheel;
- `codex-wake supervisor run --once --registry-dir <tmp>/roots.d --state-dir
  <tmp>/state --json` returns `[]` for an empty registry.

After commit `91921263a38efe5e79ebf462e905c96ee2aa33ae` was pushed, GitHub
Actions CI run `26431676604` passed release gates on Python 3.11 and 3.12:

- compile sources;
- run unit tests;
- build package;
- smoke installed wheel.

## Installed Runtime Validation

The user-scoped executable install was refreshed from this checkout:

```bash
uv tool install --force --reinstall .
# codex-wake==0.4.15
```

After the public tag was pushed, the user-scoped executable install was
refreshed again from GitHub:

```bash
uv tool install --force --reinstall git+https://github.com/CochranResearchGroup/codex-wake.git@v0.4.15
# resolved v0.4.15 to 91921263a38efe5e79ebf462e905c96ee2aa33ae
# installed codex-wake==0.4.15
```

The user supervisor is installed and running:

```json
{
  "service": {
    "active": "active",
    "enabled": "enabled",
    "name": "codex-wake-supervisor.service",
    "unit": "/home/ecochran76/.config/systemd/user/codex-wake-supervisor.service",
    "log": "/home/ecochran76/.local/state/codex-wake/codex-wake-supervisor.log"
  },
  "root_count": 1,
  "roots": [
    {
      "root_id": "codex-wake-98975473",
      "wake_root": "/home/ecochran76/workspace.local/codex-wake/.codex/wake",
      "enabled": true,
      "health_source": "supervisor",
      "health_mode": "loop",
      "health_recent": true
    }
  ]
}
```

`monitor check --json` reports the repo-scoped service disabled while the root
is still ready through supervisor health:

```json
{
  "monitor_ready": true,
  "monitor_source": "supervisor",
  "service": {
    "active": "inactive",
    "enabled": "disabled",
    "matches_wake_root": true
  },
  "health": {
    "source": "supervisor",
    "mode": "loop",
    "recent": true,
    "persistent": true,
    "path": "/home/ecochran76/.local/state/codex-wake/monitors/98975473f9fc.json"
  }
}
```

`doctor --json` includes the same monitor block and transport readiness. The
app-server transport reports `codex_cmd_ready=true` from the repo service unit
environment, and OpenClaw/tmux interactive commands are visible.

OpenClaw plugin and skill runtime checks:

- `openclaw skills info codex-wake --agent main --json` reports
  `eligible=true`, `modelVisible=true`, `userInvocable=true`, and
  `commandVisible=true`.
- `openclaw plugins inspect codex-wake --runtime --json` reports plugin
  version `0.1.1`, status `loaded`, activated `true`, tool
  `codex_wake_schedule`, and config schema keys
  `requireMonitorByDefault` and `monitorStaleAfterSeconds`.
- `openclaw gateway status --require-rpc --json --timeout 180000` reports
  Gateway runtime `active/running`, RPC `ok=true`, and capability
  `admin_capable`.
- The only Gateway status warning observed is the pre-existing recommended
  audit warning `gateway-path-nonminimal`.

The user systemd manager has the OpenClaw Gateway auth variable names imported
for supervisor-fired OpenClaw dispatch. Values were not recorded:

```text
OPENCLAW_GATEWAY_PASSWORD=<set>
OPENCLAW_GATEWAY_TOKEN=<set>
```

The updated `codex-wake` skill was synced and diff-checked across:

- `skills/codex-wake/`
- `/home/ecochran76/.agents/skills/codex-wake/`
- `/home/ecochran76/.codex/shared/skills/codex-wake/`
- `/home/ecochran76/.openclaw/skills/codex-wake/`

Release/public install validation:

- `v0.4.15` tag points at
  `91921263a38efe5e79ebf462e905c96ee2aa33ae`.
- GitHub release:
  `https://github.com/CochranResearchGroup/codex-wake/releases/tag/v0.4.15`
- Public tag install smoke in a temporary virtualenv reported package version
  `0.4.15`, exposed `monitor` and `supervisor`, ran
  `monitor check --json`, and returned `[]` from `supervisor run --once` with
  an empty registry.
- After refreshing the user-scoped install from the public tag and restarting
  `codex-wake-supervisor.service`, `monitor check --json` still reported
  `monitor_ready=true`, `monitor_source=supervisor`, and the repo wake root had
  `active_total=0`, `terminal_total=0`, `archived_total=21`.

## Live Wake Validation

Codex app-server supervisor-fired wake:

- Wake id: `wake_20260526_034420_a0c4`
- Target transport: `app-server`
- Target thread: `019e3c37-6dbf-70a0-bbaf-0668ed98ecc3`
- Unique marker: `P42_SUPERVISOR_APP_20260525_2244`
- Record evidence:
  - `app_server_preflight.status.type=idle`
  - `dispatch_result.turn_id=019e6262-6108-7430-b44a-7776a2e9ad9c`
  - event sequence includes `predicate_matched`, `dispatch_attempt`,
    `app_server_preflight`, `ack_observed`, and `archived`

OpenClaw plugin-created supervisor-fired wake:

- Wake id: `wake_20260526_034938_2c63`
- Target transport: `openclaw_gateway`
- Unique marker: `P42_SUPERVISOR_OPENCLAW_20260525_2249`
- Record evidence:
  - `attempts=3`
  - failed attempts at `2026-05-26T03:49:58Z` and
    `2026-05-26T03:50:58Z`
  - requeued until `next_attempt_at=2026-05-26T03:55:58Z`
  - successful attempt at `2026-05-26T03:55:58Z`
  - `openclaw_gateway_preflight.rpc_ok=true`
  - `openclaw_gateway_preflight.rpc_capability=admin_capable`
  - `dispatch_result.status=ok`
  - `dispatch_result.summary=completed`
  - `dispatch_result.run_id=codex-wake:wake_20260526_034938_2c63`
  - `dispatch_result.session_id=b0abcc43-cba3-40f0-8691-082ec7e49c97`
  - event sequence includes `openclaw_gateway_dispatch_result`

Slack readback confirmed the OpenClaw wake marker:

```json
{
  "text": "P42_SUPERVISOR_OPENCLAW_20260525_2249",
  "ts": "1779767796.969089",
  "timestampUtc": "2026-05-26T03:56:36.969Z"
}
```

The first plugin-created OpenClaw dogfood wake,
`wake_20260526_034707_8dab`, failed before the user-systemd Gateway auth
environment was imported. That failure exposed two hardening requirements that
were addressed in this lane:

- document/import `OPENCLAW_GATEWAY_TOKEN` and `OPENCLAW_GATEWAY_PASSWORD` into
  the user systemd manager when OpenClaw config references them;
- make the daemon honor future `next_attempt_at` values before retrying
  pending records.

After cleanup:

```json
{
  "active_total": 0,
  "terminal_total": 0,
  "archived_total": 21
}
```

## Closeout

P42 acceptance is satisfied:

- skill, CLI, and plugin all expose monitor readiness;
- CLI-created wakes can require monitor readiness with `--require-monitor`;
- plugin-created OpenClaw wakes require recent persistent monitor health by
  default;
- the user-scoped supervisor monitors explicitly enrolled roots and writes
  persistent health;
- repo-scoped services remain supported and inspectable;
- installed wheel, local `uv tool`, user supervisor, OpenClaw plugin, Codex
  app-server wake, and OpenClaw Gateway wake behavior were verified.

Residual notes:

- OpenClaw Gateway status still reports the existing recommended
  `gateway-path-nonminimal` audit warning.
- No active or terminal wake records remain in the repo wake root after
  dogfood cleanup.
