# CI Release Gates

Date: 2026-05-19
Lane: P16

## Scope

Add public GitHub Actions release gates for non-live validation.

## Workflow

Added `.github/workflows/ci.yml`.

The workflow runs on push to `main` and on pull requests. It uses a Python matrix:

- Python 3.11
- Python 3.12

Each matrix job runs:

```bash
python -m compileall -q src tests .codex/hooks
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
python -m venv /tmp/codex-wake-build
/tmp/codex-wake-build/bin/python -m pip install --upgrade pip build
/tmp/codex-wake-build/bin/python -m build
python -m venv /tmp/codex-wake-ci
/tmp/codex-wake-ci/bin/python -m pip install --upgrade pip
/tmp/codex-wake-ci/bin/python -m pip install dist/*.whl
/tmp/codex-wake-ci/bin/codex-wake --help
/tmp/codex-wake-ci/bin/codex-waked --once --no-dispatch --wake-root /tmp/codex-wake-ci-empty
printf '{"prompt":"hello","cwd":"%s"}' "$PWD" | /tmp/codex-wake-ci/bin/codex-wake-hook
TMUX_PANE='%11' TMUX='/tmp/tmux-1000/default,123,0' \
  /tmp/codex-wake-ci/bin/codex-wake --wake-root /tmp/codex-wake-ci-runtime after 1m -- "CI smoke wake"
/tmp/codex-wake-ci/bin/codex-wake --wake-root /tmp/codex-wake-ci-runtime list
```

The workflow intentionally avoids live tmux dispatch, Codex hook trust UI, and user systemd service checks.

## Local Validation

Before pushing the workflow, the same release-gate sequence was run locally from the repo root. The first attempt showed this workstation's Python is externally managed, so the workflow build step was changed to use a temporary venv. The venv-based sequence then passed.

Key local outcomes:

- Unit tests: `44` tests passed.
- Package build produced source and wheel artifacts.
- Installed wheel exposed `codex-wake`, `codex-waked`, and `codex-wake-hook`.
- Non-wake hook smoke returned empty output.
- CLI wake creation smoke wrote a pending `not_before` wake with tmux environment variables but no live dispatch.

## Upstream CI Evidence

First pushed run:

- Run: `26092513119`
- URL: `https://github.com/CochranResearchGroup/codex-wake/actions/runs/26092513119`
- Result: success
- Note: GitHub emitted a Node 20 deprecation warning for `actions/checkout@v4` and `actions/setup-python@v5`.

The workflow was then updated to `actions/checkout@v6` and `actions/setup-python@v6`.

Final pushed run:

- Commit: `72e95f5879e5dd63e50203401b62259b7e119dda`
- Run: `26092549749`
- URL: `https://github.com/CochranResearchGroup/codex-wake/actions/runs/26092549749`
- Result: success

Jobs:

- `Release gates (3.12)`: success
- `Release gates (3.11)`: success

Both jobs completed:

- Check out repository
- Set up Python
- Compile sources
- Run unit tests
- Build package
- Smoke installed wheel

## Result

Pass. P16 is closed.
