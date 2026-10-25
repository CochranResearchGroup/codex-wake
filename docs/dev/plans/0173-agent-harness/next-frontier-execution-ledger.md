# Renewed harness frontier execution

State: OPEN
Owner: ecochran76 / primary coordinator
Branch: feat/harness-next-frontier
Canonical main readback: 37a5cbb
Validated observation/ownership input: 3dde546
Qualified HF06 input: 5d34fc73089e3e45013a6428a789f190a2428a9f
Integration checkpoint: 3af0cb618b273b10b60c65e5f5021faf5d7c11d6
Goal allocation: renewed by user; 2 hours / 2,000,000 tokens, manually enforced
Counter: get_goal new allocation starts at zero; do not reset live/native campaigns
Implementation stop: 100 minutes elapsed; reserve 20 minutes for review, verification and recoverable closeout
Broad review: 0/1 used; final bounded TDD remediation: 0/1 used
CI: skipped by operator

## Current State

Previous goal completed HF03/HF04 source acceptance. This new goal reuses their
validated source and the separately implemented HF06 prerequisite; it does not
reimplement them or claim they merged on main. Prior goal review/repair receipts
remain historical and do not count as this renewed allocation's single review.

HF06 delta is computed from f29042b to5d34fc7 after verifying f29042b's tree equals
main37a5cbb exactly. Applying that qualified delta avoids duplicate pre-squash
history. Only CLI dispatch and MCP group dispatch conflicted; both intents were
preserved. Permission evaluator12, public harness7 and permission convergence3
pass. Known workspace-revision fix from PR329 is being carried and revalidated
so acceptance/check consumers do not inherit the reviewed workspace bypass.

An accidental uncommitted merge in the original operator checkout was aborted
normally before this work. Original main remains clean at43e3db2. All subsequent
mutations are in the isolated next-frontier worktree. No production/native policy
or service was changed.

## Frontier and custody

All selected nodes consume validated HF02/03/04/06/07/13 prerequisites; no missing
blocker IDs or cycle exists. Only the current seven-node frontier is selected;
dependents unlocked by these nodes are not silently added to this packet.

| ID | Requirement | Owner | State |
| --- | --- | --- | --- |
| HF08 | independent acceptance checks | primary | product decisions pending; existing seams investigated |
| HF05 | guarded menu interaction / takeover | /root/hf05 | source discovery complete; isolated menu qualification in progress |
| HF14 | durable bounded background job / await | /root/hf14 | design discovered; product choices pending |
| HF16 | tab preview/apply/conditional undo | /root/hf16 | design discovered; product choices pending |
| HF18 | exact managed-agent resume | /root/hf18 | design discovered; product choices pending |
| HF21 | durable human attention queue | separate worker to be assigned when slot available | pending |
| HF27 | operator dashboard / known attachment | /root/hf27 | design discovered; UI/navigation choice pending |

At most three implementation lanes run at once (primary + two workers); additional
independent tickets queue without shared writes. Each worker keeps one ticket and
its own branch/worktree once coding is authorized. Primary owns shared CLI/MCP,
common action registry, glossary and serial reconciliation. No nested workers.
All product decisions freeze in feature specs before coding. Supporting discovery
must change a named implementation decision; two no-progress checkpoints trigger
simplification rather than governance/test-fixture churn.

## Decision questionnaire

Previews form4c4576f4308b, revision6a969d0c6b36f0193fe0bd9d5644895d798c022efc2a6e60d719fcdbb1965f4b.
Sessionbb6affa86f99. Public view:
https://previews.ecochran.dyndns.org/a/4c4576f4308b

No final responses at initial readback. Recommendations are not approvals.
The form freezes first guarded interaction, acceptance types, job scope, tab-order
priority, resume/authority behavior, attention decisions and dashboard interface/
navigation. Material choices remain pending; prerequisite reconciliation and safe
read-only capability discovery continue independently. Feature coding does not
proceed on elapsed time alone.

## Acceptance and closeout bounds

Each feature is a complete caller path with actual effect/refusal evidence, not
helper-only scaffolding. Tests use approved existing seams, disposable state and
provider-free protocols; any supported real-TUI claim needs installed-version
qualification. No arbitrary provider/production input, credential copying, live
operator tab mutation, installs or main merges are implied. Private test runtimes
must block external provider traffic and clean up only their owned processes.

