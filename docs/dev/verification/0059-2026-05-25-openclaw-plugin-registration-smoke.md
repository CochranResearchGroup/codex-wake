# OpenClaw Plugin Registration Smoke

Date: 2026-05-25

Plan: `docs/dev/plans/0040-2026-05-25-openclaw-gateway-wake-transport.md`

## Scope

Execute P40 Slice 4: add and validate an OpenClaw plugin that lets a live
OpenClaw agent schedule a durable `codex-wake` `openclaw_gateway` wake without
the model manually copying target metadata into the wake record.

## Plugin Surface

Added external plugin package:

- `plugins/openclaw-codex-wake/package.json`
- `plugins/openclaw-codex-wake/openclaw.plugin.json`
- `plugins/openclaw-codex-wake/index.js`
- `plugins/openclaw-codex-wake/lib/scheduler.js`
- `plugins/openclaw-codex-wake/test/scheduler.test.mjs`
- `plugins/openclaw-codex-wake/README.md`

The plugin registers:

- command: `/codex-wake`
- tool: `codex_wake_schedule`

Design points:

- The plugin writes schema-versioned wake JSON directly and does not run shell
  commands.
- It captures trusted OpenClaw runtime context: `agentId`, `sessionKey`,
  workspace directory, and channel/thread evidence when available.
- It rejects missing or placeholder session keys.
- It stores channel/account/thread data as evidence by default. It stores
  `reply_channel`, `reply_to`, and `reply_account_id` only when those dispatch
  overrides are explicitly configured.

## Installation And Catalog Evidence

Install command:

```bash
openclaw plugins install --link ./plugins/openclaw-codex-wake
systemctl --user restart openclaw-gateway.service
```

Runtime inspection:

```bash
openclaw plugins inspect codex-wake --runtime --json
```

Relevant result:

- `status: loaded`
- `source: /home/ecochran76/workspace.local/codex-wake/plugins/openclaw-codex-wake/index.js`
- `enabled: true`
- `activated: true`
- `toolNames: ["codex_wake_schedule"]`
- `commands: ["codex-wake"]`
- `diagnostics: []`

Gateway catalog:

```bash
openclaw gateway call tools.catalog --json \
  --params '{"agentId":"main","includePlugins":true}'
```

Relevant result:

- plugin id `plugin:codex-wake`
- tool id `codex_wake_schedule`
- label `Schedule Wake`
- source `plugin`

## Focused Validation

```bash
npm test
node --check plugins/openclaw-codex-wake/index.js
node --check plugins/openclaw-codex-wake/lib/scheduler.js
rg -n "child_process|spawn\(|exec\(|shell" plugins/openclaw-codex-wake
```

Results:

- 9 plugin tests passed.
- Node syntax checks passed.
- The only `shell`/`exec` matches were documentation text and harmless regex
  `.exec(...)` calls; there is no `child_process`, `spawn`, or shell execution
  in the plugin.

## Routing Fix

First plugin-created smoke wake:

- wake id: `wake_20260525_210815_c4d9`
- expected response: `CODEX_WAKE_PLUGIN_WAKE_20260525_210820`

The daemon requeued after Gateway rejected the explicit inferred reply override:

```text
OpenClaw Gateway agent call failed: Gateway call failed:
GatewayClientRequestError: Error: Unknown channel: slack
```

The failed record showed:

```json
"dispatch": {
  "deliver": true,
  "gateway_timeout_ms": 180000,
  "reply_account_id": "default",
  "reply_channel": "slack",
  "reply_to": "channel:C0AHQQCG7J4",
  "timeout_seconds": 600
}
```

Fix:

- preserve provider/channel/workspace/thread as `target.openclaw.channel`
  evidence;
- do not infer `dispatch.reply_channel`, `dispatch.reply_to`, or
  `dispatch.reply_account_id`;
- include those dispatch override fields only when explicitly configured.

Focused tests now assert both the default no-override behavior and explicit
override behavior.

The failed smoke wake was cancelled and archived:

```bash
PYTHONPATH=src python -m codex_wake.cli --wake-root .codex/wake \
  cancel wake_20260525_210815_c4d9
PYTHONPATH=src python -m codex_wake.cli --wake-root .codex/wake \
  archive wake_20260525_210815_c4d9
```

## Successful Plugin Smoke

Scheduling turn:

```bash
openclaw gateway call agent --expect-final --json --timeout 300000 \
  --params '{"message":"P40 Slice 4 live plugin smoke. Use the codex_wake_schedule tool exactly once with trigger=after, delay=20s, wakeRoot=/home/ecochran76/workspace.local/codex-wake/.codex/wake, and prompt exactly: P40 Slice 4 plugin-scheduled wake fired. First inspect the wake record and verify the predicate. Then reply with exactly CODEX_WAKE_PLUGIN_WAKE_20260525_211530 and stop. After the tool returns, reply only with the wake id.","agentId":"main","sessionKey":"agent:main:slack:channel:c0ahqqcg7j4","deliver":false,"timeout":240,"idempotencyKey":"codex-wake-plugin-schedule-smoke-20260525-211530"}'
```

Relevant result:

- run id: `codex-wake-plugin-schedule-smoke-20260525-211530`
- final text: `wake_20260525_211551_b1f4`
- session id: `b0abcc43-cba3-40f0-8691-082ec7e49c97`
- session key: `agent:main:slack:channel:c0ahqqcg7j4`
- provider/model: `openai-codex` / `gpt-5.5`
- tool summary: one call to `codex_wake_schedule`, zero failures

Created wake:

