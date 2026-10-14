# Plan0156 checkpoint21 — same owned tab, fresh conversation

State transition: unsupported same-tab mode → source-qualified same-tab transition.
Acceptance state: full Plan0156 OPEN / IN_PROGRESS; installed same-tab/preflight/
continuation remain unaccepted. Progress classification: outcome_progress at
public CLI/native fixture seam only. Parent limits/deadline unchanged.

RED: PYTHONWARNINGS=ignore .venv/bin/python -m unittest
 tests.test_agent_handoff_preflight.HandoffPreflightTests.test_same_tab_uses_fresh_identity_in_original_owned_pane_once -q.
Actual CLI returns blocked instead of awaiting_activation because same-tab was
unimplemented. GREEN same command: PASS1/0.477s.

Same-tab uses native fresh thread creation and exact target resume in the
original verified single-pane tab, through tmux respawn-pane. No blind /new key
injection and no same-thread resume misrepresented as fresh context. Spawn
adapter replacement is internal to explicitly selected handoff mode, journaled
in immutable child intent with exact source/PID-generation/pane/window identity.
Before replacement it rechecks source's empty composer, pending obligations,
paused goal and the original attachment. Native name, removed peer environment,
new client identity and exact task admission continue through existing guards.

Subsequent handoff calls reconcile the detached original source with the exact
fresh successor in that pane and observe old generation exit. Original source
conversation/checkpoint/native goal remain available and paused; pending work is
still checked and separately attributed. No source goal reset or capability copy.
Unknown respawn reply searches the existing native/pane generation, never repeats
respawn or creates a replacement thread/tab/task.

Recovery qualification: same command with
 test_same_tab_lost_respawn_response_reconciles_new_generation_without_respawn:
PASS1/0.644s. This is positive lost-response qualification, not a separate TDD RED.
The first recovery-test failure was a misplaced assertion in fixture handler,
corrected in the harness; it is not presented as a production defect/fix cycle.
Real PTY clients, simulated external tmux/native boundary; no provider acceptance.

Second actual RED/GREEN: same command with
 test_same_tab_stale_title_cannot_replace_pinned_source_generation.
A replacement client temporarily retains old pane title; source guard overwrote
pinned generation and changed child intent, yielding WakeError. RED expected
source_attachment_generation_changed but got WakeError. Guard now holds without
overwriting original generation; after title catches up identical intent reaches
preflight with one respawn/thread/task. GREEN PASS1/0.497s.

Relevant validation: PYTHONWARNINGS=ignore .venv/bin/python -m unittest
 tests.test_agent_handoff_preflight tests.test_agent_handoff tests.test_agent_spawn
 tests.test_agent_refresh tests.test_session_lifecycle tests.test_daemon
 tests.test_lifecycle_mcp tests.test_a2a_mcp
 tests.test_handoff_acceptance_supervision -q — PASS117/23.840s.
Expected argparse rejection output belongs to a negative test. git diff --check PASS.
No broad final CI/review, native same-tab or product-complete claim follows.

Next source unit: rollback from active owned successor and missing original source
attachment, with exact owner/turn fencing and conserved receiver usage. Same-tab
source qualification does not waive installed rollback/cleanup, nonnull refresh
goal proof, successful selected native preflight/goal continuation, combined
review/remediation, CI, integration/release/clean main or issues248–251 closure.
External known subtotal263464 plus unknown receiver reserve250000 remains; zero
additional provider assignments here. Latest observed root275992/2160s before
final validation. Stop and checkpoint before2M or deadline1791908966.
Memory disposition: unavailable; no reviewed Codex Wake Graphiti target.
