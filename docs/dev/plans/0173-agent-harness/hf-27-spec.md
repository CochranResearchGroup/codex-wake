# HF-27 terminal operator overview

State: OPEN. Issue: #340. Base: 2a51dd2. Operator decision: form d9b59f368e984dff925597304f90e901.

Terminal first, one-shot text/JSON. Show enrolled and suppressed managed identities,
workspace path, nullable task, binding and semantic freshness separately. Git
repo/worktree remains explicitly uninspected. No prompt, credentials or endpoints.
Limit 1..100 agents and total monotonic budget .1..30 seconds. Budget exhaustion
retains unknown rows and marks inventory partial. Missing observations never imply
absence, readiness, completion or authority.

Explicit local operator focus resolves an existing exact conversation and one
attachment afresh, checks runtime/root/process/pane/window/session/socket, then
revalidates immediately before selecting the pane. No open/resume/input fallback.
Grok focus unsupported until qualified equivalent native attachment evidence exists.
Host-verified operator capability and current common workspace.navigate permission
are required. MCP exposes overview/navigation plan only, never focus.

Public seams: OperatorOverview snapshot/navigation_plan/focus; command run/execute.
Tests use disposable managed state and private tmux/protocol fixtures; no operator
server, provider or production effects. Shared CLI/MCP registration is primary-owned.
