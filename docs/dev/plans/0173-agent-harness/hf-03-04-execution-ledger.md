# HF-03 / HF-04 parallel implementation frontier

State: OPEN
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
