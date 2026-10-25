# Issue #355: compact bounded agent dispatch

Source baseline: `ce1ad93eec437c1b4854dde2c9a174d5c5f94255` (`origin/main`).
Ticket: <https://github.com/CochranResearchGroup/codex-wake/issues/355>.
Parent contract: <https://github.com/CochranResearchGroup/codex-wake/issues/350>, story 21.
Validation: isolated source worktree, CPython 3.12.13, deterministic native Unix
WebSocket transport, fixture tmux/client and controlled clock/rollout usage. No
provider inference, installed binary qualification, production launch or campaign
renewal. The coordinator owns the parent plan and integration.

## Observable checks

- New public `sessions spawn` input is a compact `BOUNDED_ASSIGNMENT` packet for
  both plain instructions and approved briefs. The exact native thread creation
  has only `cwd`/`ephemeral`; no parent history/capability is transferred.
- The packet carries objective/instructions, approved pin/authority, workspace,
  non-goals, acceptance, evidence, allowance limits/deadline, stop conditions and
  a compact return contract. The fixture packet stays below 8 KiB, with exact
  rendered UTF-8 bytes and SHA256 inspectable in the lifecycle receipt.
- A fresh deterministic worker reads the pinned raw operands `[6,7]` through the
  packet locator and reports `42`. Raw operands are absent from the packet;
  observation time, coverage and ambiguity survive its summary. The original
  admission's verified source status is retained with explicit snapshot freshness.
- The observed output summary reports exactly two agent-message text bytes, the
  native thread/turn locator and coverage limits. It retains at most 16 message
  locators; full bodies remain at the native source. This measures bytes rather
  than tokens or allocation savings, and does not certify result acceptance.
- Full-history mode records a task-specific reason and required pinned source.
  Public CLI proposal rejects missing/empty reasons, unreferenced sources and
  summaries lacking ambiguity. Full history is fetched by locator rather than
  copied automatically.
- Historical version-1 lifecycle assignments keep their original bytes and
  fingerprint on retry; changing instructions under the same intent is denied.
- Existing configured objective reservation, overspend, expiry, final usage,
  queue reconciliation and handoff preflight cases remain regression checks.

## Red and green record

`uv run --extra dev python -m unittest
 tests.test_agent_spawn.AgentSpawnTests.test_spawn_executes_exact_assignment_once_across_pending_observation -q`
initially failed: delivered text had no `BOUNDED_ASSIGNMENT` packet (`IndexError`).
After the packet was wired into public spawn, this and the shared-actor budget
case passed: 2 tests, 3.307 s.

`uv run --extra dev python -m unittest
 tests.test_agent_spawn.AgentSpawnTests.test_fresh_worker_uses_bounded_brief_and_summary_without_parent_history -q`
initially failed because the existing brief validator rejected `dispatch`.
After optional dispatch validation and native output metadata, it passed:
1 test, 1.091 s.

`uv run --extra dev python -m unittest
 tests.test_task_brief_lifecycle.TaskBriefLifecycleTests.test_preexisting_spawn_intent_keeps_original_assignment_on_upgrade -q`
initially failed with `intent key already binds a different lifecycle assignment`;
after preserving the historical format it passed: 1 test, 0.172 s.

The first expanded handoff selection was interrupted after its mock worker tried
to parse an escaped preflight contract directly from raw task text. The fixture
now decodes packet `instructions` first and retains the exact original native
input for reconciliation. The pinned-brief successor check then passed:
1 test, 4.147 s. The interrupted run is not counted as a pass. Initial default
Python lacked `websockets`; qualified runs used the development environment.

Final focused acceptance used
`PYTHONPATH=src:tests /home/ecochran76/workspace.local/codex-wake/.venv/bin/python -W ignore::DeprecationWarning -m unittest`
with these cases: plain exact-once spawn, fresh brief/evidence worker,
full-history exception, historical intent preservation and invalid dispatch CLI
proposals. Result: **5 tests passed, 5.973 s**.

The same interpreter/environment ran
`tests.test_native_delivery tests.test_lifecycle_mcp -q`:
**18 tests passed, 8.143 s**.

Expanded source regression:

```sh
uv run --extra dev python -W ignore::DeprecationWarning -m unittest \
  tests.test_agent_spawn tests.test_task_brief_lifecycle \
  tests.test_task_briefs tests.test_task_brief_commands \
  tests.test_agent_handoff_preflight -q
```

Result: **96 tests passed, 273.087 s**, exit 0. This used the isolated worktree's
uv development environment, with the same CPython version. The five focused
checks above were rerun after the final fixture assertions changed; the expanded
selection was not mislabeled as the full repository suite.

Touched production and focused test files pass Ruff with only existing E701/E702
style debt excluded. Baseline/current lint counts match exactly for all touched
tracked Python files; the pre-existing handoff fixture also has F841 and is not
claimed lint-clean. `git diff --check` passes. CodeGraph was initialized for this
verified worktree, then synchronized after changes.

## Limits and integration

Current governor state is not supplied to this spawn seam by a verified public
result. Packets explicitly label it **unknown** and require authorized public
inspection; they never claim active enforcement or propagate invented counters.
Integration with sibling governor-state work must carry any already-verified
state, including operator deactivation, without treating a packet as renewed
allowance. Existing expiry-only profiles remain labelled as such.

No installed-runtime/provider or allocation-efficiency claim is made. The raw
input/turn locators remain authoritative; task completion is separate from
primary acceptance and issue closure. Optional `dispatch` fields extend brief
content without migrating existing revisions; older proposal validators reject
those new fields. Existing admitted intents retain their prior format.

Memory disposition: **forbidden**. This delegated lane is explicitly confined to
its worktree; user-scoped memory writes and coordinator closeout are outside its
authorized write surface.
