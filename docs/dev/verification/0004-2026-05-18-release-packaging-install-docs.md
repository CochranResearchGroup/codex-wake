# Release Packaging And Install Docs Verification

Date: 2026-05-18
Branch: `main`

## Version Boundary

Selected `v0.1.0` as the initial MVP release boundary. There were no existing git tags before this lane.

Package metadata:

```toml
name = "codex-wake"
version = "0.1.0"
license = "MIT"
```

## Operator Docs

Updated `README.md` with:

- requirements
- source and GitHub install commands
- installed command verification
- `UserPromptSubmit` hook setup with `codex-wake-hook`
- `after`, `at`, and `file` examples
- daemon one-shot and polling usage
- state layout
- current limits

Added release notes:

```text
docs/releases/v0.1.0.md
```

## Packaging

Added installed hook command:

```toml
codex-wake-hook = "codex_wake.hook:main"
```

Built source and wheel artifacts:

```bash
rm -rf dist build src/codex_wake.egg-info
uv build
```

Observed:

```text
Successfully built dist/codex_wake-0.1.0.tar.gz
Successfully built dist/codex_wake-0.1.0-py3-none-any.whl
```

## User-Scope Install Refresh

Refreshed the installed command surface:

```bash
uv tool install --force .
command -v codex-wake
command -v codex-waked
command -v codex-wake-hook
codex-wake --help
codex-waked --once --no-dispatch --wake-root /tmp/codex-wake-p11-empty
printf '{"prompt":"hello","cwd":"/tmp"}' | codex-wake-hook
```

Observed:

```text
Installed 3 executables: codex-wake, codex-wake-hook, codex-waked
/home/ecochran76/.local/bin/codex-wake
/home/ecochran76/.local/bin/codex-waked
/home/ecochran76/.local/bin/codex-wake-hook
checked=0 fired=0 failed=0 pending=0 dispatched=0 submitted=0 requeued=0
hook nowake exit=0 output_bytes=0
```

## Source Validation

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
python -m compileall -q src tests .codex/hooks
python /home/ecochran76/workspace.local/agent-policies/repo-policy-selector/scripts/audit_planning_contract.py --repo-root /home/ecochran76/workspace.local/codex-wake --json
```

Observed:

```text
Ran 30 tests in 0.120s
OK
planning audit ok: true
```

