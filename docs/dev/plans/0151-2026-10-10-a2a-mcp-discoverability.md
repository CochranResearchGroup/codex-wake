# Plan0151 — Discoverable agent-to-agent MCP

State: OPEN
Workflow: IN_PROGRESS
Owner: primary / ecochran76
Lane: P73
Branch: feat/a2a-mcp
Target: origin/main
Work-Item: https://github.com/CochranResearchGroup/codex-wake/issues/240

## Scope

Advertise accepted tracked request/reply in README and agent skill; provide an
optional official-SDK stdio MCP facade over the same CLI domain with installation,
operator setup and agent workflow examples. Bind actor capability/root to host launch context. Require each message call
to declare its actual native-shell thread claim, validated against runtime and
fixed capability; never infer caller identity from a shared server environment. Bounded CLI calls use
shared existing daemon; no separate mailbox, dispatcher or watcher per thread.

## Non-goals

No production messages, enrollment, operator tools, force-close, blind retries,
new transport, changed mailbox schema or recovery behavior. No gov_policy
measurement; explicit operator request parks its evaluation for future work.

## Acceptance criteria

- Human and agent entrypoints advertise exact capabilities and setup boundaries.
- Tools list schemas/descriptions/annotations for session discovery and tracked
  send/inbox/read/ack/reply/show/reconcile/cancel/arm-reply, with no arbitrary CLI.
- Same CLI identity/capability/claim/generation/idempotency rules remain authority;
  inherited pane or caller-selected credentials cannot impersonate another actor.
- Real installed stdio MCP initialization/discovery and isolated request/reply
  prove bodies, correlation, accepted/completed receipts, dedup and denial.
- Invalid requests invoke no command; uncertainty is surfaced and never retried.
- Focused tests, installed package parity, governed integration/release and MCP
  registration verified without service restart or changes to unrelated sessions.

## Definition of done

Integrated exact release and installed MCP entrypoint qualified; setup documents
and installed skill match source; root main clean; issue closed from receipts.
Existing A2A acceptance remains complete independently of this additive facade.

## Current State

Issue240 owned-target preflight PASS. Existing0.12.0 has no MCP entrypoint;
README/skill headline understate A2A. Optional SDK implementation and docs next.

## Test seams and bounds

MCP tools public list/call contracts, CLI domain via private existing fixture
runtime, installed stdio protocol client. One primary, no delegated work, two
correction attempts per seam, one serial Standards/Spec review. Checkpoint on
qualification and before release; no real notification or test Byobu tab.

## Context contract revision

Host observation: this session's governance MCP process has no CODEX_THREAD_ID,
while native shell does. Upstream issue19937 documents the same gap. Startup
identity cannot authorize multiplexed caller operations. MCP schemas now require
caller_thread_id on message/current tools, verified by unchanged CLI identity and
fixed-capability checks. No credential/root/operator overrides in tool arguments;
explicit caller facts are not attestation. Shared-connection child-claim denial
is added to installed qualification. No Codex patch or new identity authority.
