# OpenClaw Gateway Wake Transport

Date: 2026-05-25

## Scope

Design and implement the OpenClaw-native wake path as a Gateway-backed
transport plus, if the Gateway transport proves viable, an OpenClaw plugin that
registers wake requests from inside live OpenClaw turns.

The target shape is hybrid:

- `codex-wake` owns durable wake records, trigger evaluation, retry state,
  cancellation, retention, and operator inspection.
- An OpenClaw Gateway dispatcher owns the actual delayed agent turn for
  OpenClaw Slack/API sessions.
- An OpenClaw plugin owns agent-facing registration when OpenClaw has live
  session context available.

## Current State

`codex-wake` already supports tmux wakes and Codex app-server wakes. OpenClaw
Slack/API sessions are not tmux panes, so `TMUX_PANE` is normally empty and the
tmux transport cannot target them.

The first OpenClaw smoke attempt was not a real wake proof. Slack Mirror showed
that the `#oc-main-agent` run used a placeholder app-server thread id
(`noop-smoke-test`) and `codex-waked --no-dispatch`. That can prove a wake
record and predicate transition, but it cannot prove a future OpenClaw turn,
Slack delivery, hook ack, or operator-visible behavior.

OpenClaw has plugin and Gateway surfaces that appear suitable for this lane:
plugin commands/tools, plugin services, session workflow scheduling, and
Gateway methods. A direct core patch is not the preferred first move.

Slice 1 is recorded in
`docs/dev/verification/0056-2026-05-25-openclaw-gateway-capability-probe.md`.
The selected dispatch surface is the Gateway `agent` method, with
`openclaw agent --session-key ... --message ... --json` as the stable CLI
wrapper and direct `openclaw gateway call agent --expect-final --json` as the
sidecar proof path. No OpenClaw core patch is needed for Slice 2.

Slice 2 is recorded in
`docs/dev/verification/0057-2026-05-25-openclaw-gateway-target-implementation.md`.
`codex-wake` now has an `openclaw_gateway` target transport for creating
durable OpenClaw wake records, validating real `agent:<agent_id>:...` session
keys, dispatching through Gateway method `agent`, and storing sanitized
preflight/result evidence. Real Slack-visible delivery remains Slice 3.

## Non-Goals

- Do not treat `--no-dispatch` as wake success.
- Do not use placeholder thread ids, fake session keys, or inferred Slack
  targets as validation proof.
- Do not modify OpenClaw core unless a concrete SDK or Gateway seam is missing.
- Do not make OpenClaw session store or generic turn lifecycle logic
  `codex-wake`-owned.
- Do not store Slack tokens, Gateway tokens, raw transcripts, or private
  message bodies in tracked fixtures or wake records.
- Do not require tmux for OpenClaw Slack/API sessions.

## Architecture Decision

Use a sidecar/Gateway transport first, then productize registration through an
OpenClaw plugin.

Reasoning:

- A sidecar transport can be implemented and tested in this repo without
  editing OpenClaw core.
- The Gateway is the right execution boundary for starting a real OpenClaw
  agent turn.
- A plugin is the durable OpenClaw-native registration boundary because it can
  capture the current `agentId`, `sessionKey`, and channel/thread context
  without guessing.
- Core changes should be limited to missing generic seams, such as session
  context exposure or scheduled-turn dispatch evidence.

## Target Record Shape

Add a new target transport:

```json
{
  "transport": "openclaw_gateway",
  "gateway": {
    "url": "ws://127.0.0.1:18789",
    "token_env": "OPENCLAW_GATEWAY_TOKEN"
  },
  "openclaw": {
    "agent_id": "main",
    "session_key": "agent:main:slack:channel:c0ahqqcg7j4",
    "channel": {
      "provider": "slack",
      "workspace": "default",
      "channel_id": "C0AHQQCG7J4",
      "thread_ts": "1779729958.218239"
    }
  },
  "dispatch": {
    "deliver": false,
    "timeout_seconds": 120,
    "gateway_timeout_ms": 180000
  }
}
```

Rules:

- Gateway auth fields may name environment variables; they must not contain
  secret values.
- `session_key` is required for OpenClaw registration unless a documented
  Gateway method can safely resolve the current session from channel refs.
- Channel refs are evidence and validation aids, not a substitute for
  `session_key`.
- Records must preserve `wake_id`, trigger evidence, dispatch attempt metadata,
  Gateway response metadata, and final validation evidence.
