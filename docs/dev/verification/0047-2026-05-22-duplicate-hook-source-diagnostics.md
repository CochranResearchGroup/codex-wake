# Duplicate Hook Source Diagnostics

Date: 2026-05-22

Request: after the user-scope hook dogfood showed duplicate developer context,
make the overlap visible in the operator diagnostics.

## Change

Added read-only hook source diagnostics for:

- project hook source: `<repo>/.codex/hooks.json`
- user hook source: `$CODEX_HOME/hooks.json` or `~/.codex/hooks.json`

`codex-wake hook check` and `codex-wake doctor --json` now report installed
hook scopes and warn when `codex-wake-hook` is present in both project and user
sources.

## Source Validation

Focused tests:

```text
PYTHONPATH=src python -m unittest tests.test_hook_config tests.test_cli
.....................................
Ran 37 tests in 0.244s
OK
```

Full test suite:

```text
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
.........................................................................................
Ran 89 tests in 0.590s
OK
```

Compile check:

```text
python -m compileall -q src tests
```

Source CLI smoke against this repo:

```text
PYTHONPATH=src python -m codex_wake.cli --wake-root .codex/wake hook check
hook_project_config_installed=true
hook_user_config_installed=true
hook_installed_scopes=project,user
hook_duplicate_install=true
hook_overlap_warning=codex-wake-hook is installed in both project and user hook sources; Codex may run both and inject duplicate wake context.
```

## Installed Runtime Validation

Refreshed the user-scoped installed tool from this working tree:

```text
uv tool install --force --reinstall .
Installed 3 executables: codex-wake, codex-wake-hook, codex-waked
```

Installed `doctor --json` reports the overlap:

```json
{
  "duplicate_installed": true,
  "installed_scopes": [
    "project",
    "user"
  ],
  "overlap_warning": "codex-wake-hook is installed in both project and user hook sources; Codex may run both and inject duplicate wake context."
}
```

Installed `hook check` reports the same text fields:

```text
hook_project_config=/home/ecochran76/workspace.local/codex-wake/.codex/hooks.json
hook_project_config_installed=true
hook_user_config=/home/ecochran76/.codex/hooks.json
hook_user_config_installed=true
hook_installed_scopes=project,user
hook_duplicate_install=true
hook_overlap_warning=codex-wake-hook is installed in both project and user hook sources; Codex may run both and inject duplicate wake context.
```

Wake root remained clean:

```json
{
  "active_total": 0,
  "archived_total": 10,
  "terminal_total": 0
}
```

## Result

Pass. Operators can now see when both hook sources are installed before running
a live wake dogfood. The change only reports overlap; it does not automatically
trust, disable, or remove either hook source.
