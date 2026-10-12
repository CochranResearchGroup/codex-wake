# Lifecycle design review

Comparison: design docs against main e3445f3; prototype independently preserved
at5e1b0ac on prototype/agent-lifecycle. Primary reviewed serially; no sub-agents.
Spec authority: approved lifecycle defaults and Plan0155 runtime questions.

## Standards

PASS: GLOSSARY remains language authority; plans have bounded scope and states.
Prototype code is retained off main; raw synthetic turn/private runtime evidence
stays private; curated findings expose no credentials. No product implementation,
service restart or installed configuration change. Existing goals/A2A work stay
attributed; published evidence distinguishes source, runtime, schema and future
acceptance. One redundant forge label alias removed to unblock validated issue
preflight; allowed actions/target/exact labels unchanged.

## Spec

PASS: actual refresh/handoff probe answered the uncertain questions. Same-thread
resume is explicitly insufficient for MCP freshness; skill proof is direct file
read. Outgoing-agent checkpoint, new loaded ID, native received/completed turn,
real v2 MCP call and process cleanup observed. Goal/allowance/claim migration and
ask-Matt invocation are expressly unproved and required by implementation tickets.
Spawn is a real prerequisite; refresh and handoff have no artificial blocking
edge, but share integration surfaces and execute serially. Fixed cumulative
bounds and transition reconciliation survive fresh context/controller restart.

## Validation

Three live short model turns; no original incident or production peers reused.
Ordinary installed close PASS; owned client/MCP/server/session process census
PASS. Curated runtime summary contains exact identities and raw-source hashes.
Four issue readbacks and native dependency links verified. Policy wiring and
active planning audit PASS; whitespace PASS. Prose/registry-only main changes
need no new tests; no claim of full source suite or model compliance. Hosted CI
waiting skipped under standing instruction. No leftover test tab/process.

## Remaining implementation gates

- Real public spawn/refresh/handoff CLI/MCP operations and owned intent journal.
- Fresh loaded skill/catalog proof and requested-resource refresh behavior.
- Genuine ask-Matt-selected successor preflight and one bounded native goal owner.
- Accounted original pending wakes/messages, explicit fresh actor/claim disposition.
- Interrupted transition, expiry, rollback, release/install and combined acceptance.

Review result: zero accepted blocking design findings. No feature completion
claim. The readiness frontier is issue249/Plan0157 only.