- Dispatch sends a short `WAKE_TRIGGER_ID=...` handoff prompt that points the
  OpenClaw agent back to the durable wake record. It does not embed the
  original wake prompt in the Gateway call.

## Status And Evidence

Reuse existing wake statuses where possible. Add transport-specific events
instead of broad new statuses:

- `openclaw_gateway_preflight`
- `openclaw_gateway_dispatch_attempt`
- `openclaw_gateway_dispatch_result`
- `openclaw_gateway_visibility_check`

Success for this transport requires more than `submitted=1`. The minimum proof
for OpenClaw wake success is:

- trigger matched;
- Gateway dispatch accepted the turn for the intended `agent_id` and
  `session_key`;
- a later OpenClaw transcript, Gateway result, or Slack Mirror message shows
  the unique wake marker or expected unique response.

## Implementation Slices

### Slice 1: Gateway Capability Probe

Inspect the current OpenClaw Gateway and CLI surfaces to identify the narrowest
supported way to start a turn in an existing session.

Acceptance criteria:

- Document the exact Gateway method or CLI command selected.
- Confirm how to pass `agent_id`, `session_key`, prompt text, timeout, and
  delivery behavior.
- Confirm what response metadata can be stored as dispatch evidence.
- Identify any missing plugin SDK or Gateway seam before proposing a core
  change.

### Slice 2: `openclaw_gateway` Target In `codex-wake`

Add record creation, validation, and dispatch support for the new transport.

Candidate CLI:

```bash
codex-wake --wake-root .codex/wake openclaw after \
  --agent main \
  --session-key agent:main:slack:channel:c0ahqqcg7j4 \
  --workspace default \
  --channel C0AHQQCG7J4 \
  --thread-ts 1779729958.218239 \
  --openclaw-path "$(command -v openclaw)" \
  30s \
  -- "Wake idempotently. Echo the unique wake marker, then inspect state."
```

Acceptance criteria:

- CLI rejects missing `session_key`, fake placeholder values, and unsupported
  placeholder targets.
- Wake JSON stores structured OpenClaw target metadata without secrets.
- Daemon dispatch records Gateway preflight, attempt, result, and failures.
- Focused tests cover record creation, validation errors, successful fake
  Gateway dispatch, Gateway failure, and timeout behavior.

Status: Implemented in source with fake Gateway validation. Real sidecar smoke
is Slice 3.

### Slice 3: Real Sidecar Smoke

Run the transport against a real OpenClaw session using a unique visible
message.

Acceptance criteria:

- Use a real active OpenClaw `agent_id` and `session_key`.
- Run without `--no-dispatch`.
- Verify the later response through Slack Mirror or OpenClaw transcript
  evidence.
- Record the exact wake id, session key, Slack target, Gateway response, and
  evidence retrieval path under `docs/dev/verification/`.

### Slice 4: OpenClaw Plugin Registration

Add an OpenClaw plugin only after Slice 2 proves the sidecar transport. The
plugin should make registration safe from inside OpenClaw turns.

Expected plugin behavior:

- register an agent-facing wake command/tool;
- capture current `agentId`, `sessionKey`, and channel/thread context from the
  OpenClaw runtime;
- write or request a `codex-wake` record with `transport=openclaw_gateway`;
- reject placeholder targets and no-dispatch smokes;
- return the wake id and required validation command to the requesting agent.

Acceptance criteria:

- Plugin can schedule a wake from `#oc-main-agent` without manual target
  copying.
- The scheduled wake later produces a unique Slack-visible response in the same
  intended session.
- Plugin behavior is covered by focused OpenClaw tests or a documented plugin
  harness smoke.

### Slice 5: Core Seam Decision

If the plugin cannot capture required session context or schedule a safe
Gateway turn through supported SDK surfaces, write a scoped OpenClaw seam plan.

Acceptance criteria:

- Name the missing seam precisely.
- Explain why sidecar and plugin-only approaches are insufficient.
- Keep any proposed OpenClaw core change generic and plugin-agnostic.

## Definition Of Done

This lane is complete when:

- `codex-wake` has a documented `openclaw_gateway` transport;
- fake targets and `--no-dispatch` false positives are rejected;
- a real Gateway-fired OpenClaw wake is verified in Slack Mirror or transcript
  evidence;
- an OpenClaw plugin or documented SDK blocker exists for live-session
  registration;
- roadmap, runbook, docs, and installed skill guidance are updated.
