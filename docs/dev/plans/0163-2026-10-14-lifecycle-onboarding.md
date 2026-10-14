# Plan0163 — Lifecycle discovery and onboarding

State: CLOSED
Workflow: DONE
Owner: primary / ecochran76
Target: origin/main
Branch: docs/lifecycle-onboarding
Pull-Request: https://github.com/CochranResearchGroup/codex-wake/pull/268
Work-Item: https://github.com/CochranResearchGroup/codex-wake/issues/267
Dependency: P156 and P162 integrated

## Current State

Source edits and bounded review complete. Delivery is through a protected-main
PR; installed skill synchronization follows verified merge, without a package
release or service restart. Source outcome and Git custody remain separate.

User approved polishing existing documentation/help/skill surfaces after Ask Matt
routing. Clean main base d587b86bba9ff23e03147738092e4c42a047e675; one registered
checkout, no competing active checkout. Current installed release is 0.15.1,
with 19 MCP tools. Existing glossary supplies all required lifecycle terms.

## Scope and non-goals

Make spawn, refresh and handoff discoverable from README and installed skill;
provide CLI/MCP templates and correct stale candidate/pending claims against
Plan0156 and Plan0162 evidence. Preserve host grants, checkpoint requirements,
readiness/acceptance distinction and cumulative resource boundaries.
No runtime behavior, command schema, release, service restart or paid native run.
No glossary/ADR change: no new domain decision. Governed issue267 records this slice; no peer messages or live runtime effects.

## Acceptance and definition of done

- README chooser links to a lifecycle quickstart and accurately states 19 tools.
- CLI templates parse against current CLI; MCP argument names match tool schemas.
- Agent skill routes each outcome, configuration readback and same-intent recovery.
- Current docs remove obsolete pending release/gate claims without inflating proof.
- Local links, JSON examples and whitespace checks pass; Standards and Spec review
  recorded separately against the pinned base working-tree patch.
- Updated skill is ready for backed-up synchronization to both installed roots
  after merged-main verification; no package release or client restart required.

## Execution and review bounds

Single owner, serialized edits -> surface validation -> two-axis review -> one
bounded remediation -> closeout. No independent implementation lane is needed.
At most one broad review and one verification of accepted findings.
Graphiti discovery skipped: supplied scope and current canonical evidence fully
answer this documentation correction; no historical decision needs recovery.

## Validation and review

surface-validation.json: four CLI parsers, four MCP schemas, six JSON examples,
13 local links and 19-tool catalog PASS. Documentation-only: no paid/native
transition run. Whitespace PASS. Active planning audit PASS with the repository's
existing accepted baseline, no unused baseline or new findings. Primary reviewed
Standards and Spec separately; fixed S163-01 hardcoded reviewer workflow and S163-02 installed portability, and
verified it closed-world. Evidence: docs/dev/evidence/plan0163/review.md.
Installed skills remain unchanged until merged-main byte verification.
