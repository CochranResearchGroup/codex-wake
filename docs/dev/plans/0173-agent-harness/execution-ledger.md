# First frontier execution ledger

State: RUNNING
Owner: ecochran76 / primary
Goal: close #315, #316 and #317; then one broad two-axis code review and one
bounded TDD remediation pass. Maximum requested elapsed time: two hours, starting
2026-10-24T19:40:40Z. No live provider, installed-policy or deployment effects.

Integration: feat/harness-frontier
Checkout: /home/ecochran76/workspace.local/codex-wake-harness-frontier
Source base / review fixed point: f96f4c8244529e8b4e8e4206202d4a1e91084a52
Approved planning imported through 73600ca.

| Ticket | Blockers | State | Owner | Branch / worktree | Owned surface |
| --- | --- | --- | --- | --- | --- |
| #315 / HF-02 | HF-01 design complete | validated | /root/hf02 | feat/315-managed-inventory / codex-wake-hf02 | New inventory leaves, focused tests, feature docs |
| #316 / HF-07 | HF-01 design complete | validated | /root/hf07 | feat/316-task-briefs / codex-wake-hf07 | New task-brief leaves, focused tests, feature docs |
| #317 / HF-13 | HF-01 design complete | validated | /root | feat/harness-frontier / codex-wake-harness-frontier | Wake policy, record/dispatcher integration, shared CLI/MCP registration |

Each worker starts at 73600ca and commits only owned paths. Primary integrates
serially, preserves exact caller/grant/resource semantics, and owns shared hubs,
schemas, profiles and final acceptance. Worker evidence does not prove integration.
#310 remains separately owned; do not duplicate or silently broaden its contract.

## Acceptance and validation

Frozen sources: hf-02-spec.md, hf-07-spec.md, hf-13-spec.md and GitHub #315–317.
Public CLI/MCP inventory, assignment admission and wake registration/dispatch
are the approved test seams. Use disposable roots and injected native clocks,
runtime bindings and host authority. No provider calls or real terminal changes.

Record red/green commands, worker commits, integrated commits and requirement
evidence below. A skipped gate remains incomplete. After integrated validation,
close tickets with source evidence, then run exactly one Standards/Spec review
against the recorded fixed point and one bounded TDD pass for accepted findings.

## Evidence log

- Initial origin/main fetched as f96f4c8; original main checkout 43e3db2 preserved.
- HF-02 and HF-07 dispatched to separate worktrees; HF-13 retained by primary.

## Implementation checkpoint

Progress classification: progress. Worker leaves and lifecycle carrying are integrated.

- #315 worker deef6c68547239aed9e85f9fda1e51ed0504ecb9 integrated d57e3de;
  12 inventory tests and public main-CLI/MCP identity/suppression proof pass.
- #316 worker83ca4a2 integrated471508a; worker57a27b8 integratedfa3c441;
  13 brief/store/caller/lifecycle tests pass. Main CLI/MCP caller tests verify
  approval boundaries and admitted revision surviving later approval/restart.
- #317 primary added frozen schema8 policy over base6/7, explicit owner completion,
  startup admission, compatible-reader receipts and old-record preservation.
  Five focused wake-policy tests and18 native-intent recovery tests pass.
- Public caller suite:5 pass. CLI suite:66 pass. Native delivery:15 pass.
  Managed Grok scheduling/runtime:10 pass. Undefined-name checker and policy
  wiring pass. Full suite is running in isolated declared-dependency environment.
- First red: `PYTHONPATH=src python -m unittest discover -s tests -p
  test_wake_policy.py -v` failed6!=8. Green with new policy registration.
  Integrity mutation case failed before binding policy to original intent hash,
  then passed. Worker red/green receipts returned in their completion messages.
- Initial default interpreter lacked MCP/jsonschema; stopped that exact run and
  provisioned local .venv with `uv pip install --python .venv/bin/python -e
  '.[mcp,dev]'`. This is an isolated test environment, not production installation.
- Existing handoff fixture inspected ambient XDG roots: untouched baseline and
  candidate failed the same10 tests. Exact10 pass under isolated XDG state.
  Worker owns narrow fixture isolation/full-pin preflight proof follow-up.

Remaining gates: integrate fixture follow-up, freeze source, complete comprehensive
validation, reconcile every ticket criterion, then close tickets before the one
requested broad Standards/Spec review and bounded TDD remediation pass.

## Frozen validation checkpoint: 71d35b9

