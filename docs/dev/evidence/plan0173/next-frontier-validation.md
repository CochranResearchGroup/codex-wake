# Next frontier source acceptance

Latest corrective result: source16c2501 passes the final full local3.12 suite,
1651tests/823.097s, OK(skipped1), exit0 under900scap. Issue342's three failure
patterns are repaired. Earlier failures/provisional dispositions below are retained
history and are superseded by the final corrective evidence at the end.

Source:7bb337ef5bc248e06f059b62ff043ecc9e6807a2, branchfeat/harness-next-frontier,
draftPR341. Seven source tickets334–340 closed;335 reopened for review defects
and reclosed after repair. Main integration/release/production install separate.
CI intentionally skipped. Original operator checkout remains clean43e3db2.

## Selected validation

Qualified Python3.12 and3.11 environments live in the existing harness-frontier
checkout; dependencies match pyproject.toml `[mcp,dev]`. All commands use
`PYTHONPATH=src:tests python -m unittest ...`.

- Before review:79 feature/compatibility tests pass3.12/24.020s and3.11/25.526s.
- Final3.12 selection:85 pass28.287s: test_work_acceptance,
  test_attention_queue, test_attention_queue_commands, test_background_jobs,
  test_operator_overview, test_agent_resume, test_agent_resume_protocol,
  test_tab_organization, test_guarded_interactions, test_grok_runtime,
  test_runtime_a2a, test_frontier_attention_callers, test_frontier_job_await.
- Final3.11 changed selection:22 pass10.492s: test_work_acceptance,
  test_frontier_attention_callers, test_frontier_job_await, test_tab_organization.
- Final3.12 prerequisite selection:64 pass24.923s: test_agent_observation,
  test_resource_claims, test_resource_claim_commands, test_harness_callers,
  test_harness_resource_callers, test_task_briefs, test_task_brief_commands,
  test_task_brief_lifecycle, test_session_permissions, test_permission_convergence,
  test_permission_migration.
- Final-source wheel built with `uv build --wheel`, installed into a disposable
  isolated environment. SHA2561fff8cf6d206c00c67fcd9a0fa846ea7c0a3dff7342045622169feb6f0be97a9.
  Seven installed CLI help paths work; actual stdio MCP lists75tools including
  all seven feature families, and refuses unattested menu inspection. Run outside
  repository with PYTHONPATH removed and private XDG state/cache/config.
- Ruff passes changed acceptance/shared caller files and new caller tests;
  gitdiffcheck passes. Actual installed Grok menu proof is recorded separately
  in hf05-menu-acceptance.md; actual tmux focus/ordering and native resume protocol
  evidence live with their feature specs. Provider turns0 in owned qualification.

## Comprehensive result and limits

A single comprehensive3.12 run started before final remediation:
`python -m unittest discover -s tests`,1647tests/529.094s,
FAILED2failures/4errors/1skip. This is **not a clean full-suite result**.

- Two existing handoff preflight scenarios held at awaiting_preflight instead of
  awaiting_activation (exact_idle_owned_client_not_ready). Both pass isolated on
  the fixed-point baselineff59117 and finalsource. Retain as timing/qualification
  failures under comprehensive execution; successful diagnostic repeats do not
  erase the first failures. No handoff source change is in the selected diff.
- Offline time inspection lacks the expected sources field. Reproduced unchanged
  on baselineff59117 and finalsource; outside this feature scope. Baseline3-test
  diagnostic has1error; final4-test diagnostic has1error from this samecase.
- Three subcases in the new acceptance verifier test refused owner_unqualified
  at the30-second resource observation fence. The same public behavior passes
  final focused and isolated diagnostic runs. Production refused effect safely;
  exact clock/freshness cause in comprehensive execution remains unproven. An
  earlier3.11 remediation selection also saw a freshness refusal; all first logs
  are retained. The new multi-effect regression refreshes observation before
  each evaluation. No production fence is weakened and no clean comprehensive
  claim or blanket unrelated-failure claim is made.

Local full logs/diagnostics retained in user state
`~/.local/state/codex-wake/next-frontier-final-validation/`.
The outstanding comprehensive reliability issues remain an integration limitation
of draftPR341; source acceptance uses the specified feature/compatibility seams.
No second full suite or broad review was run merely to seek a clean result.

## Reconciliation and custody

Review1/1: independentStandards/Spec with primaryadjudication recorded in
next-frontier-review.md. Two blockingHF08 defects repaired in one boundedTDD pass;
one nonblocking persistence duplication heuristic retained as backlog.
Six worker checkouts removed only after cleanstatus and verified durablebundle;
branches retained. Bundle and exactsource/pathreceipt live in
`~/.local/state/codex-wake/next-frontier-worker-custody/`.
Other worktrees/services untouched. Baseline diagnostic checkout is disposable.
Memory dispositionforbidden: explicit developer boundary requires a memory-update
request; receipt next-frontier-final-memory.json, no Graphiti write attempted.

## Corrective local validation, issue342

At17c1d4c the single corrective comprehensive3.12 run passes1651tests/636.042s,
OK(skipped1), exit0. It includes the two acceptance review regressions plus one
clock discontinuity regression and one additional offline-mode regression absent
from the original1647-test collection. Focused34tests pass3.11/3.12; final isolated
wheel's10 acceptance tests pass outside repository.

The acceptance errors were traced to an actual backward wall-clock step of0.7587s;
production correctly refused future observation. Existing configured clock now
propagates into resource checks and tests use a consistent injected clock. Offline
inspection explicitly selects its intended configuration instead of ambient host
settings. Detailed red/green records are in acceptance-freshness-repair.md and
time-inspection-repair.md.

The earlier handoff failures remain unproven as to cause; current full pass does
not erase them. Issue342 staysopen for that component, with fixture-only exact
readiness diagnostics retained. DraftPR341 still requires prerequisite integration
and an explicit disposition of known intermittent handoff behavior before claiming
merge readiness. No main/provider/service change or CI run occurred.

Handoff follow-up after the passing17c1d4c join captured a fresh original failure:
exact natural tmux observation timeout, identity scans1.421–1.738s beyond the
fixture's1s budget. The test fixture now controls the external observation clock,
retains real process evidence, and explicitly exercises safe timeout/deferral and
same-intent reconciliation. Intermediate51-case run retained6failures; final
clock-isolated51cases pass205.689s. See handoff-preflight-repair.md. This supersedes
the previously unresolved handoff disposition; a final joined run follows the
concrete fixture repair rather than retrying unchanged code until green.

Final corrective join at16c2501:1651tests/823.097s, OK(skipped1), exit0.
All three repairs qualified; source issue342 closed. Handoff module51/205.689s
and affected3cases3.11/19.958s pass. Original process/start-time and admission
guards remain real; production still safely defers an incomplete observation.
Previous open handoff disposition is superseded by natural timeout evidence and
controlled regression in handoff-preflight-repair.md. CI remains skipped.
