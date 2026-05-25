# OpenClaw Gateway Target Implementation

Date: 2026-05-25

Plan: `docs/dev/plans/0040-2026-05-25-openclaw-gateway-wake-transport.md`

## Scope

Execute P40 Slice 2: add source-level `openclaw_gateway` target creation,
validation, and daemon dispatch support in `codex-wake`.

## Implementation

Added `src/codex_wake/openclaw_gateway.py` with:

- structured `openclaw_gateway` target construction and validation;
- required durable `agent:<agent_id>:...` session keys;
- rejection for placeholder values such as `noop-smoke-test`;
- optional OpenClaw CLI path persistence through `--openclaw-path`;
- Gateway RPC preflight through `openclaw gateway status --require-rpc --json`;
- Gateway `agent` dispatch through `openclaw gateway call --expect-final`;
- deterministic idempotency key `codex-wake:<wake-id>`;
- short `WAKE_TRIGGER_ID=...` handoff prompts that point back to the durable
  wake record instead of embedding the original prompt text;
- sanitized dispatch metadata that records run/session/model/provider summaries
  without storing raw assistant response text.

Wired the transport into:

- `codex-wake openclaw after`;
- `codex-wake openclaw at`;
- the generic daemon firing dispatcher;
- schema summary target transport reporting;
- wake record schema documentation;
- README and skill guidance.

## Validation

Focused tests:

```bash
PYTHONPATH=src python -m unittest tests.test_openclaw_gateway tests.test_cli tests.test_records tests.test_app_server tests.test_injector
```

Result: 74 tests passed.

Full suite:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
```

Result: 112 tests passed.

Compile check:

```bash
python -m compileall -q src tests .codex/hooks
```

Result: passed.

Whitespace check:

```bash
git diff --check
```

Result: passed.

CLI record-creation smoke:

```bash
tmp=$(mktemp -d)
PYTHONPATH=src python -m codex_wake.cli \
  --wake-root "$tmp/wake" \
  openclaw after \
  --agent main \
  --session-key agent:main:slack:channel:c0ahqqcg7j4 \
  --workspace default \
  --channel C0AHQQCG7J4 \
  --thread-ts 1779729958.218239 \
  1m -- 'P40 Slice 2 CLI smoke'
PYTHONPATH=src python -m codex_wake.cli --wake-root "$tmp/wake" status --json
```

Result:

- created `wake_20260525_203630_d921`;
- `active_total: 1`;
- `counts_by_target_transport.openclaw_gateway: 1`;
- `counts_by_status.pending: 1`.

## Acceptance Result

Slice 2 acceptance passes at the source/fake-Gateway level:

- CLI creates durable OpenClaw Gateway wake records without tmux.
- CLI rejects missing session key and placeholder session keys.
- Wake JSON stores structured target metadata without token/password values.
- Fake Gateway dispatch covers preflight, success, failure, max-attempt
  failure, and timeout requeue behavior.
- Dispatch result stores sanitized evidence, not raw assistant transcript text.

## Known Gaps

- This slice did not run a real delayed wake against a live OpenClaw session.
- This slice did not verify Slack-visible delivery.
- OpenClaw plugin registration from live session context remains Slice 4.

## Next Step

Run P40 Slice 3: create an `openclaw_gateway` wake against a real active
OpenClaw session, run without `--no-dispatch`, and verify the unique wake
response through Slack Mirror or OpenClaw transcript evidence.
