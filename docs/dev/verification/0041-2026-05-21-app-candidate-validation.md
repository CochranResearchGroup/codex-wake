# App Candidate Validation Verification

Date: 2026-05-21

## Scope

Validate optional resume-backed status checks for `codex-wake app candidates`.

## Implementation

- Added `codex-wake app candidates --validate`.
- Added `codex-wake app candidates --validate --only-idle`.
- Validation uses `thread/resume` through the existing status helper and does not call `turn/start`.
- JSON rows now include `validation`; validated rows include `status_type` and `status` when resume succeeds.
- Resume failures stay row-local as `validation: resume_failed` with `validation_error`.

## Source Validation

Focused tests:

```text
PYTHONPATH=src python -m unittest tests.test_cli tests.test_app_server
```

Result:

```text
Ran 36 tests in 0.290s
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
Ran 86 tests in 0.652s
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
--validate            check each candidate with thread/resume without
                      starting a turn
--only-idle           with --validate, only print candidates whose resumed
                      status is idle
```

Validated repo candidates:

```text
PYTHONPATH=src python -m codex_wake.cli app candidates --cwd "$PWD" --validate --json --limit 2
```

Result: two local repo candidates returned `validation: resume_ok` and `status_type: idle`.

Idle-only repo candidates:

```text
PYTHONPATH=src python -m codex_wake.cli app candidates --cwd "$PWD" --validate --only-idle --json --limit 2
```

Result: returned the same two idle candidates after filtering.

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

Result included `--validate` and `--only-idle`.

Installed idle-only validation:

```text
codex-wake app candidates --cwd "$PWD" --validate --only-idle --json --limit 2
```

Result: two local repo candidates returned `validation: resume_ok` and `status_type: idle`.

## Known Gaps

- Validation checks current resumed thread status but does not reserve or lock the thread.
- A thread can become active after validation and before wake registration.
