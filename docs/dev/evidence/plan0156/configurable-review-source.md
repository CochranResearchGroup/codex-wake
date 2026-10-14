# Configurable review source checkpoint

2026-10-14, issue255, branch feat/agent-lifecycle; plan remains OPEN.

Public CLI and MCP resolve user defaults and objective overrides, expose actual
selected instruction bytes/hashes and reject unavailable selections without
substitution. Handoff binds the resolved configuration into its intent; changing
defaults cannot rewrite an existing assignment. Existing mandatory checkpoint
fields and runtime ownership/resource guards remain required.

Native transcript evidence must show selected instructions read. Completed
helper checks establish readiness separately from work acceptance. Accept requires
actual downstream review selection, named changes, host-approved criterion
progress, existing matching evidence hashes, no scope deviation or unsupported
claims, remaining work and the exact checkpoint next packet. Correct and blocked
do not prepare a goal. Native/provider behavior in tests is injected fixture
evidence; no installed acceptance claim is made.

Red/green commands:

- `PYTHONPATH=src python -m unittest discover -s tests -p 'test_lifecycle_configuration.py' -v`
  initially failed because configuration was absent; passed after CLI resolver.
- `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_lifecycle_configuration.py' -v`
  MCP initially returned unknown_tool; passes with host-bound adapter. Initial
  non-venv invocation lacked jsonschema; retained as environment failure.
- `PYTHONPATH=src:tests .venv/bin/python -m unittest test_agent_handoff_preflight.HandoffPreflightTests.test_ready_runtime_with_unsupported_completion_cannot_prepare_a_goal -v`
  initially prepared a successor goal despite correct verdict; now holds.
- Same runner, `test_non_github_review_accepts_evidence_without_changing_native_guards`:
  initially rejected local-review policy; now passes with configured selection.
- Same runner, `test_missing_writer_instruction_read_blocks_before_successor_admission`:
  initially admitted despite missing read; now blocks before thread creation.

Focused selection: lifecycle configuration, handoff guards/preflight, lifecycle
MCP and A2A MCP:52 tests passed in18.354s. Subsequent frozen-default regression
passed independently. Compileall, policy wiring and diff whitespace passed.
Final focused selection passed53 tests in20.577s after instruction-read and
frozen-default regressions. Logs: /tmp/plan0156-review-focused-final.log.

Remaining: issue256 durable budget enforcement, issue257 correction control and
installed both-mode acceptance, updated native harness, full integration/release
gates and cleanup. Legacy helper-only acceptance is deliberately insufficient.
