# App Status Resume Mode Verification

Date: 2026-05-21

## Scope

Validate `codex-wake app status --resume` and documentation for resumable app-server wake targets.

## Changes

- Added `codex-wake app status --resume <thread-id>`.
- Kept default `app status` on `thread/read`.
- `--resume` uses `thread/resume` and does not call `turn/start`.
- Updated README and app-server mode docs to explain resumable rollout-backed app-server wake targets.

## Source Validation

Focused tests:

```text
PYTHONPATH=src python -m unittest tests.test_app_server
PYTHONPATH=src python -m unittest tests.test_cli
```

Results:

```text
Ran 6 tests in 0.036s
OK

Ran 23 tests in 0.269s
OK
```

Compile and full suite:

```text
PYTHONPATH=src python -m compileall -q src tests
PYTHONPATH=src python -m unittest discover -s tests
```

Result:

```text
Ran 79 tests in 0.794s
OK
```

Diff check:

```text
git diff --check
```

Result: pass.

## CLI Smoke

Source-tree help:

```text
PYTHONPATH=src python -m codex_wake app status --help
```

Installed working-tree help after `uv tool install --force .`:

```text
codex-wake app status --help
```

Both showed:

```text
usage: codex-wake app status [-h] [--endpoint ENDPOINT] [--json] [--resume] thread_id
```

## Outcome

Pass. Operators now have both:

- `codex-wake app status <thread-id>` for a non-loading `thread/read` status check.
- `codex-wake app status --resume <thread-id>` for the same resume-backed status path used by dispatch preflight, without starting a turn.

## Follow-Up

This is an installed CLI/runtime change and should be included in the next release.
