# Handoff resource continuity / #365

State: OPEN — bounded source and instruction repair, pending primary reconciliation
Owner: primary / ecochran76; delegated implementation: handoff_ritual_diagnosis
Branch: fix/handoff-automatic-allocation
Baseline: origin/main96f0f01104e6f0297d3c1ea4c7c2477051270787
Work item: https://github.com/CochranResearchGroup/codex-wake/issues/365

Authority: operator clarified that a new session reading a handoff continues already-authorized work without resource reset, repeated approval or enrollment ritual. Existing numeric ceilings and original deadlines are retained. Manual mode does not silently activate governance. A stale completed/blocked goal for unrelated work is not a global lock.

Scope: reproduce optional supervision's forced allocation selection; derive the existing allocation only from qualified native lineage plus the private retained source receipt/current host grant; preserve explicit allocation compatibility, current governor setting, spending, deadline and genuine stops. Correct agent instructions for ordinary operator-directed manual handoff reading. No live goal, watcher, service, provider, native daemon or original wake mutations.

Non-goals: infer native identity from arbitrary Markdown; fabricate response-level accounting; observe every file read; transfer arbitrary host privileges; reset or renew an objective; automatically enroll unsupervised sessions; repair native orphan-tool panic (#364, plan0177); infer why an original result went missing.

| Requirement | Acceptance and current boundary |
| --- | --- |
| Read a handoff and continue authorized manual work | Agent skill/lifecycle guidance explicitly removes set/reset/enrollment/reapproval as a prerequisite; no governor activation. No runtime file-read hook is claimed. |
| Optional supervised successor needs no allocation-ID ritual | Public MCP regression joins qualified source allocation with omitted ID; same original deadline and cumulative80/100tokens. |
| Completed/blocked source goal does not obstruct existing authorized continuation | Public regression covers source statuses active/complete/blocked without native goal mutations. |
| Accounting basis follows existing objective | Omitted accounting basis inherits source fresh/cache-inclusive basis; explicit changes still use the existing rejection guard. |
| Governor choice follows existing objective | Deactivated source allocation remains inactive on successor attachment. |
| Real exhaustion does not replenish on handoff | Public regression retains stop_latched with80/80spent. |
| Old unrelated objective does not lock a new session | Public regression retains old exhausted/blocked allocation and allows independent new allocation under host-approved self-enrollment envelope. |
| Do not fabricate lineage from ordinary handoff prose | Qualified native parent plus private source receipt/current host envelope are required for automatic supervised selection. Missing source binding holds that optional adapter only; manual authority is separate. |

Definition of done for this bounded slice: source/public-seam regressions pass; instruction and domain authorities agree; primary adjudicates limitations; integration/release remain separate. No source result is claimed installed.

## Diagnosis and red/green

Initial exact red: public CommandRunner.call(wake_goal_limits_set) with qualified successor, intact source allocation and20tokens remaining returns setup_unavailable / successor must select its existing objective allocation. Omitting only allocation_id causes failure; specifying it preserves original deadline/cumulative80tokens and succeeds. Private minimal loop /tmp/codex-wake-handoff-ritual/test_handoff_auto.py ran RED0.188s, explicit-ID control GREEN0.218s. Initial malformed child fixture returned descendant_session_identity_mismatch; corrected to native shared-session lineage and unique response ID before accepting the symptom red.

Ranked hypotheses: (1) default selection chooses a fresh native-thread allocation despite qualified existing lineage; explicit allocation makes it green. Confirmed. (2) manual Markdown read lacks durable native linkage; no runtime file-read hook exists, so instruction correction must not claim automatic metering. (3) stale inactive native goal alone is a universal gate; existing inactive-status tests pass, so this is not the demonstrated source bug. New independent-session regression protects separation from a prior exhausted objective.

Repository regression test_goal_supervision.GoalSupervisionTests.test_verified_successor_inherits_allocation_without_operator_selection RED0.298s before source patch, then GREEN with stale source statuses and inactive-governor case. Existing managed handoff tests for continuous-monitor activation and inherited deadline already passed2/1.974s, confirming the explicitly managed handoff path is separate from ordinary file reading.

The fix changes only the established first-enrollment successor refusal: after qualified usage identifies a source, read its private receipt, resolve current host grant and check runtime identity, then let the existing allocation admission enforce original caps/deadline/accounting/stop/deactivation. Explicit allocation selections and missing-source refusal stay compatible. No opportunistic enrollment is added to inspection or file reads. A second red slice caught cache-inclusive source allocations being rejected when a successor omitted the accounting argument. That omission now inherits the source basis rather than defaulting to fresh; no explicit basis change is authorized.

## Final selected validation

- `PYTHONPATH=src:tests <installed-dev1-python> -m unittest test_goal_supervision test_governor_deactivation test_enforcement_permissions test_goal_engagement`:54PASS16.963s initially; after accounting-basis follow-up54PASS13.623s with full output /tmp/codex-wake-handoff-ritual/selection-final.log. This is an affected selection, not the full suite.
- Candidate repository regression copied unchanged to /tmp/codex-wake-handoff-ritual/redtests/test_goal_supervision_candidate.py and run against baseline source: one test/four subcases RED0.588s, all with successor must select its existing objective allocation. Same test command/module against candidate source GREEN0.841s. Receipts /tmp/codex-wake-handoff-ritual/repository-{red,green}.log. Baseline terminal checkout source src/ was verified byte-equivalent through git diff to origin/main96f0f01 before patch.
- Additional exhaustion scenario initially asserted MCP error=false for a correctly held result; fixed the test expectation to error=true with stop_latched, not the implementation. That setup/assertion failure is not counted as a product regression or passing test.
- Second slice: same public regression, cache-inclusive source subcase RED0.682s with allocation accounting basis cannot change during self enrollment, then GREEN0.696s after inheriting omitted basis. Logs /tmp/codex-wake-handoff-ritual/basis-{red,green}.log.
- Pinned Ruff0.14.2 undefined-name selection on changed Python files PASS; `python3 scripts/check_policy_wiring.py` PASS; `git diff --check` PASS.
- No new native/provider acceptance, installation, live controller or goal mutation. Tests own isolated temporary roots and fixture watchers/native sockets, with normal unittest cleanup.

Primary review/integration, installed skill refresh and release validation remain pending. This plan does not claim the arbitrary Markdown/no-lineage case has an automatic metering protocol. Memory disposition: forbidden — task does not authorize persistent memory writes.
