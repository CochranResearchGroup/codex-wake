# Resource-enforcement discovery audit

Request: before PR/release, verify agents will discover and correctly use Wake
when the user supplies resource limits. Base7dfb868; same feature branch.

## Findings and changes

1. **Fixed — discovery metadata omitted the capability.** The shipped skill
   description and public MCP configuration/spawn descriptions now mention
   /goal resource limits, dedicated strict execution and sampled token stops.
   An actual MCP tools/list regression was observed red, then green.
2. **Fixed — no portable first-use guide.** Added the packaged resource-limits
   reference and links from skill, README and lifecycle docs. It tells agents
   what to inspect, where the limits apply, what missing setup means, how to
   preserve deadlines/accounting and when only the operator can reconcile/renew.
3. **Fixed — release synchronization was implicit.** The operator guide now
   requires complete skill-directory publication, hash/link checks, skill catalog
   refresh and MCP-client reload. The wheel does not contain the skill directory.
   Existing installed skills and clients were not changed by this audit.
4. **OPEN RELEASE BLOCKER — ordinary-caller first bootstrap is missing.**
   `operation_binding` pins MCP to the caller UUID; `admit_spawn` reads that
   source's native goal before `ensure_execution`. In a new dedicated home there
   is no such source/server. Proven prior native acceptance used non-UUID
   operator bootstrap references. The zero-effect public CLI reproduction
   injects unavailable endpoint and ready-monitor responses and observes
   thread/goal/get with zero executor-creation calls. It is ordering evidence,
   not native first-launch acceptance. See bootstrap-order.json and its script.
5. **Control route requires qualification.** Strict-home config refuses
   unqualified MCP servers/hooks. Neither inherited outer tools nor installing
   the skill establishes a supported in-executor control route. Do not loosen
   identity, grants, parent accounting or endpoint ownership to hide this gap.

## Verification

- Public MCP discovery: retained failing catalog test; all3 lifecycle MCP tests
  passed after metadata corrections.
- Focused MCP/strict configuration selection:9 passed, no skips,3.810s.
- Isolated complete skill copy:7 files,6 relative links all resolve. No actual
  user skill root changed. Hash manifest retained.
- Policy wiring and diff whitespace checks pass. No containment semantics changed,
  no model calls, no service starts and no production installation occurred.

## Release decision

The dedicated operator-managed containment implementation remains accepted.
Self-service agent first use is **not release-ready**. Plan0167 stays OPEN for an
explicit caller-authorized bootstrap/control interface and a cold normal-agent
proof: user budget → approved profile → contained work → cumulative readback →
verified stop, with no unrelated effects. Documentation is not that proof.
