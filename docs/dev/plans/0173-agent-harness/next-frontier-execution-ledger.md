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
