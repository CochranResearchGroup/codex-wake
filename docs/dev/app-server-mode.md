# App-Server Mode

Status: MVP stdio transport implemented
Verified: 2026-05-18 with Codex CLI 0.130.0

## Contract

Codex Wake supports an app-server target record shape for controlled dispatch:

```json
{
  "target": {
    "transport": "app-server",
    "endpoint": "stdio://",
    "thread_id": "thread_..."
  }
}
```

The implemented path starts or uses a stdio app-server client and sends:

1. `initialize`
2. `thread/resume`
3. `turn/start`

The wake prompt sent to `turn/start` is still the canonical short prompt:

```text
WAKE_TRIGGER_ID=<wake-id>
Resume the scheduled wake task.
```

## CLI

Use explicit app-server commands for time-based wakes:

```bash
codex-wake app after thread_abc 45m -- "Resume this thread through app-server."
codex-wake app at thread_abc "2026-05-19T17:30:00-05:00" -- "Check the release state."
```

The older `--app-server-thread-id` option on time commands remains available for compatibility, but the `app` subcommands are the clearer operator surface.

When `turn/start` is accepted, Codex Wake records available response metadata in `dispatch_result`, including `thread_id` and `turn_id` when returned by app-server.

## Source Verification

Official docs checked on 2026-05-18:

- App-server supports stdio, WebSocket, Unix socket, and off transports.
- WebSocket transport is experimental and unsupported.
- Local WebSocket listeners are appropriate for localhost and SSH forwarding.
- Non-loopback WebSocket listeners require WebSocket auth before remote exposure.

Local Codex CLI checked on 2026-05-18:

- `codex-cli 0.130.0`
- `codex app-server --listen stdio://`
- `codex app-server generate-json-schema --experimental`
- `codex app-server generate-ts --experimental`

Generated schema confirmed:

- `thread/resume` uses `ThreadResumeParams` with `threadId`.
- `turn/start` uses `TurnStartParams` with `threadId` and text `input`.

## Safety Boundary

Only `stdio://` is implemented in Codex Wake right now. Non-stdio endpoints are rejected during CLI creation and dispatch validation.

WebSocket support is deferred until there is a clear local operator need and a testable auth setup. If implemented, it must enforce one of:

- loopback-only `ws://127.0.0.1:<port>`
- SSH-forwarded loopback
- authenticated `wss://` for non-local access

Do not expose unauthenticated non-loopback WebSocket app-server endpoints.
