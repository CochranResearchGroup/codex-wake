# App-Server Contract Refresh Verification

Date: 2026-05-20

## Scope

Refresh app-server controlled-dispatch design against the current local Codex CLI without starting a live wake turn.

## Evidence

Local Codex CLI version:

```text
codex-cli 0.131.0
```

`codex app-server --help` confirmed:

- `--listen <URL>` supports `stdio://`, `unix://`, `unix://PATH`, `ws://IP:PORT`, and `off`.
- WebSocket auth modes are `capability-token` and `signed-bearer-token`.
- WebSocket auth options include token file, token digest, shared secret file, issuer, audience, and clock skew settings.

Schema generation command:

```text
codex app-server generate-json-schema --out /tmp/codex-app-schema-p29 --experimental
```

Generated schema evidence:

- `v2/ThreadResumeParams.json` requires `threadId`, supports `cwd`, and documents that `persistExtendedHistory` is deprecated and ignored.
- `v2/TurnStartParams.json` requires `threadId` and `input`.
- `v2/TurnStartResponse.json` requires a `turn` object.
- `v2/ThreadStatusChangedNotification.json` exposes thread status values including `idle`, `active`, `systemError`, and `notLoaded`.

Source-tree stdio initialize smoke:

```text
PYTHONPATH=src python - <<'PY'
from codex_wake.app_server import StdioAppServerClient
client = StdioAppServerClient(timeout_seconds=10)
try:
    result = client.initialize()
    print(result)
finally:
    client.close()
PY
```

Result:

```text
{'userAgent': 'codex-wake/0.131.0 (Ubuntu 24.4.0; x86_64) xterm-256color (codex-wake; 0.1.0)', 'codexHome': '/home/ecochran76/.codex', 'platformFamily': 'unix', 'platformOs': 'linux'}
```

## Outcome

Pass. The current local app-server contract still supports the implemented stdio dispatch primitives: `initialize`, `thread/resume`, and `turn/start`. No immediate source code change is required for the existing unit-tested stdio path.

## Follow-Up

The next implementation lane should add either:

- a disposable-thread app-server dispatch dogfood that proves `turn/start` acceptance against a real thread; or
- a thread-status preflight helper that reads app-server thread status before starting a wake turn.

WebSocket dispatch remains deferred until there is a concrete local operator need and a testable auth setup.
