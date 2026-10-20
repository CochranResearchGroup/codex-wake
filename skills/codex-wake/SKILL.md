---
name: codex-wake
description: Use Codex Wake when a user gives /goal resource limits (tokens, time, memory, swap, CPU, tasks): register token/time limits for the existing native goal through MCP; an independent watcher requests checkpoint then pauses the goal and interrupts its exact active turn. Dedicated host-approved executors provide separate memory/CPU controls. Also use it for durable agent-to-agent requests, correlated replies, exclusive work claims, suspended reply wakes, session/tab lookup, wake listing/cancellation and persistent emergency pause, host-approved worker spawn, self-refresh of skill/MCP resources with approved shared reload after idle checks, fresh-context handoff, and scheduled follow-ups. Prefer its MCP tools for tracked exchanges when configured; use the CLI otherwise.
---

# Codex Wake

Use durable triggers when work must resume after a defined event. Load the
matching reference before acting; inspect the returned receipt before claiming
registration, delivery, enforcement or refresh.

| Request | Required reference |
| --- | --- |
| Token/time allowance for the existing native `/goal`; enrollment or held enforcement | [Existing goal limits](references/existing-goal-limits.md) |
| Controller maintenance or real-agent acceptance | [Operator maintenance and acceptance](references/controller-maintenance.md) |
| Memory, swap, CPU or task controls in a dedicated executor | [Resource limits](references/resource-limits.md) |
| Update this client's skill/MCP, spawn a worker or hand off to fresh context | [Lifecycle](references/lifecycle.md) and [refresh workflow](references/workflows.md#refresh-this-agent-after-an-update) |
| List/cancel wakes or emergency pause/interrupt/resume | [Wake controls](references/wake-controls.md) |
| Durable peer request, claim, reply or suspended reply wake | [Tracked work](references/workflows.md#tracked-agent-to-agent-work) and [mailbox workflow](references/workflows.md#local-agent-mailbox-workflow) |
| Find a session/tab or address a human tab target | [Human targets](references/workflows.md#human-tab-targets-through-mcp) |
| Scheduled follow-up, transport choice or host readiness | [Native workflow and preconditions](references/workflows.md#native-workflow-first) and [patterns](references/workflows.md#common-patterns) |

Use your actual native caller identity and existing objective allocation.
Successors retain cumulative spend, the original deadline and stop latches.
New enrollment defaults to fresh input plus output; re-enrollment preserves its
accounting basis. Verify a fresh independent controller and qualified accounting
before autonomous campaign work. A held campaign still permits operator replies,
bounded setup diagnosis and checkpoint writing. Only explicit user renewal
recorded through host authority creates a new allowance.

For refresh, inspect the profile's scope and preserve one fixed intent. Shared
MCP refresh requires all affected conversations idle; queued admission is not
verified refresh. Client replacement alone does not prove MCP reconnection.

Detailed workflows and examples remain in [workflows](references/workflows.md).
