# Plan0156 checkpoint 01

Authority: operator execute-Plan156 goal; Plan0156/0157, issue248/249. Root source
base a7410107ca29e15e0fe0d5ef612d156d96b0e987, branch feat/agent-lifecycle.
Initial worktree clean. No shared services or production peers changed.

State transition: READY -> IN_PROGRESS. Progress: outcome_progress at the
deterministic public CLI seam; no installed criterion accepted.

TDD commands: initial cycle used `PYTHONPATH=src python -m unittest
tests.test_agent_spawn -v`; subsequent cycles use `.venv/bin/python -m unittest
tests.test_agent_spawn -v` or the specific method recorded in each red log.
Red/green receipts spawn-01 through04 are retained here. Cycle02 initially hit
missing websockets before the meaningful red; editable `.[mcp]` environment was
then installed, and the retained red shows None !=5. Cycle03 intermediate green
failed: fixture mistakenly returned global pane metadata to the exact pane list;
after correcting the fixture, production misread existing evidence value
`turn_completed` as `completed`. Corrected that value and passed; this is two
corrections, not an erased successful first attempt. Cycle04 changes the public
scenario to an in-progress turn followed by completed observation; red proved
duplicate task submission, green proves one creation/tab/task across three calls.
Fixtures use a real Unix protocol socket and real PTY/client process generation;
tmux and trusted-time observations are injected. They are not installed proof.

Implemented: host profile selection, fixed intent fingerprint, locked/fsynced
journal, uncertain thread-create fence, unique thread correlation name, owned
idle client readiness, exact queue identity and correlated completion readback.
This is an incomplete implementation checkpoint, not a released spawn product.

Remaining: interrupted tab and task-admission reconciliation, expiry checks at
later effects, safe profile/root/credential/caller scope, guarded MCP, installed
skills, real installed spawn evidence and cleanup. Then0158 refresh and0159
handoff with actual preflight/accounting, combined release/rollback/integration.
Do not route installed work through the unfinished controller yet.

Native discovery worker `/root/native_lifecycle_contract` completed read-only.
Installed Codex0.162.1 schemas under
`~/.local/state/codex-wake/plan0155/schema/v2/` show no thread/start idempotency
field or atomic goal transfer/import counters. Native queue correlation and
loaded inventory support the next slice. Primary reconciled this evidence with
current source. Worker did not mutate native state or delegate.

Goal readback at checkpoint preparation:184749 tokens,445 seconds, ACTIVE.
Ceiling2,000,000 tokens and six hours from epoch1791817417; checkpoint before
ceiling1791839017. Forty-five-minute backstop; each child and installed-effect
boundary requires checkpoint. Original full objective unchanged.

Next action: add one failing public regression for lost task-admission response,
then reconcile exact queue/turn evidence without resend; separately handle
interrupted tab effect. Keep two corrections per seam and one consolidated
Standards/Spec review plus one remediation pass for the campaign.

Memory disposition: unavailable. Healthy Graphiti atlas returned zero reviewed
Codex Wake cloud manifests; no safe target group established.

Checkpoint validation: `.venv/bin/python -m unittest tests.test_agent_spawn
tests.test_session_lifecycle tests.test_sessions tests.test_a2a_mcp -v` passed29
tests in3.872s; compileall and policy wiring PASS; git diff --check PASS.
Focused selection only; no comprehensive suite or installed acceptance yet.
