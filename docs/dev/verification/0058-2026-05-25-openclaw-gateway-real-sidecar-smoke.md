# OpenClaw Gateway Real Sidecar Smoke

Date: 2026-05-25

Plan: `docs/dev/plans/0040-2026-05-25-openclaw-gateway-wake-transport.md`

## Scope

Execute P40 Slice 3: run a real `openclaw_gateway` wake against an active
OpenClaw session and verify a unique response through runtime transcript
evidence.

## Target

- Agent: `main`
- Session key: `agent:main:slack:channel:c0ahqqcg7j4`
- OpenClaw session id: `b0abcc43-cba3-40f0-8691-082ec7e49c97`
- Channel evidence: `C0AHQQCG7J4`
- Wake root: `.codex/wake`
- Unique expected response: `CODEX_WAKE_OPENCLAW_SLICE3_20260525_203917`

Gateway readiness before the smoke:

```bash
openclaw gateway status --deep --require-rpc --json
```

Relevant result:

- CLI version `2026.5.22`
- Gateway `ws://127.0.0.1:18789`
- RPC `ok: true`
- RPC capability `admin_capable`

Session discovery before the smoke:

```bash
openclaw sessions --agent main --active 240 --limit 20 --json
```

Relevant result:

- `agent:main:slack:channel:c0ahqqcg7j4`
- `sessionId: b0abcc43-cba3-40f0-8691-082ec7e49c97`
- provider `openai-codex`
- model `gpt-5.5`

## Wake Creation

Command:

```bash
PYTHONPATH=src python -m codex_wake.cli \
  --wake-root .codex/wake \
  openclaw after \
  --agent main \
  --session-key agent:main:slack:channel:c0ahqqcg7j4 \
  --workspace default \
  --channel C0AHQQCG7J4 \
  --openclaw-path /home/ecochran76/.nvm/versions/node/v24.14.0/bin/openclaw \
  --deliver \
  --timeout 180 \
  --gateway-timeout-ms 240000 \
  5s -- 'P40 Slice 3 real OpenClaw Gateway wake smoke. First inspect this wake record and verify the predicate. Then reply with exactly CODEX_WAKE_OPENCLAW_SLICE3_20260525_203917 and stop.'
```

Created wake:

- `wake_20260525_203934_201f`
- pending record:
  `.codex/wake/pending/wake_20260525_203934_201f.json`

## Dispatch

First daemon pass:

```bash
PYTHONPATH=src python -m codex_wake.daemon --wake-root .codex/wake --once
```

Result:

```text
checked=1 fired=1 failed=0 pending=0 dispatched=1 submitted=0 requeued=1
```

The first attempt requeued because the sidecar sent `expectFinal` in the JSON
params. The OpenClaw Gateway contract expects final-response waiting as the CLI
flag `--expect-final`, not as an `agent` method param:

```text
invalid agent params: at root: unexpected property 'expectFinal'
```

Fix applied during this slice:

- removed `expectFinal` from `openclaw_gateway_agent_params`;
- added a regression assertion that the params omit `expectFinal`;
- cleared stale `last_error` on successful OpenClaw Gateway retry;
- widened provider/model parsing to support `meta.agentMeta`.

Second daemon pass after the fix:

```bash
PYTHONPATH=src python -m codex_wake.daemon --wake-root .codex/wake --once
```

Result:

```text
checked=1 fired=1 failed=0 pending=0 dispatched=1 submitted=1 requeued=0
```

Submitted wake evidence:

- `attempts: 2`
- `dispatch_result.transport: openclaw_gateway`
- `dispatch_result.gateway_method: agent`
- `dispatch_result.run_id: codex-wake:wake_20260525_203934_201f`
- `dispatch_result.session_id: b0abcc43-cba3-40f0-8691-082ec7e49c97`
- `dispatch_result.session_key: agent:main:slack:channel:c0ahqqcg7j4`
- `dispatch_result.status: ok`
- `dispatch_result.summary: completed`
- `dispatch_result.payload_text_summary.text_count: 1`
- `dispatch_result.payload_text_summary.total_length: 42`

The wake was archived after verification:

```bash
PYTHONPATH=src python -m codex_wake.cli --wake-root .codex/wake archive wake_20260525_203934_201f
```

Final wake-root status:

- `active_total: 0`
- `terminal_total: 0`
- `archived_total: 14`
- `counts_by_target_transport.openclaw_gateway: 1`

## Transcript Evidence

OpenClaw transcript search:

```bash
rg -n "CODEX_WAKE_OPENCLAW_SLICE3_20260525_203917|codex-wake:wake_20260525_203934_201f|wake_20260525_203934_201f" \
  /tmp/openclaw/openclaw-2026-05-25.log \
  /home/ecochran76/.openclaw/agents/main/agent/codex-home/sessions/2026/05/25/rollout-2026-05-25T12-26-13-019e602c-4096-7443-956c-e87def4e8307.jsonl \
  /home/ecochran76/.openclaw/agents/main/sessions/b0abcc43-cba3-40f0-8691-082ec7e49c97.trajectory.jsonl
```

Relevant hits:

- trajectory line 68: `session.started` for
  `runId: codex-wake:wake_20260525_203934_201f` and session key
  `agent:main:slack:channel:c0ahqqcg7j4`;
- rollout line 121: user message includes
  `WAKE_TRIGGER_ID=wake_20260525_203934_201f`, wake root, and record cwd;
- rollout line 136: final agent message
  `CODEX_WAKE_OPENCLAW_SLICE3_20260525_203917`;
- rollout line 137: assistant output text
  `CODEX_WAKE_OPENCLAW_SLICE3_20260525_203917`;
- rollout line 139: task complete with turn id
  `019e60de-8978-7160-ba2c-87b46463d7fc`;
- OpenClaw log line 2387: console log message
  `CODEX_WAKE_OPENCLAW_SLICE3_20260525_203917`;
- trajectory line 80: `session.ended` with `status: success` for the same
  wake run id.

Slack Mirror search against the mirrored private `oc-main-agent` channel was
also attempted. It returned no matching message because the mirror's latest
indexed channel timestamp was still older than this smoke. The accepted Slice 3
proof is therefore OpenClaw transcript/log evidence, not Slack Mirror evidence.

## Validation After Fix

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
python -m compileall -q src tests .codex/hooks
git diff --check
```

Results:

- 112 tests passed.
- Compile check passed.
- Diff whitespace check passed.

## Acceptance Result

Slice 3 passes:

- used a real active OpenClaw `agent_id` and `session_key`;
- ran `codex-waked --once` with dispatch enabled;
- produced a real Gateway-submitted OpenClaw turn;
- verified the unique expected response in OpenClaw rollout/trajectory/log
  evidence;
- archived the smoke wake so the repo wake root has no active or terminal
  records.

## Next Step

Proceed to P40 Slice 4: decide and implement the OpenClaw plugin registration
surface so OpenClaw agents can schedule these wakes from live session context
without manually copying `agent_id`, `session_key`, and channel evidence.
