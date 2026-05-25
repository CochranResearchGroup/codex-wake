# OpenClaw Gateway Capability Probe

Date: 2026-05-25

Plan: `docs/dev/plans/0040-2026-05-25-openclaw-gateway-wake-transport.md`

## Scope

Execute P40 Slice 1: identify the narrowest supported OpenClaw Gateway path for
starting a real agent turn with an explicit agent and session key.

## Current State

The OpenClaw checkout was dirty with unrelated local work in Slack/status files,
so this pass treated that repo as read/probe-only. No OpenClaw source files were
edited.

## Selected Dispatch Surface

Use the Gateway `agent` method.

Two supported operator surfaces exist:

```bash
openclaw agent \
  --agent main \
  --session-key agent:main:<session> \
  --message "..." \
  --timeout 120 \
  --json
```

```bash
openclaw gateway call agent \
  --expect-final \
  --timeout 180000 \
  --json \
  --params '{"message":"...","agentId":"main","sessionKey":"agent:main:<session>","deliver":false,"timeout":120,"idempotencyKey":"..."}'
```

For the first `codex-wake` sidecar implementation, prefer the direct Gateway
method through a small client when practical. Use the `openclaw agent` CLI as a
stable fallback or diagnostic parity check, because its help text and source
confirm that it runs through the Gateway.

## Source Evidence

- `openclaw agent --help` says the command runs an agent turn via the Gateway
  and accepts `--agent`, `--session-key`, `--message`, `--deliver`,
  `--reply-channel`, `--reply-to`, `--timeout`, and `--json`.
- `src/cli/program/register.agent.ts` registers the CLI surface and describes
  the command as `Run an agent turn via the Gateway`.
- `src/commands/agent-via-gateway.ts` calls `callGateway` with:
  - `method: "agent"`
  - `params.message`
  - `params.agentId`
  - `params.sessionKey`
  - `params.deliver`
  - `params.channel`
  - `params.replyChannel`
  - `params.replyAccountId`
  - `params.timeout`
  - `params.lane`
  - `params.extraSystemPrompt`
  - `params.idempotencyKey`
  - `expectFinal: true`

## Runtime Evidence

Gateway health:

```bash
openclaw gateway status --deep --require-rpc --json
```

Relevant result:

- CLI version: `2026.5.22`
- Gateway URL: `ws://127.0.0.1:18789`
- RPC: `ok: true`
- RPC capability: `admin_capable`
- Slack default account: `running: true`, `connected: true`, `healthState:
  healthy`

Recent target session discovery:

```bash
openclaw sessions --agent main --active 180 --limit 20 --json
```

Relevant result:

- `agent:main:slack:channel:c0ahqqcg7j4`
- `sessionId: b0abcc43-cba3-40f0-8691-082ec7e49c97`
- `agentRuntime.id: codex`
- `modelProvider: openai-codex`
- `model: gpt-5.5`

Direct Gateway smoke:

```bash
openclaw gateway call agent \
  --expect-final \
  --timeout 180000 \
  --json \
  --params '{"message":"Reply with exactly P40_GATEWAY_PROBE_20260525_142100.","agentId":"main","sessionKey":"agent:main:codex-wake-p40-probe-20260525-142100","deliver":false,"timeout":120,"idempotencyKey":"codex-wake-p40-probe-20260525-142100"}'
```

Result:

- `runId: codex-wake-p40-probe-20260525-142100`
- `status: ok`
- `summary: completed`
- `result.payloads[0].text: P40_GATEWAY_PROBE_20260525_142100`
- `result.meta.agentMeta.sessionId:
  f9cf5373-3857-4efb-9092-f41a36736fee`
- `result.meta.agentMeta.provider: openai-codex`
- `result.meta.agentMeta.model: gpt-5.5`
- `result.meta.systemPromptReport.sessionKey:
  agent:main:codex-wake-p40-probe-20260525-142100`
- `result.meta.finalAssistantVisibleText:
  P40_GATEWAY_PROBE_20260525_142100`

## Dispatch Contract For P40 Slice 2

The first `openclaw_gateway` target should store:

- Gateway URL or resolvable Gateway command mode.
- `agent_id`.
- `session_key`.
- optional channel evidence: provider, workspace, channel id, thread ts.
- prompt text.
- explicit timeout seconds.
- explicit delivery mode.
- deterministic `idempotencyKey`, preferably derived from wake id.

The daemon dispatch attempt should record:

- method: `agent`
- run id / idempotency key
- response status and summary
- `result.meta.agentMeta.sessionId`
- provider/model when present
- final visible/raw text when present
- delivery status when present
- error type/message when dispatch fails

## Boundary Decision

No OpenClaw core patch is needed for Slice 2.

The first implementation can live entirely in `codex-wake` as an
`openclaw_gateway` sidecar transport that calls the Gateway `agent` method.
The OpenClaw plugin remains the preferred Slice 4 registration layer because it
can capture live session context without manual target copying.

## Known Gaps

- This probe used `deliver: false`; it proved Gateway execution and response
  metadata, not Slack-visible delivery.
- The real OpenClaw session key
  `agent:main:slack:channel:c0ahqqcg7j4` was discovered but not used for a
  delivered wake in this slice.
- OpenClaw plugin session-context capture remains unverified until Slice 4.

## Next Step

Implement P40 Slice 2 in `codex-wake`: add `openclaw_gateway` target records,
CLI validation, daemon dispatch through the Gateway `agent` method, and focused
tests for success, failure, timeout, and fake-target rejection.

