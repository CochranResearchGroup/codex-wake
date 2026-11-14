# P232 | Native Grok workers for modded Codex

State: OPEN
Workflow: IN_PROGRESS; native authentication required
Work item: https://github.com/CochranResearchGroup/codex-wake/issues/621
Owner: primary / ecochran76
Branch: feat/native-grok-workers
Base: 1aa49867
WIP limit: one implementation lane; one completed read-only contract sidecar
Scope: native Grok delegation through the existing Codex Wake MCP extension

## Outcome

The operator selected native Grok first. Modded Codex already exposes the Wake
local Grok lifecycle tools; the first slice configures that existing extension
and makes its worker workflow discoverable. Grok sessions retain their own exact
native identity and operation receipts. A Codex model-provider switch, Rust
worker-tree replacement, browser Grok control, copied parent history/credentials,
new resource grants and arbitrary tool-approval bypass are outside this slice.

## Acceptance

- The actual modded account configuration selects the installed Wake MCP server
  and the same root as the new native owner.
- Installed worker guidance routes create, readiness, prompt, result and follow-up
  through existing tools, preserving idempotency, targets and unsupported cancel.
- One real native session reaches ready, receives one harmless prompt exactly
  once and returns its correlated answer. This criterion remains OPEN until native
  authentication is completed; transport readiness is not worker acceptance.
- Existing Codex daemons, unrelated Grok sessions and credential stores remain
  under their existing owners. Task-owned failed setup processes are stopped.

## Current State

Native Grok1.0.70 owner is running with explicit profile `codex-native`, configured
under the actual Codex MCP root. The first setup used the ordinary controller root;
read-only MCP discovery exposed the mismatch. The unused first owner was stopped,
its exact task-owned profile retired under the registry lock, and setup selected
the actual configured MCP root. No session/prompt was created during that correction.

Installed `wake_local_list(harness=grok,profile=codex-native)` now returns complete
with no holds. One stable `wake_local_create` intent reached the real native ACP
owner and returned `execution:not_started`, `reason:native_auth_required`. It
created no worker and started no provider work. The original operation ID and
target remain in private receipts; no replacement intent or prompt was issued.

The modded profile `codex-ecochran76` has its enabled Wake MCP entry pointing to
the same lifecycle root. A generic `modded` profile-inspection alias resolved a
different absent tenant; it was not used or provisioned. The managed interactive
launcher does not support `mcp get` with its remote-TUI arguments; the actual
selected account configuration was instead read directly, without changes.

The source and both installed Wake skill roots now include the native worker
reference and routing. Existing installed entry text was preserved; new reference
hashes match source. Native Codex binaries/daemons and the existing browser Grok
`input_unknown` hold were not changed.

## Remaining Gate

Complete Grok's supported native sign-in in the same home:
`grok login --device-auth`. Account approval belongs to the operator/native flow.
Do not copy tokens from a browser or vault into the owner. After verified sign-in,
inspect the existing owner and authenticate through its supported runtime behavior;
create a separately identified intended worker only after reconciling the original
terminal refusal. Require ready before the single harmless acceptance prompt.

Keep issue621 open until that acceptance passes. Publish the current guidance as
a draft packet; this plan does not claim native task execution is accepted.

## Evidence and Custody

Private operator state under `codex-wake/native-grok-workers` retains exact unit,
profile/process birth, initial-root correction, native refusal and skill preimages.
The dedicated user service has no automatic restart or login enablement. Its owned
Grok process uses an isolated leader socket; unrelated existing native sessions
are not resumed or controlled. The first owned native child was independently
verified stopped after correction.

Read-only sidecar `/root/grok_worker_contract` identified the public ACP lifecycle
and failure semantics; primary reconciled those against real installed calls.
No new fixture framework or speculative test suite was added for this configuration
and guidance slice. Hosted CI is skipped under the operator cost policy.
