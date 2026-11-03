# WSL session control for codex-bots

State: OPEN
Owner: primary / ecochran76
Ticket: GitHub466 and children467-476
Branch: feat/wsl-session-control-0200
Base:171befbaf1be833f55eb0627c802e279cf0fbf35
WIP limit:3implementation lanes

## Current State

Spec466 frozen for execution; ten child tickets published. Primary owns T1;
workers own ready T2/T3 in separate worktrees. Ledger owns dependencies, runtime
evidence and custody. Review fixed point is recorded actual origin/main171befb;
one broad Standards/Spec review after ticket validation, one bounded TDD pass.

## Scope and acceptance

Use confirmed shared public WSL/PowerShell/API/local-MCP workflow against one
WSL server with actual target tab evidence. Milestone A unblocks codex-bots;
Milestone B qualifies Grok. Follow spec466 and each tracker acceptance. No
externally published OAuth, Windows server migration or uncontrolled provider
work. Preserve credentials, active sessions and native daemon packages. Source
validation and installed/real acceptance are separate. No hosted CI or memory
writes. Qualify exact package under UID1017 before any working daemon effects.

## Execution

Readiness requires every blocker validated at integration tip. Integrate serially;
workers own disjoint source/test paths, shared contracts primary-owned. Keep
tracker closure separate from implemented/integrated/validated ledger states.
No skipped required acceptance can close a ticket.

## Shared contract

`control` is the convenient local/remote session-control namespace, retaining
existing `sessions` and `flow-sessions` interfaces. local_sessions.discover/resolve
own internal target pinning; local health constructs separate TUI binding, never
confusing daemon process with controlling UI. Local controls reuse native owners
and durable operation journal. No hard-coded profile/grant setup on local path.
