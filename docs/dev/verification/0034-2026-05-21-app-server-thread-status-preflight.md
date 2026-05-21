# App-Server Thread Status Preflight Verification

Date: 2026-05-21

## Scope

Validate the app-server thread-status preflight and read-only status helper without starting a live app-server turn.

## Changes

- Added `StdioAppServerClient.read_thread()` for `thread/read`.
- Added `codex-wake app status <thread-id>` and `--json` output.
- Added app-server dispatch preflight after `thread/resume`.
- Dispatch now records `app_server_preflight` evidence.
- Dispatch only calls `turn/start` when the resumed thread status is `idle`.
- Dispatch requeues `active` app-server threads with backoff instead of starting a new turn.

## Source Validation

Compile:

```text
PYTHONPATH=src python -m compileall -q src tests
```

Result: pass.

Focused tests:

```text
PYTHONPATH=src python -m unittest tests.test_app_server
PYTHONPATH=src python -m unittest tests.test_cli
```

Results:

```text
Ran 5 tests in 0.042s
OK

Ran 22 tests in 0.336s
OK
```

Full test suite:

```text
PYTHONPATH=src python -m unittest discover -s tests
```

Result:

```text
Ran 77 tests in 0.664s
OK
```

The plain `PYTHONPATH=src python -m unittest discover` command was not used as final validation because it discovered zero tests in this repo layout.

## CLI Smoke

Source-tree help:

```text
PYTHONPATH=src python -m codex_wake app status --help
```

Result included:

```text
usage: codex-wake app status [-h] [--endpoint ENDPOINT] [--json] thread_id
```

Source-tree app wake creation smoke:

```text
PYTHONPATH=/home/ecochran76/workspace.local/codex-wake/src python -m codex_wake --wake-root "$ROOT/wake" app after thread_abc 1m -- 'App wake smoke'
PYTHONPATH=/home/ecochran76/workspace.local/codex-wake/src python -m codex_wake --wake-root "$ROOT/wake" list --json
```

Result: created a pending app-server-targeted wake with:

```json
{
  "target": {
    "endpoint": "stdio://",
    "thread_id": "thread_abc",
    "transport": "app-server"
  }
}
```

## Installed Runtime Smoke

Installed the working tree into the user-scoped uv tool:

```text
uv tool install --force .
```

Result:

```text
Installed 3 executables: codex-wake, codex-wake-hook, codex-waked
```

Installed CLI help:

```text
codex-wake app status --help
```

Result included:

```text
usage: codex-wake app status [-h] [--endpoint ENDPOINT] [--json] thread_id
```

Installed app wake creation smoke:

```text
codex-wake --wake-root "$ROOT/wake" app after thread_abc 1m -- 'Installed app wake smoke'
codex-wake --wake-root "$ROOT/wake" list --json
```

Result: created a pending app-server-targeted wake with `transport` set to `app-server`.

## Outcome

Pass. The app-server path now has a read-only status helper and a dispatch preflight that prevents `turn/start` for active resumed threads.

## Gaps

- No live app-server `turn/start` dogfood was run in this slice.
- `app status` requires a known thread id; thread discovery remains a future operator-surface lane.
- The user-scoped installed tool was updated from this working tree but still reports package version `0.4.8`; release versioning should happen in the next release lane.
