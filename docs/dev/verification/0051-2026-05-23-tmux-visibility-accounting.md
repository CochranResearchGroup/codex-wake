# Tmux Visibility Accounting Verification

Date: 2026-05-23

Plan: [Tmux Visibility Accounting](../plans/0036-2026-05-23-tmux-visibility-accounting.md)

## Change

Tmux dispatch now writes sanitized `visibility_result` evidence after a hook ack
is observed. The field classifies:

- `visible_prompt_observed`
- `ack_observed_visibility_unproven`
- `visibility_check_failed`

The visibility check compares whether `WAKE_TRIGGER_ID=<wake-id>` newly appears
in a post-ack tmux capture. It records only line counts, marker booleans,
classification, pane id, and timestamp. Raw pane text is not stored.

`codex-wake status --json` now includes
`counts_by_visibility_classification`.

## Validation

Focused checks:

```text
PYTHONPATH=src python -m unittest tests.test_injector tests.test_records tests.test_cli
Ran 51 tests in 0.461s
OK

python -m compileall -q src tests
```

Full local gate:

```text
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
Ran 93 tests in 0.884s
OK

python -m compileall -q src tests
git diff --check
```

Installed runtime refresh:

```text
uv tool install --force --reinstall --no-cache .
codex-wake schema --json
codex-wake --wake-root .codex/wake status --json
```

Installed `codex-wake schema --json` reports `visibility_result` in
`optional_fields`. Installed `status --json` reports
`counts_by_visibility_classification`.

Installed skill sync:

```text
diff -qr skills/codex-wake /home/ecochran76/.codex/shared/skills/codex-wake
diff -qr skills/codex-wake /home/ecochran76/.agents/skills/codex-wake
```

## Expected Operator Semantics

`ack_observed` remains proof that the wake prompt was submitted through the
target session's hook path. For tmux records, `visibility_result` is now the
first-place evidence for whether the operator-visible pane showed the wake
marker.

Agents should report `ack_observed_visibility_unproven` plainly instead of
calling it an operator-visible new turn.
