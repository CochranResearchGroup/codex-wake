# App-Server Target Discovery Verification

Date: 2026-05-21

## Scope

Validate `codex-wake app candidates`, a read-only local discovery surface for rollout-backed app-server thread ids.

## Implementation

- Added local session rollout candidate discovery in `src/codex_wake/app_server.py`.
- Added `codex-wake app candidates` with text and JSON output.
- Added optional `--codex-home`, `--cwd`, and `--limit` controls.
- Updated README and app-server mode documentation.

## Source Validation

Focused tests:

```text
PYTHONPATH=src python -m unittest tests.test_app_server tests.test_cli
```

Result:

```text
Ran 33 tests in 0.348s
OK
```

Compile:

```text
PYTHONPATH=src python -m compileall -q src tests
```

Result: pass.

Full unit suite:

```text
PYTHONPATH=src python -m unittest discover -s tests
```

Result:

```text
Ran 83 tests in 0.676s
OK
```

Diff check:

```text
git diff --check
```

Result: pass.

## Source CLI Smoke

Help:

```text
PYTHONPATH=src python -m codex_wake.cli app candidates --help
```

Result included:

```text
usage: codex-wake app candidates [-h] [--codex-home CODEX_HOME] [--cwd CWD]
                                 [--limit LIMIT] [--json]
```

Local candidates:

```text
PYTHONPATH=src python -m codex_wake.cli app candidates --limit 3
```

Result: printed recent local rollout-backed thread ids and the follow-up command:

```text
Use: codex-wake app status --resume <THREAD_ID>
```

Repo-filtered JSON:

```text
PYTHONPATH=src python -m codex_wake.cli app candidates --cwd "$PWD" --json --limit 5
```

Result: emitted JSON rows for local session rollouts whose `cwd` matched this repo, with `resumable_source` set to `local_session_rollout`.

## Installed Command Smoke

Refreshed installed user command from the working tree:

```text
uv tool install --force .
```

Result:

```text
Installed 3 executables: codex-wake, codex-wake-hook, codex-waked
```

Installed help:

```text
codex-wake app candidates --help
```

Result included:

```text
usage: codex-wake app candidates [-h] [--codex-home CODEX_HOME] [--cwd CWD]
                                 [--limit LIMIT] [--json]
```

Installed text smoke:

```text
codex-wake app candidates --limit 2
```

Result: printed two local rollout-backed candidates and:

```text
Use: codex-wake app status --resume <THREAD_ID>
```

Installed repo-filtered JSON smoke:

```text
codex-wake app candidates --cwd "$PWD" --json --limit 2
```

Result: emitted JSON rows for local session rollouts whose `cwd` matched this repo.

## Known Gaps

- Candidate discovery identifies local rollout-backed thread ids; it does not prove the thread is currently idle.
- Operators should run `codex-wake app status --resume <thread-id>` before registering an app-server wake.
- Discovery reads only rollout `session_meta` lines and does not surface prompt or transcript bodies.
