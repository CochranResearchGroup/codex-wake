# Plan0154 — A2A response standards

State: CLOSED
Workflow: DONE
Owner: primary / ecochran76
Branch: docs/a2a-response-standards
Target: origin/main
Work-Item: docs/dev/plans/0154-2026-10-11-a2a-response-standards.md

## Current State

Response standard implemented in the bundled skill/reference, invocation metadata,
use cases and human/MCP guides. Both installed skill copies match source, with
previous bytes retained privately. Eight routing scenarios reconciled against
existing tool/worker rules. Links, policy wiring, active planning audit and
whitespace checks pass. No runtime code, production messages or service changes.
Review: docs/dev/evidence/plan0154/review.md. Published integration readback
is retained separately in private Plan0154 custody receipts.

## Scope

One serial packet: communication standard, skill and examples, human/MCP guides,
review against current notification/claim contracts, installed skill parity,
normal PR integration and clean main. Primary owns all write surfaces.

## Non-goals

No new transport, schema, CLI flag, runtime code, service restart, production
message, wake, enrollment or third-party delegation. Do not alter other sessions.
No claim of empirical model compliance or automatic enforcement.

## Acceptance criteria

- Questions/work requests receive a correlated sender reply; a local answer alone
  does not deliver it. Notices/results do not trigger acknowledgement loops.
- Separate message delivery from response routing. Default notified requests
  require notify replies; explicitly inbox-only exchanges reply inbox.
- Sender states purpose, expected response, recipient, deadline and evidence.
- Third-party sends have their own identity, authorization and correlation; they
  never redirect the original reply or inherit operator authority.
- Busy, unconfigured and uncertain delivery do not silently degrade to TUI or
  create retries; actual admission is distinguished from recipient receipt.
- Bundled and both installed skills contain the same standard and examples.

## Definition of done

Published PR integrated, source docs and installed skill hashes verified; root
clean main. Scenario walkthrough, link checks, policy wiring and active planning
audit pass. Existing released MCP tools and worker remain unchanged.

## Bounds and validation

Docs/skills only. No new tests for prose. Inspect existing public schemas and
worker instructions, then walk eight concrete routing scenarios. One Standards
and Spec review by primary; fix accepted contradictions once. Critical path is
serial; no independent write track or sub-agent is needed.
