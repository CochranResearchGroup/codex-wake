# Controller capability inventory — #382

Research evidence for [#382](https://github.com/CochranResearchGroup/codex-wake/issues/382), subordinate to [decision map #381](https://github.com/CochranResearchGroup/codex-wake/issues/381). Planning only; this note selects no new architecture. Question: which existing operations and authority owners can support consolidation, and where do adapters or missing contracts remain?

## Evidence boundary

Inspected 2026-10-29: Wake source pinned to `0ab5a3a302a948ea658dc6af3e19219c73cc4296`; Profiles merged source `3a9a3d4767910e2d1535aff40c29a228958e5e4c`; local modified native source `b706004728800f4cba08e5554b854f1bd5461f25`. Root Wake local main `43e3db2` differs; it was preserved and graph discovery there was treated only as a locator. Final Wake claims below use the pinned research checkout. Sources are first-party code, checked-in acceptance artifacts and explicit tracker readbacks. No credential contents or live sessions were inspected, no provider calls were made, and installed tests were not rerun.

The private deployment receipt `~/.local/state/codex-wake/repairs/profile-deployment-20261028/qualification.json` reports: both PRs merged; Wake `0.22.0.dev2-0ab5a3a` prefix/command links qualified; Profiles installed/staged with live activation rolled back. This is a historical deployment receipt, corroborated by current [#380](https://github.com/CochranResearchGroup/codex-wake/issues/380), not a fresh fleet census. The planning packet locator is `~/.local/state/codex-wake/planning/controller-wayfinder-20261029/map-receipt.json`; the issue map remains planning authority.

## Operation matrix

“API” below means importable Python owners or native app-server protocol, not a proven remotely authenticated controller service. CLI/MCP coverage is inspected source coverage, not universal installed or provider parity. R = reuse owner, A = adapt existing seam, M = missing controller contract.

| Resource / operation | Existing owner and interfaces | Reuse, adaptation and blocker |
| --- | --- | --- |
| Managed agent / list, show, enroll, reconcile, observe, wait | Wake `ManagedInventory`, observation adapter; CLI and stdio MCP | **R/A:** identity is runtime + namespace + conversation ID, with fresh process/attachment evidence. Membership grants no operations. Add explicit host identity/routing without replacing native conversation identity. [1,2,20] |
| Session / discover, resolve, current, show, target, spawn | Wake CLI/MCP; native thread start/read/resume | **R/A:** informal tab selectors resolve and pin exact targets; ambiguity and partial discovery hold. Launch requires approved profile, stable intent and readiness before task admission. Tab creation alone is not agent execution. [1,3] |
| Message / send, inbox/outbox, read, acknowledge, reply, cancel, reconcile | Wake mailbox, CLI and MCP | **R:** durable IDs, idempotency, TTL, claims, disposition evidence and uncertain-effect reconciliation. Delivery notification and accepted work are distinct from completed answer. [1,4] |
| Response requested / return target answer | Mailbox `in_reply_to`, correlation, `replies`; CLI `wait --for reply`; MCP `arm-reply` | **A/M:** foundations exist, but no single inspected send-and-return-answer operation. CLI wait returns a JSON receipt/replies structure; body read is separate. Agent return can use exact correlated reply wake. A common result envelope, wait/cancel/timeouts and stdout/agent routing need specification. [1,4,5] |
| Task / propose, approve, inspect, admit, pin brief | Wake task-brief owner; CLI/MCP | **R:** task, revision and assignment pin existing scope. Approval is exact host delegation, never a caller-selected role. Reuse for inspectable agent proposals; it is not yet a general flow proposal language. [2] |
| Resource / claim, check, release | Wake cooperative resource claims; CLI/MCP | **R/A:** worktree/build-prefix/install-prefix paths, device/inode identity, exact owner process and claim generation. Claims do not confer OS permissions or a future mutation lease. Broader resource types and cross-host naming need adapters/contracts. [2,6] |
| Job / profile, launch, show, cancel, await | Wake bounded local-command owner; CLI/MCP | **R/A:** idempotent job intents, generation-fenced cancellation, terminal result and existing wake-based await. Host command profiles and task authority remain independent. This is not arbitrary remote shell admission. [7,22] |
| Attention / request, list, show; acceptance / define, evaluate, inspect, decide | Wake frontier owners; CLI/MCP | **R:** explicit attention requests and evidence contracts are existing primitives; preserve delegated roles and distinguish evaluation from approval. [7] |
| Tab / preview, show, apply, undo | Wake tmux organization and journal | **R/A:** CLI supports all four; MCP deliberately exposes only preview/show. Apply/undo require verified local operator. Permutes tabs while retaining focus; submits no terminal input/native turn. psmux and remote presentation parity are unqualified here. [7,8] |
| Refresh / scoped MCP resources or invoking client; handoff / linked successor | Wake lifecycle CLI/MCP, native RPC | **R/A:** preserve conversation on refresh; handoff requires checkpoint hash, original cumulative allowance/deadline and approved continuation. Scope/idle/native capability checks are explicit; queued is not completed. Never substitute shared restart for unsupported thread refresh. [1,9] |
| Supervision / limits, readiness, watcher, pause/interrupt | Wake goal-limits and native goal/turn owners; CLI/MCP | **R/A:** sampled cumulative accounting, original deadline, checkpoint and exact-turn stop evidence exist. Enrollment/configuration does not prove active enforcement. Recovery observation default and opt-in policy must wrap existing authority rather than auto-enable it. [1] |
| Flow / sequence, branch, foreach, repeat, fan-out/join | Existing briefs/messages/jobs/acceptance are composable primitives | **M:** no durable general flow executor or unified declarative+SDK contract found in inspected surface. HF-09 remains TRIAGE/NOT_AUTHORIZED, explicitly requiring program-position persistence and uncertain-step reconciliation. Treat subsequent flow sketches as planning, not capability proof. [10] |
| Account/build/config / inspect, launch, history, continue, upgrade | Profiles owns selection/configuration; native owns actual runtime; Wake consumes identity | **R/A:** retain these owners. No Profiles MCP/remote API parity was established; subprocess/SDK adapters remain work. Production activation is blocked by #380. [11–14] |

## Identity and consolidation seams

Native conversation UUID is insufficient alone across tenant homes. Profiles history discovery retains owner and namespace, rejects shared mutable database paths and unsupported schemas, and ordinary resume routes to the exact owner. Wake managed identity similarly includes runtime/namespace/conversation, with attachments as presentation evidence. Resource claims add process start/boot identity and generation. These are reusable boundaries; host identity is an additional unresolved controller dimension, not a reason to rename conversations. [2,6,12,20]

Profiles already separates account and build channel, checks executable hashes/history compatibility, pins executable bytes and isolates account environment. Shared settings/skills/rules/MCP definitions have inspectable provenance. Codex account authentication remains tenant-local; supported connector identity scope is separately described, not automatically copied. Native RPC request IDs correlate transport responses, while thread/turn IDs and mailbox message/reply IDs correlate different application resources; these must not be collapsed into one acknowledgment. [4,11,13,15,21]

Cross-account continuation creates a separate successor from supported JSONL history, persists lineage and uncertainty, carries the existing request-accounting reference and marks work unauthorized. Native-goal continuation remains deferred; compressed ancestry is held rather than silently truncated. Therefore this operation cannot currently stand in for transparent account switching with automatic goal transfer. [14]

The package manifest exposes CLI, daemon, hook, webhook listener and stdio MCP entrypoints. MCP is a facade over existing CLI/owner boundaries. An HTTP webhook or source Python API is not proof of an authenticated cross-host operations API. Native source defines thread start/resume, turn start/interrupt and scoped MCP reload; Wake lifecycle access additionally constrains owned local Unix sockets. Remote admission, host registration, capability negotiation and transport parity require the later decisions. [1,9,15,16]

## Deployment contradictions and stop conditions

The account/build spec still says implementation incomplete and its ledger retains `merged:false`/`production_activated:false`, while later ledger acceptance and #380 establish merged source plus staged packages. Preserve that chronology: stale spec/publication prose cannot negate later receipts, and later fixture acceptance cannot establish production activation. The old harness smoke proves 45 tools in an isolated `0.21.0` wheel only, not current installed tool count or live deployment. [11,17,18]

#380 identifies an indirect global sessions → named-account → shared-store dependency missed by the initial census. Original global routing/account links were restored; temporary private state retained. Plain executable/profile links/Zsh configuration reverted and the writer remains unattributed. Consolidation must first reconcile launcher/config ownership, inventory indirect dependencies, retain the legacy store and establish historical ownership before assigning records. No activation retry, credential copying or active-client restart follows from this inventory. Workspace recovery #368 remains separate. [19]

Research exit: source operations, ownership, parity exceptions and migration blockers are supported. Missing live fleet parity, psmux behavior, cross-host auth/admission, general flow execution and response-return product semantics remain named evidence/specification gaps. Memory disposition: **forbidden** for this planning-only lane; no graph write authorized, primary coordinator owns serial closeout.

## Sources

Wake relative links resolve in the committed research snapshot based on the inspected base; Profiles links to inspected merged commit. Native paths refer to local modified source, not an upstream capability claim.

[1]: ../../../src/codex_wake/mcp_server.py
[2]: ../../../src/codex_wake/harness_mcp.py
[3]: ../../../src/codex_wake/session_lifecycle.py
[4]: ../../../src/codex_wake/a2a_mailbox.py
[5]: ../../../src/codex_wake/messages_cli.py
[6]: ../../../src/codex_wake/resource_claims.py
[7]: ../../../src/codex_wake/frontier_mcp.py
[8]: ../../../src/codex_wake/tab_organization_commands.py
[9]: ../../../src/codex_wake/native_protocol.py
[10]: ../plans/0173-agent-harness/0009-2026-10-23-hf-09-turn-sequence.md
[11]: ../plans/0179-account-build-workflow/spec.md
[12]: https://github.com/ecochran76/codex-profiles/blob/3a9a3d4767910e2d1535aff40c29a228958e5e4c/src/codex_profiles/history.py
[13]: https://github.com/ecochran76/codex-profiles/blob/3a9a3d4767910e2d1535aff40c29a228958e5e4c/src/codex_profiles/build_channels.py
[14]: https://github.com/ecochran76/codex-profiles/blob/3a9a3d4767910e2d1535aff40c29a228958e5e4c/src/codex_profiles/continuation.py
[15]: /home/ecochran76/workspace.local/codex-ar2-orphan-output/codex-rs/app-server-protocol/src/protocol/common.rs
[16]: ../../../pyproject.toml
[17]: ../plans/0179-account-build-workflow/ledger.json
[18]: ../plans/0173-agent-harness/installed-smoke.json
[19]: https://github.com/CochranResearchGroup/codex-wake/issues/380

[20]: ../../../src/codex_wake/managed_inventory.py
[21]: https://github.com/ecochran76/codex-profiles/blob/3a9a3d4767910e2d1535aff40c29a228958e5e4c/src/codex_profiles/config.py
[22]: ../../../src/codex_wake/background_jobs.py