Progress classification: progress. Feature implementation is frozen for the
Python3.11 and3.12 comprehensive runs (sessions34829 and99902 respectively).

- Worker8849e9a integrated639a7c6: per-test XDG isolation and full native/PTY
  preflight fixture. Original pin/revision1 reaches the successor after revision2
  is approved; original admission remains single. No production guard change.
- Compatibility update71d35b9 retains authentic historical schema5/6 writer
  fixtures for legacy reader/migration tests, while the real new-registration
  public CLI asserts schema8. Monitor/CLI schema expectations include8.
- Seven policy tests pass: frozen defaults/idempotency, explicit conflict,
  malformed/changed intent, all owner-end actions, lost-response no-replay,
  startup admission and missing owner-journal fencing. Twelve inventory, thirteen
  task-brief and five integrated public caller tests pass. Legacy network10,
  migration5 and monitor10 focused tests pass.
- Presubmit compile, F821/F822/F823, policy wiring and whitespace checks pass.
- Initial comprehensive diagnostic run on an evolving tree found compatibility
  fixture expectations and ambient-XDG leakage; it is not final-tip acceptance.
  Both were repaired without weakening the existing behavior assertions.
- The one opt-in disposable systemd containment test is unrelated to these
  features and remains outside this provider-free source acceptance envelope.

Acceptance mapping pending comprehensive completion:

| Ticket criterion | Public evidence |
| --- | --- |
| #315 deliberate exact enrollment | managed inventory command/runtime observer tests, integrated native MCP enrollment |
| #315 persistent identity and stale binding | concurrent/restart/successor/reconcile tests; CLI/MCP share ID and suppression |
| #315 Codex/Grok capability-aware inventory | native observer tests and authenticated host-bound Grok caller tests; grants_operations false |
| #316 pinned approved revision | task-brief admission/restart tests and main CLI/MCP revision1 after approval2 |
| #316 scope proposal is not approval | native worker denial, private exact controller delegation and CLI operator capability proof |
| #316 bounded context and obligations | required context changed/missing/symlink/oversize tests; actual spawn/handoff/preflight pin propagation |
| #317 existing durable behavior / explicit policy | schema5/6/7 compatibility and new schema8 policy/default/owner-action tests |
| #317 origin/expiry/uncertainty continuity | native-intent18 tests, owner retirement no resend, restart/configuration freeze tests |
| #317 isolated epoch/monitor evidence | counter discontinuity/time uncertainty tests, schema8 monitor refusal/advertisement; no live reboot claim |

## Comprehensive matrix: first frozen-source result

Both Python3.11 and3.12 executed1495 tests on the same frozen runtime source.
Each reported three failing subcases in one existing acceptance-evidence fixture,
with the same `successor_assignment_awaiting_preflight` instead of the expected
review-rejection reason. New feature tests passed. This is not a clean matrix.
Worker /root/hf07 is checking per-scenario XDG isolation because multiple
subcases run inside one test; the first subcase passes and leaves registration
state for the others. No production guard or expected assertion is being relaxed.

Isolated installed-wheel smoke passed: version0.21.0 from site-packages,45 MCP
tools advertised, new inventory read served and metadata-free wake registration
denied with zero new wake records. Wheel SHA256:
3a7c5dd83674400caea2418875c309483dfa55c90b928885d5ff9f104eb15736.
This is a disposable prefix, not a production install or release.

## Source acceptance and tracker closure gate

Progress classification: progress. All three ticket acceptance mappings above
are now validated on the integration branch. Serial Python3.12:1495 tests pass,
with one unrelated opt-in systemd test skipped. CI run40129096911 independently
passed the unit suites on Python3.11 and3.12; it failed later because the installed
MCP smoke asserted exactly32 tools. The smoke now checks required names, and
passes against the isolated0.21.0 wheel with45 tools, zero native turns and no
notifications. Local serial3.11 remains running as additional verification.

No runtime source changed after71d35b9. Diagnostic-only preflight assertion
change0d57048 does not alter behavior. The observed parallel-full-suite fixture
failures did not reproduce in valid serial178-prefix, full62-handoff module,
serial full3.12 or independently hosted CI unit suites. No production guard or
acceptance expectation was weakened.

PR326 is draft. Ticket source closure precedes the single requested broad review;
closure does not claim main integration, release or production deployment.
Review fixed point remains f96f4c8244529e8b4e8e4206202d4a1e91084a52.
