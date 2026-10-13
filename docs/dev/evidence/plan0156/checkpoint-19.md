# Plan0156 checkpoint19 — sandbox transport diagnosis and host-observation reframe

State transition: failed installed preflight → provider-free diagnosis → changed fixture prepared.
Acceptance state: full Plan0156 OPEN / IN_PROGRESS; native preflight/continuation not accepted.
Progress classification: blocker_reduction. Resource window/deadline and full scope
from checkpoint16 unchanged; historical receipts and failed budgets retained.

## Exact cause evidence

Native successor rollout reports effective model gpt-6.1-sol, workspace-write
sandbox, restricted network and its full managed permission profile. Replay uses
that exact profile through codex sandbox --sandbox-state-json (sandboxCwd is a
file URI). No permissions disabled, extended or bypassed.

RED command: python3 /tmp/plan156-resume-diagnosis/socket_visibility.py. Disposable
owned socket under /tmp/codex-daemon-1000: host stat/connect succeeds; sandbox
PermissionError13 at lstat while same listener stays alive. This matches actual
native_request lstat failure. Control socket elsewhere under /tmp allows stat
but denies connect with PermissionError1. Endpoint lifetime/identity changes are
not required. This reproduces actual sandbox protection without a provider call.

GREEN boundary qualification: python3
 scripts/handoff_sandbox_transport_qualification.py --execute
 --rollout /home/ecochran76/.local/state/codex-wake/plan0156/live-handoff-02/codex-home/sessions/2026/10/13/rollout-2026-10-13T05-37-12-01a134d6-767f-7061-bd4a-0ffa03547d98.jsonl
 --receipt docs/dev/evidence/plan0156/sandbox-transport-01.json.
Host socket accessible, sandbox socket denied; host-authored observation outside
sandbox workspace readable, overwrite denied. PASS in under one second, zero
model assignments. The boundary remains enforced, rather than granting socket
access to the sandbox. Initial bridge probe caught PermissionError only and
returned RED on EROFS30; corrected assertion accepts only EPERM/EACCES/EROFS.
All temporary sockets/files confined to generated owned directories and removed.

## Reframed fixture path

Installed acceptance runner performs real native skill/catalog and source MCP
resource reads on the host. It verifies paused source identity, enabled selected
guide and exact ready source resource, and publishes source/successor/checkpoint/
intent-bound observations outside the successor's writable workspace. Successor's
actual selected preflight script must read and verify that host evidence; it
still runs installed CLI version and verifies frozen local repo identity, writes
its own preflight/handoff artifacts and emits the native command marker.
Host also executes git ls-remote and focused installed socket/PTY validation;
restricted-network shell must not perform these host-only operations. Those
results are explicitly labeled performed_by=host_controller, never attributed to
successor execution. Wrong source or absent evidence fails closed.

Continuation script consumes host-observed exact active goal, runs the bounded
command and emits its native marker. External controller completes the exact
unchanged goal only after the actual native command/turn completion and current
active owner are verified. No shell socket access, extra model task, identity
inheritance or extra approval. This is prepared code, not proven native acceptance.
Instruction read now includes full selected instructions, canonical plans and
checkpoint in one output to avoid redundant reads/tool loops; nothing omitted.
Failure cleanup now discovers successor from receipt even if preflight never
reached awaiting_activation, retaining actual receiver usage/goal readback.

Qualification: generated helper compiles; public host-observation API checks
correct/foreign source identity (injected native boundary, not installed proof).
Relevant supervision/handoff checks PASS33/9.655s; source tests do not establish
native acceptance. No broad review consumed and no new provider attempt yet.

## Next bounded packet

Publish frozen candidate, fresh isolated installed11 and one new fixed-expiry
native fixture using this changed host-observation mechanism. Prior two failing
native attempts are preserved and end the unchanged socket-dependent method;
this reframe changes the failed transport, not the scope or accepted thresholds.
One attempt for the reframed packet; on failure preserve it and continue another
ready source unit rather than repeating provider attempts. Same total250000,
preflight150000, source<100000, ten minutes, two native assignments; original
parent deadline1791908966. Verify all installed module hashes/remote/clean tree
before effects. Full remaining gates in checkpoint18 still required.
Memory disposition: unavailable; no reviewed Codex Wake Graphiti target.
