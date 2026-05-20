# Wake Record Schema Versioning

Date: 2026-05-19
Lane: P22

## Scope

Validate the schema versioning contract and installed-visible schema command.

## Source Validation

Commands:

```bash
python -m compileall -q src tests .codex/hooks
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
```

Outcome:

- `70` tests passed.
- Compileall passed.

Coverage added:

- Schema summary reports `schema_version=1`.
- Schema compatibility is `additive_optional_fields`.
- Required fields include `schema_version`.
- Predicate types include `process_done`.
- Optional fields include `dispatch_result`.
- Schema bump triggers include incompatible predicate semantic changes.
- CLI `schema` and `schema --json` expose the same metadata.

## Source CLI Smoke

Commands:

```bash
ROOT=/tmp/codex-wake-p22-source
PYTHONPATH=src python -m codex_wake.cli --wake-root "$ROOT/wake" schema
PYTHONPATH=src python -m codex_wake.cli --wake-root "$ROOT/wake" schema --json
```

Outcome:

```text
schema_json_ok=true
schema_version=1
compatibility=additive_optional_fields
schema_doc=docs/dev/wake-record-schema.md
predicate_types=not_before,file_exists,file_changed,process_done
target_transports=tmux,app-server
optional_fields=context_paths,evidence_paths,last_error,previous_status,archived_at,dispatch_result
```

## Installed-Wheel Smoke

Commands:

```bash
python -m venv /tmp/codex-wake-p22-build
/tmp/codex-wake-p22-build/bin/python -m pip install --upgrade pip build
/tmp/codex-wake-p22-build/bin/python -m build
python -m venv /tmp/codex-wake-p22-install
/tmp/codex-wake-p22-install/bin/python -m pip install --upgrade pip
/tmp/codex-wake-p22-install/bin/python -m pip install dist/*.whl
ROOT=/tmp/codex-wake-p22-installed
/tmp/codex-wake-p22-install/bin/codex-wake --wake-root "$ROOT/wake" schema
/tmp/codex-wake-p22-install/bin/codex-wake --wake-root "$ROOT/wake" schema --json
```

Outcome:

```text
installed_schema_json_ok=true
schema_version=1
compatibility=additive_optional_fields
schema_doc=docs/dev/wake-record-schema.md
schema_bump_required_for=rename_or_remove_required_fields,...
```

## Known Limits

- This lane documents schema version `1`; it does not migrate or bump records.
- `schema` reports the current compatibility policy, not a full JSON Schema validator.
- Existing wake records are not rewritten.

## Result

Pass. P22 is closed.
