# HF-03 / HF-04 parallel implementation frontier

State: CLOSED
Owner: ecochran76 / primary coordinator
Branch: feat/harness-observation-ownership
Base: 37a5cbb03e1c9e7db5026c99d6dca3cbf443ee5f
Target: validated integration branch; origin/main integration separate
Work items: #330 (HF-03), #331 (HF-04)
Budget: 2 hours / 2,000,000 tokens cumulative; implementation stop at 100 minutes, reserve 20 minutes for validation/review/closeout
Review bound: exactly one broad review; at most one bounded TDD remediation; discovery passes 0 used
CI: explicitly skipped by operator

## Current State

Both blockers are HF-02, validated on base in merged PR326. Two nodes, known
blocker IDs, no cycles. Prior HF06/PR327 and workspace correction PR329 are
independent pending integration and are not reset, merged or duplicated here.
HF03 primary owns shared CLI/MCP/glossary integration. HF04 worker /root/hf04 owns
separate claims modules/tests/docs in its isolated worktree. Defaults questionnaire
was offered; conservative existing-invariant defaults proceed as routine choices
under explicit implementation authority and remain steerable.

## Packet custody

| Ticket | Owner | State | Branch / worktree | Scope |
| --- | --- | --- | --- | --- |
| HF03 #330 | primary | running | feat/harness-observation-ownership / codex-wake-observation-ownership | observation module, CLI/MCP, focused tests, shared docs |
| HF04 #331 | /root/hf04 | running | feat/331-resource-ownership / codex-wake-resource-ownership | claims owner/adapter, focused tests, claims docs/spec |

No nested workers. Independent implementation parallel; cherry-picks and shared
contract integration serial under primary. Worker evidence must include base,
result SHA, changed paths, exact red/green commands, acceptance limits and process
status. Primary verifies before marking integrated/validated or closing tracker.

## Validation and exit

Focused public seam tests first, real CLI and MCP entrypoint smoke in isolated
roots, affected compatibility tests, undefined-name/compile/diff/policy checks.
No CI gating, provider calls, deployment, installation or real operator tab input.
First acceptance evidence deadline: 20 minutes. Checkpoint at each implementation
slice or material state change; maximum two no-progress/hardening checkpoints
before simplifying tactics. Each loop has one primary controller and exits on
acceptance or bounded evidence failure.

After both tickets validated, close tracker with source evidence, freeze review
base/tip and run exactly one independent Standards/Spec review. Primary adjudicates
blocking/backlog/rejected/needs_evidence; one TDD repair pass, focused revalidation.
No repeated broad reviews. Local completion means validated branch and accurate
tracker outcomes, not publication/deployment. Preserve unresolved custody.

## Implementation checkpoint — outcome_progress

HF03 implementation and shared CLI/MCP wiring are green. Native protocol tests
use actual read-only SharedAppServerReader with external Unix-connection fixtures;
Grok uses existing runtime/terminal-host fixtures. Ten observation tests pass on
Python3.11/3.12;13 resource tests and7 public harness tests pass on both. Inventory
compatibility12 and Grok runtime10 pass on3.12. Worker commits70c3ee7,b61afe6,fcc2030
integrated asd5b4af3,6d442ba,da990e9. No scope conflicts. Fresh verified evidence
requalifies a stale cached inventory while suppression and changed process deny.

Build first attempt through `python -m pip wheel` failed because the reused
venv lacks pip; `uv build --wheel` succeeded. Isolated wheel installed under
/tmp/hf0304-installed using declared[mcp] dependencies. Its131 Python source
modules match the integration source. Actual installed CLI and52-tool stdio MCP
observe ready and wait matched against an owned local Unix protocol fixture;
unattested stdio resource claim is denied. Native methods were only initialize,
initialized andthread/read. No provider turn, agent-runtime launch or production change.
Receipt: user-scoped HF0304 validation directory (raw development logs outsideGit).

An initial invalid-config test used real sleep and was interrupted on its301s
input; corrected to a fake monotonic clock before recording its bounded red and
green outcomes. This was harness correction, not policy relaxation. Exactlyone
broadreview remains unused; finalTDD remediation remains unused. Recorded starting
base37a5cbb offered as the review fixed point; it is the narrow goal startingbase.

## Review checkpoint — blocker_reduction

Source acceptance closed GitHub330/331 on009238e; remote branch readback is009238e.
Single broadreview consumed: /root/frontier_standards accepted0;
/root/frontier_spec candidateS1 independently reproduced byprimary and accepted
blockingP2. Reopened330 pendingbounded repair;331 remainsclosed. One TDDpass is
reserved solelyforS1, no otherreviewfinding or baselinebug enters it. See
hf-03-04-review-and-remediation.md. Local comprehensive3.12 remainsrunning on
frozen009238e. Do not change Python source until its terminalreceipt; other
independent sessions are running their own test suites and are left untouched.

## Final checkpoint — outcome_progress

Both tickets implemented, integrated and validated on the owned integration
branch. Exactlyone broadreview andone boundedTDD remediation consumed. S1 fixed
at0b18828: omittednativeactiveflags remainunknown and cannotmatchworking. Ten
observation,13resource and7publicharness tests pass onboth3.11/3.12 finalsource.
Undefined-name, compileall, policywiring anddiffchecks pass. Isolated rebuiltwheel
131modules match,52tools, actualCLI/stdionativeprotocol smoke passesincludingS1.
No provider turns, production installation, service changes or CI. Complete wheel
hash and review adjudication are in hf-03-04-review-and-remediation.md.

Comprehensive3.12 frozen009238e:1521tests,1failure,1skip,565.025s. Original handoff
preflightscope_drift failed exact_idle_owned_client_not_ready. Isolated method
passes onfinalsource andunchangedbaseline. Retained as flaky validation evidence;
this is NOT a clean comprehensive pass, no quarantine/full-suite retry performed.
It does not exercise new observation/resource behavior; sourceacceptance remains
supported by the named caller tests and installedprotocol smoke. No handoffguard
was weakened. Raw firstfailure and both isolated comparisons are user-scoped.

Worker branchfeat/331-resource-ownership clean atfcc2030 and published with exact
remote readback; allseven ownedfiles matched integration before closure metadata
updates. Runtime source/test patch equivalence retained. Worker checkout was removed normally after final clean-state, runtime patch
equivalence and remote custody checks; branch remains durable.
Original operator checkout/main43e3db2 remainsuntouched. Source target is the
validated integration branch; main merge and release remainoutstanding boundaries,
not hidden completion claims. Goal budget meter and exact published finaltip are
reported at closeout; no successor resets the goal allowance.
