# Runtime Retention Cleanup

Date: 2026-05-19
Lane: P20

## Scope

Validate dry-run-first cleanup for archived wake records.

## Source Validation

Commands:

```bash
python -m compileall -q src tests .codex/hooks
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
```

Outcome:

- `65` tests passed.
- Compileall passed.

Coverage added:

- Cleanup previews old archived records without deleting them.
- Cleanup with `--delete` removes only matching archived records.
- Fresh archived records are retained.
- Active records are not deleted by cleanup.
- CLI `cleanup --archive-terminal` archives terminal records before cleanup evaluation.
- CLI dry-run and delete output is deterministic enough for operator review.

## Source CLI Smoke

Commands:

```bash
ROOT=/tmp/codex-wake-p20-source
WAKE=$(PYTHONPATH=src python -m codex_wake.cli --wake-root "$ROOT/wake" after 1m -- 'P20 cleanup smoke' | awk '{print $1}')
PYTHONPATH=src python -m codex_wake.cli --wake-root "$ROOT/wake" cancel "$WAKE"
PYTHONPATH=src python -m codex_wake.cli --wake-root "$ROOT/wake" cleanup --archive-terminal --older-than 30d
# archived_at was set to 2026-04-01T00:00:00Z for retention smoke
PYTHONPATH=src python -m codex_wake.cli --wake-root "$ROOT/wake" cleanup --older-than 30d
PYTHONPATH=src python -m codex_wake.cli --wake-root "$ROOT/wake" cleanup --older-than 30d --delete
PYTHONPATH=src python -m codex_wake.cli --wake-root "$ROOT/wake" list --archived
```

Outcome:

```text
archived wake_20260520_011517_8e60 /tmp/codex-wake-p20-source/wake/archive/wake_20260520_011517_8e60.json
cleanup mode=dry-run older_than=30d archived=1 matched=0
would-delete wake_20260520_011517_8e60 ... retention_at=2026-04-01T00:00:00Z
cleanup mode=dry-run older_than=30d archived=0 matched=1
deleted wake_20260520_011517_8e60 ... retention_at=2026-04-01T00:00:00Z
cleanup mode=delete older_than=30d archived=0 matched=1
No wakes.
```

## Installed-Wheel Smoke

Commands:

```bash
python -m venv /tmp/codex-wake-p20-build
/tmp/codex-wake-p20-build/bin/python -m pip install --upgrade pip build
/tmp/codex-wake-p20-build/bin/python -m build
python -m venv /tmp/codex-wake-p20-install
/tmp/codex-wake-p20-install/bin/python -m pip install --upgrade pip
/tmp/codex-wake-p20-install/bin/python -m pip install dist/*.whl
ROOT=/tmp/codex-wake-p20-installed
WAKE=$(/tmp/codex-wake-p20-install/bin/codex-wake --wake-root "$ROOT/wake" after 1m -- 'P20 installed cleanup smoke' | awk '{print $1}')
/tmp/codex-wake-p20-install/bin/codex-wake --wake-root "$ROOT/wake" cancel "$WAKE"
/tmp/codex-wake-p20-install/bin/codex-wake --wake-root "$ROOT/wake" cleanup --archive-terminal --older-than 30d
# archived_at was set to 2026-04-01T00:00:00Z for retention smoke
/tmp/codex-wake-p20-install/bin/codex-wake --wake-root "$ROOT/wake" cleanup --older-than 30d
/tmp/codex-wake-p20-install/bin/codex-wake --wake-root "$ROOT/wake" cleanup --older-than 30d --delete
/tmp/codex-wake-p20-install/bin/codex-wake --wake-root "$ROOT/wake" list --archived
```

Outcome:

```text
archived wake_20260520_011548_afd1 /tmp/codex-wake-p20-installed/wake/archive/wake_20260520_011548_afd1.json
cleanup mode=dry-run older_than=30d archived=1 matched=0
would-delete wake_20260520_011548_afd1 ... retention_at=2026-04-01T00:00:00Z
cleanup mode=dry-run older_than=30d archived=0 matched=1
deleted wake_20260520_011548_afd1 ... retention_at=2026-04-01T00:00:00Z
cleanup mode=delete older_than=30d archived=0 matched=1
No wakes.
```

## Known Limits

- Cleanup does not prune ack files, logs, locks, or event files in this slice.
- Cleanup is operator-invoked only; the daemon does not perform automatic retention.
- Archived records without a parseable retention timestamp are skipped rather than deleted.

## Result

Pass. P20 is closed.