Source closure requires each ticket's frozen criteria proven on the integration
branch. Then run one independent Standards/Spec review, adjudicate all candidates
and run one bounded TDD pass on accepted blockers. Preserve unresolved branches,
first failures, uncertainty and exact remaining gates. No repeated broad reviews.

## Prerequisite checkpoint — blocker_reduction

Known workspace fix carried at a5ca8ef. Combined prerequisite selection passes64
onPython3.12 (28.273s) andPython3.11; exact command:
PYTHONPATH=src:tests python -m unittest test_agent_observation test_resource_claims test_resource_claim_commands test_harness_callers test_harness_resource_callers test_task_briefs test_task_brief_commands test_task_brief_lifecycle test_session_permissions test_permission_convergence test_permission_migration.
Undefined-name anddiffchecks pass. The current integration base now validates
HF02/03/04/06/07/13 together; current frontier is HF05/08/14/16/18/21/27. Existing
permission source, semantic observation, durable custody and exact revision scope
are preserved. This is prerequisite integration, not closure of any new feature.

All seven ticket discovery packets assigned separately: HF08primary; HF05hf05,
HF14hf14, HF16hf16, HF18hf18, HF21hf21, HF27hf27. Their bounded read-only findings
are retained in the session and will become feature specs after product answers.
No worker implementation lane has begun; no broad review or finalTDD consumed.

HF05 installed capability evidence advanced: actual Grok1.0.40 command palette
Ctrl+P thenEscape, disposable private tmux/config/cwd with external networking
blocked in a distinct network namespace; no provider prompt/Enter/paste in the
first probe, byte-identical composer restored and owned cleanup census empty.
A bounded follow-up uses the existing local /session-info control and explicit
4.7/high configuration to prove the unchanged host identity grammar. Do not
claim a model footer or control geometry alone as exact runtime identity.

Product questionnaire remains unanswered at latest readback. Seven feature
specifications are not frozen; no implementation is authorized from silence.
Next dependent action is literal reconciliation of submitted form answers.

## Pending-decision checkpoint — blocker_reduction

Combined prerequisite64-test matrix is green on3.12(28.273s) and3.11(27.437s),
published branch12f748a with matchingremote readback and cleancheckout. Original
operator checkout remains clean43e3db2. No newfeatureticket has been closed.

HF05 follow-up terminal experiment is terminal and cleaned, not still running.
Receipt /tmp/hf05-bound-palette-7bw_osy4/receipt.json: one existing localidentity
command returned exactsessionUUID/cwd/Turn0, but the isolated fake-key profile
emitted1.0.40 without[stable] and stayedmodel4.6; model4.7 IDs were unavailable.
Unchanged production identity/readiness adapters refused. No palette input followed
that refusal, no grammar was relaxed and no provider prompt was sent. First
control-only paletteproof remains a fact; it is not qualified managedmenu acceptance.
Future HF05 implementation must qualify an explicit actual-version menu profile
without widening provider submission support or laundering thisgap through fixtures.

Questionnaire4c4576f4308b has no finalresponses on latest readback. All independent
safe prerequisite integration and bounded discovery for seven tickets is complete.
Feature coding waits for literal product answers (especially UI mode/navigation,
ordering precedence, acceptance andjobclasses); silence is not approval. Goal
remainsactive, review0/1 andfinalTDD0/1 unused. This turn advanced authoritative
source and validation; it is progress, not a repeated no-progress/blocked turn.

## Operator decisions resolved — outcome_progress

Form4c4576f4308b response d9b59f368e984dff925597304f90e901,
revision6a969d0c6b36f0193fe0bd9d5644895d798c022efc2a6e60d719fcdbb1965f4b,
submitted2026-10-25T02:48:49Z, iscomplete. All eight primary choices are
recommended; Other fields are inactive/unanswered, not inferred decisions.
Resolved: one version-qualified menu flow with explicit takeover/return; exact
artifact checks and bounded deterministic verifiers with explicit human/reviewer
judgments; approved bounded local process-group jobs; configurable activity-first
repo ordering with protected exceptions; exact saved resume with verified access
and no silent fallback/renewal; one durable human queue with no implicit grant;
terminal-first overview and explicit existing-only attachment focus.