- wake id: `wake_20260525_211551_b1f4`
- predicate due at: `2026-05-25T21:16:11Z`
- target transport: `openclaw_gateway`
- dispatch fields: `deliver`, `timeout_seconds`, and `gateway_timeout_ms`
  only; no inferred reply override fields

Daemon pass after trigger:

```bash
PYTHONPATH=src python -m codex_wake.daemon --wake-root .codex/wake --once --ack-timeout 30
```

First pass result:

```text
checked=1 fired=1 failed=0 pending=0 dispatched=1 submitted=0 requeued=1
```

The first pass coincided with an OpenClaw Gateway restart and failed during
preflight. The same exact preflight command later exited `0` with RPC
`admin_capable`, so the same wake was retried instead of duplicating it.

Second pass result:

```text
checked=1 fired=1 failed=0 pending=0 dispatched=1 submitted=1 requeued=0
```

Submitted wake evidence:

- `attempts: 2`
- `status: submitted`
- `openclaw_gateway_preflight.rpc_ok: true`
- `openclaw_gateway_preflight.rpc_capability: admin_capable`
- `dispatch_result.transport: openclaw_gateway`
- `dispatch_result.gateway_method: agent`
- `dispatch_result.run_id: codex-wake:wake_20260525_211551_b1f4`
- `dispatch_result.session_id: b0abcc43-cba3-40f0-8691-082ec7e49c97`
- `dispatch_result.session_key: agent:main:slack:channel:c0ahqqcg7j4`
- `dispatch_result.status: ok`
- `dispatch_result.summary: completed`
- `dispatch_result.payload_count: 1`
- `dispatch_result.payload_text_summary.total_length: 38`

## Transcript And Slack Evidence

OpenClaw transcript/log search:

```bash
rg -n "wake_20260525_211551_b1f4|CODEX_WAKE_PLUGIN_WAKE_20260525_211530|P40 Slice 4 plugin-scheduled" \
  /tmp/openclaw \
  /home/ecochran76/.openclaw \
  -S
```

Relevant hits:

- OpenClaw log line 2748: scheduling turn final text
  `wake_20260525_211551_b1f4`
- OpenClaw log line 2791: wake turn final marker
  `CODEX_WAKE_PLUGIN_WAKE_20260525_211530`
- OpenClaw session transcript contains the assistant final message
  `CODEX_WAKE_PLUGIN_WAKE_20260525_211530`
- trajectory line 122 records `session.ended` with `status: success` for
  `runId: codex-wake:wake_20260525_211551_b1f4`

Live Slack readback:

```bash
openclaw message read \
  --channel slack \
  --account default \
  --target channel:C0AHQQCG7J4 \
  --limit 20 \
  --json
```

Relevant result:

- message `ts: 1779743864.850509`
- `timestampUtc: 2026-05-25T21:17:44.851Z`
- bot profile: `OpenClaw`
- text: `CODEX_WAKE_PLUGIN_WAKE_20260525_211530`

Slack Mirror lexical search was also attempted through both
`slack-mirror-user` and the Slack Mirror MCP, but the mirrored index had not
yet ingested the new private-channel message. Live OpenClaw Slack readback is
the Slack-visible proof for this slice.

## Cleanup

The successful smoke wake was archived:

```bash
PYTHONPATH=src python -m codex_wake.cli --wake-root .codex/wake \
  archive wake_20260525_211551_b1f4
```

Final wake-root status:

- `active_total: 0`
- `archived_total: 16`
- `counts_by_status.archived: 16`
- `counts_by_target_transport.openclaw_gateway: 3`

## Skill Availability

The tracked `skills/codex-wake` guidance was synced to user and OpenClaw skill
roots:

- `/home/ecochran76/.agents/skills/codex-wake`
- `/home/ecochran76/.codex/shared/skills/codex-wake`
- `/home/ecochran76/.openclaw/skills/codex-wake`

Verification:

```bash
diff -qr skills/codex-wake /home/ecochran76/.agents/skills/codex-wake
diff -qr skills/codex-wake /home/ecochran76/.codex/shared/skills/codex-wake
diff -qr skills/codex-wake /home/ecochran76/.openclaw/skills/codex-wake
openclaw skills info codex-wake --agent main --json
```

Relevant result:

- source `agents-skills-personal`
- `modelVisible: true`
- `userInvocable: true`
- `commandVisible: true`

## Final Validation

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
python -m compileall -q src tests .codex/hooks
npm test --prefix plugins/openclaw-codex-wake
node --check plugins/openclaw-codex-wake/index.js
node --check plugins/openclaw-codex-wake/lib/scheduler.js
git diff --check
```

Results:

- 112 Python tests passed.
- Python compile check passed.
- 9 OpenClaw plugin tests passed.
- Node syntax checks passed.
- Diff whitespace check passed.

Upstream CI for implementation commit `ebc9235` also passed:

- GitHub Actions run `26420370299`
- `Release gates (3.11)`: success
- `Release gates (3.12)`: success

## Acceptance Result

Slice 4 passes:

- the plugin registered a live OpenClaw tool and command;
- a live `main` OpenClaw agent turn used `codex_wake_schedule`;
- the plugin captured the intended session key and channel evidence;
- the plugin wrote a durable `openclaw_gateway` wake record without shell
  execution or placeholder targets;
- the daemon submitted the wake through OpenClaw Gateway with dispatch enabled;
- the expected unique response appeared in OpenClaw transcript/log evidence and
  live Slack readback;
- dogfood wake state was archived so the repo wake root has no active records.
