# HF-21 worker evidence

Work item #339; branch feat/339-attention-queue; base
457030622d59d2ec47f5190b2025fbb7ea50ca79. Product authority:
d9b59f368e984dff925597304f90e901; staged response clarification from coordinator.
Owned worktree /home/ecochran76/workspace.local/codex-wake-attention-queue.

## Source qualification

Read current AGENTS, policy selection/planning/runtime/architecture/validation,
engineering/testing and closeout policies; HF21 ticket, HF06 spec and common
permissions contract, HF03/HF04 specs and GLOSSARY. CodeGraph discovery in the
source worktree established PermissionStore, common CLI principal verification,
resource custody and private durable-state patterns. Implementation adds no
shared command registry, action catalog, glossary, scheduler or context registry.

## Observed red/green evidence

Commands run with `PYTHONPATH=src` and deterministic temporary filesystem fixtures:

1. `pytest -q tests/test_attention_queue.py`: red collection failed with
   `ModuleNotFoundError: codex_wake.attention_queue`; implementation then green:
   8 passed. An earlier invocation without PYTHONPATH failed on the package import
   and was corrected before the meaningful missing-module red.
2. `pytest -q tests/test_attention_queue_commands.py`: red collection failed with
   missing attention_commands; adapter implementation then combined green:
   11 passed.
3. Updated staged request/response behavior tests: combined red 7 failed,
   8 passed; callback-optional record stage and MCP restriction then green:
   15 passed.
4. Permission-reuse/raw-corruption/real-capability coverage: combined red
   2 failed, 16 passed. Corrected the fixture's verified task scope and exact-self
   target mismatch; strict response validation fixed malformed choice admission.
   Combined green: 18 passed. Final affected command below repeated after CLI task
   verifier and documentation completion; 18 passed in 2.55s.

Final focused validation:
`PYTHONPATH=src pytest -q tests/test_attention_queue.py tests/test_attention_queue_commands.py`

Coverage includes actual BusStore-issued operator capability on CLI request and
respond without a feature validator; durable reconstruction, single consumption,
request dedup/conflict, owner scope, operator-only response, expiry, staged
response with changed account/attempt/policy/unknown submission at consumption,
existing matching PermissionStore approval and later policy fence, notice-only
acknowledgment, raw corrupt/unknown-state retention and MCP role/mutation refusal.

## Integration seam and limits

`attention_commands.register_parser`, `run`, `execute`; `AttentionQueue` public
store methods request/inspect/respond/consume/close. Parent wires shared CLI/MCP.
MCP exposes only request/list/show. Principal subjects are verified conversation
IDs; native adapter verifies metadata. Feature-owner trusted context callback is
mandatory at consume and optional at request/respond. Its output must come from
the owner's actual journal; there is deliberately no self-assertion fallback.
Permission decisions reference existing approvals only. Consume never executes,
replays, resumes or creates a grant. Owners retain immediate pre-I/O permission
and operation/custody checks and crash/uncertainty reconciliation responsibility.

No installed, provider, production, dashboard, GitHub or memory effects. Shared
registry integration and final combined review remain coordinator-owned. No
worker review performed; global final review/remediation allowance preserved.
Memory disposition: forbidden because the worker assignment prohibits writes.

## Validation harness correction

The initial pytest receipts above remain historical evidence only. Coordinator
identified the repository's authoritative runner as unittest discovery, with no
pytest dependency. Converted owned tests to unittest.TestCase and standard-library
TemporaryDirectory, subTest, redirect_stdout and StringIO. Parameter cases remain
covered as subtests. Removed owned principal-verifier mocks: adapter coverage now
calls public execute with host Principal, and CLI coverage retains the real
BusStore-issued operator capability for request, response and inspection without
a feature validator. No dependency or shared-runner changes.

Observed current validation:

- `PYTHONPATH=src python3.11 -m unittest discover -s tests -p 'test_attention_queue*.py'`
  — 10 test methods, parameter subtests included, OK (2.332s).
- `PYTHONPATH=src python3.12 -m unittest discover -s tests -p 'test_attention_queue*.py'`
  — 10 test methods, parameter subtests included, OK (1.643s).

This corrects implementation validation only; no broad review or findings-remediation
pass was performed or consumed.
