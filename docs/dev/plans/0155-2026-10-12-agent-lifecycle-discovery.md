# Plan0155 — Agent lifecycle design and runtime probe

State: CLOSED
Workflow: DONE
Owner: primary / ecochran76
Branch: prototype/agent-lifecycle
Target: preserved prototype branch; design artifacts integrate via PR
Work-Item: docs/dev/plans/0155-2026-10-12-agent-lifecycle-discovery.md

## Current State

Three disposable native turns completed. Same-thread restart reread v2 skill
but retained v1 MCP; fresh `/new` thread loaded/called v2 MCP and read the agent's
handoff. One ordinary close and full OS cleanup verified; no private processes
remain. Prototype retained on named branch; design/spec/tickets derive from
these observations. Limits: no goal transfer, real A2A binding or actual ask-Matt
preflight qualification. Findings: docs/dev/evidence/plan0155/findings.md.

## Scope

Primary owns a serial disposable runtime probe, then source-backed lifecycle
specification and three execution tickets (spawn, refresh, handoff). Existing
shared services/agents and pending work remain unchanged. Preserve prototype on
a named published branch; root returns clean main after design integration.

## Non-goals

No production lifecycle controller, global configuration changes, live-peer
messages, real goal reset, cumulative allowance extension, unenrolled A2A
transfer, unattended rollout or proof beyond observed disposable runs.

## Acceptance criteria

- Observe fresh test thread and visible tab identities, actual readiness and exit.
- Change isolated skill/MCP markers, quit and resume exact same thread; report
  whether tools/skills actually refresh rather than assuming they do.
- Have outgoing test agent write its own private handoff, launch a fresh test
  chat and read that file; preserve original scope/allowance and identify missing
  binding/goal/preflight work explicitly.
- Capture interrupted transition reconciliation and clean up exact owned tabs
  and processes without disturbing other sessions.
- Publish findings and a small executable plan with blocking edges, invariants,
  failure outcomes and explicit runtime acceptance for each future ticket.

## Definition of done

Prototype and receipts preserved; every owned test tab/process closed; findings,
glossary terms, specification and tickets published; root clean main. Product
implementation tickets remain PLANNED until separately executed.

## Bounds and seams

Actual installed CLI and disposable TUI/native thread are the behavior seam.
Use a private CODEX_HOME and working root with only a toy MCP/skill; inherit
operator-configured model without a model override. At most six short model
turns, twelve minutes of live probe and two corrections per failing transition.
No model-fabricated runtime receipts. All live calls target test threads only.
No parallel write track; controller is the primary process outside test agents.
One serial Standards/Spec review; no new prototype tests or service restart.