Ready implementation wave1: primaryHF08; independentHF14 andHF21 workers.
HF05/HF16/HF18/HF27 remain assigned and queue for slots. Each feature freezes its
spec before its first red test. Shared new action names join HF06 ACTIONS; old
policies retain their known_actions and therefore do not silently gain new
mutation rights. No global/operator policy is changed by source registration.
Private test fixtures configure their policies explicitly. Source-only actions:
acceptance.verify, job.launch/cancel, attention.request/respond/consume,
workspace.order/undo/navigate, terminal.menu/takeover/return. Inspect reuses
session.inspect and resume consumes existing resume.self. Primary owns registry.

## Seven-feature integration — outcome_progress

All seven owned lanes delivered and were reconciled into feat/harness-next-frontier.
HF05 includes final-source installed Grok1.0.40 isolated menu qualification,
binding-generation custody and real legacy host input refusal; zero provider turns.
HF08 exact artifacts, genuine claimed verifier processes and explicit decisions
are independent of worker prose. HF14 uses owned bounded supervisors and the
existing exact-owner native file wake; real MCP registration, firing once and
authoritative task retirement are covered. HF16 preserves focused/manual/mixed
windows with conditional apply/undo. HF18 retains exact conversation/profile and
refuses uncertain/new-history recovery. HF21 has real CLI/MCP callers; a real-clock
response/history timestamp regression found during integration was fixed. HF27
qualifies repository identity and an actually attached tmux client before focus.

Shared CLI and native MCP adapters now expose all seven features. Model tools
cannot acquire operator menu input, takeover, tab mutation, attention response,
or dashboard focus. Host scope, lifecycle profiles, authority and runtime
observations remain independently verified. Resume.recover is explicit alongside
resume.self; no old policy gains an action implicitly.

Focused matrix:79 tests pass Python3.12(24.020s) and3.11(25.526s), including real
private tmux/native protocol compatibility. Additional actual top-level attention
callers(2) and exact-owner job-await callers(2) pass. One earlier test invocation
named nonexistent test_agent_resume_commands; corrected to actual protocol module,
with no product failure concealed. Full suite and installed artifact checks follow.
The review fixed point is ff5911775eb54965454e664556fc96d53c5d3584, the validated
prerequisite checkpoint proposed to the operator. Review0/1; final remediation0/1.
CI skipped by explicit instruction. Main merge, release and production installs
remain separate from these source-acceptance tickets.

Source checkpoint66dc1d9 published and remote verified. HF16 offline journal
inspection also passes without a runtime selector/server; red KeyError reproduced
and removed. Isolated wheel at33d43c8 passes seven installed CLI paths and actual
stdio MCP discovery(75tools), including all seven families and refusal of
unattested menu inspection. Final-source artifact will be rebuilt after remediation.
Seven source-acceptance issues334–340 now meet their frozen source criteria and
are being closed with this evidence. One broad review follows; issues will be
reopened for any blocking source defect until repaired. Full3.12 suite is running;
its result is not yet claimed. No main merge or production install occurred.

## Final source closeout — outcome_progress

Seven source tickets334–340 closed and tracker read back;335 reopened after the
single review and reclosed following both accepted defect repairs at7bb337e.
Review1/1; finalTDD1/1. Independent standards found one nonblocking duplication
heuristic; spec found twoHF08 defects. Primary adjudication, red/green receipts
and deferred heuristic are in next-frontier-review.md. No second broadreview.

Final validation:85 featuretests3.12 pass;22 changedtests3.11 pass;64 prerequisite
tests pass; final isolated wheel75 MCPtools andsevenCLIpaths pass. The one full
1647-test run was NOTclean(2failures/4errors/1skip); exact baseline comparison,
freshness qualification limits and firstfailures retained in
../../evidence/plan0173/next-frontier-validation.md. DraftPR341 preserves those
integration limitations; no mainmerge/release/install is claimed. Six ownedworker
checkouts cleanly retired after durablebundle, otherlanes untouched. Memory
forbidden receipt retained outsideGit; no memorywrite authorized.
