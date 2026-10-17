# Plan0167 — Resource enforcement discoverability and first use

State: OPEN. Owner: primary / ecochran76. Work item: #274, #278.
Branch: feat/objective-enforcement. Base:7dfb868.

## Scope and acceptance

Audit how an agent discovers resource enforcement from a user-supplied budget.
Improve shipped skill triggers, packaged instructions, MCP tool descriptions and
operator release checks. Verify public tool discovery and relative skill links.
Do not change authority or containment semantics, install production skills,
restart user clients, merge or release. This is a requested onboarding audit, not
a second broad review of Plan0166.

## Current State

Discoverability gaps confirmed: resource enforcement absent from skill metadata
and MCP descriptions; detailed controls guide lacked a portable agent workflow.
Corrections add resource-limit triggers, inspection/decision steps, caller/TUI
coverage boundaries, missing-control behavior and release synchronization checks.
Public MCP catalog regression observed red, then three lifecycle MCP tests passed.

A release-blocking functional onboarding gap remains: an ordinary MCP caller's
first strict spawn reads its native goal before creating the dedicated executor.
Operator bootstrap worked in prior acceptance; it is not an agent authority
fallback. A zero-model-call public CLI reproduction preserves this ordering.
Private strict-home MCP services are also refused unless a control route is
separately qualified. No self-service release claim is justified yet.

## Next bounded packet

Design and implement an explicit caller-authorized bootstrap/control route,
retaining host-selected objective/profile, original limits, ownership and prior
spend. Prove cold first launch through the actual agent surface, unsupported
setup refusals, counted work, independent stop and unrelated preservation.
Do not bypass source-goal checks or let callers choose another objective through
an undocumented CLI route. Close this plan only after that proof, or record an
explicit decision to release operator-only support with honest agent guidance.
