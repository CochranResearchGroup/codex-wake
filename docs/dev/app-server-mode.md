# App-Server Mode

Status: MVP stdio transport implemented
Verified: 2026-05-20 with Codex CLI 0.131.0

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

Inspect an app-server thread without starting a turn:

```bash
codex-wake app candidates
codex-wake app candidates --cwd "$PWD" --json
codex-wake app status thread_abc
codex-wake app status --resume thread_abc
codex-wake app status --json thread_abc
```

Dispatch preflight resumes the target thread, records `app_server_preflight`
status evidence, and only calls `turn/start` when the resumed thread reports
`idle`. If the thread reports `active`, Codex Wake requeues the wake with
backoff instead of starting another turn. Malformed status or non-idle
unhealthy states fail the wake record visibly.

App-server wake targets must be resumable rollout-backed thread ids. A bare
`thread/start` response is not enough if no turn has materialized a rollout for
later resume. Plain `app status` uses `thread/read` and can report `notLoaded`
for a resumable thread in a fresh stdio app-server process. Use `app status
--resume` when checking the same path dispatch will use; it calls
`thread/resume` and reports the resumed status without starting a turn.

`app candidates` scans local Codex session rollout metadata under
`~/.codex/sessions` and reports recent rollout-backed thread ids. It reads only
the first `session_meta` line from each rollout file and does not emit prompt or
transcript body content. Use `--cwd "$PWD"` to narrow the list to a repo, then
run `codex-wake app status --resume <thread-id>` before registering an
app-server wake.

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

Local Codex CLI refreshed on 2026-05-20:

- `codex-cli 0.131.0`
- `codex app-server --listen stdio://`
- `codex app-server generate-json-schema --out /tmp/codex-app-schema-p29 --experimental`
- The generated schema now includes v2 schema files under `v2/`.
- `ThreadResumeParams` still requires `threadId` and supports `cwd`; `persistExtendedHistory` is deprecated and ignored but remains accepted for older clients.
- `TurnStartParams` still requires `threadId` and `input`, and supports optional turn-scoped overrides such as `cwd`, model, effort, permissions, and sandbox policy.
- `TurnStartResponse` still returns a required `turn` object.
- `ThreadStatusChangedNotification` exposes `idle`, `active`, `systemError`, and `notLoaded` thread states, which is the likely future basis for safer app-server wake preflight.
- A source-tree stdio initialize smoke succeeded and returned Codex home, platform, and user-agent metadata.

## Current Implementation Boundary

The current implementation is suitable for unit-tested stdio dispatch and for future controlled dogfood against a known thread id. It should not yet be treated as a full replacement for the tmux path because:

- live app-server dispatch has not been dogfooded against a deliberately created disposable thread;
- current dispatch treats `turn/start` acceptance as the app-server acknowledgement, while tmux dispatch still relies on the Codex hook ack file;
- thread status preflight is implemented for resumed-thread status, but still needs a live disposable-thread dogfood.

The next app-server implementation lane should add a bounded operator smoke for a disposable thread.

## Safety Boundary

Only `stdio://` is implemented in Codex Wake right now. Non-stdio endpoints are rejected during CLI creation and dispatch validation.

WebSocket support is deferred until there is a clear local operator need and a testable auth setup. If implemented, it must enforce one of:

- loopback-only `ws://127.0.0.1:<port>`
- SSH-forwarded loopback
- authenticated `wss://` for non-local access

Do not expose unauthenticated non-loopback WebSocket app-server endpoints.
