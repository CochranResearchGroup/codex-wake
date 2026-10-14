# Plan0156 checkpoint22 — owned active/missing-source rollback

State transition: rollback seam incomplete → source-qualified owned recovery.
Acceptance state: full Plan0156 OPEN / IN_PROGRESS; installed rollback and combined
preflight/continuation still open. Progress classification: outcome_progress at
public CLI/socket/PTY fixture seam. Parent resource window and full scope unchanged.

## Actual RED/GREEN cycles

Command prefix: PYTHONWARNINGS=ignore .venv/bin/python -m unittest
 tests.test_agent_handoff_preflight.HandoffPreflightTests.<case> -q.

- test_rollback_pauses_owned_active_successor_before_restoring_source:
  RED CLI5 instead of0; GREEN PASS1/0.831s. Exact goal identity/ownership checked,
  continuation lease fenced before pause/interrupt, source remains paused.
- test_rollback_restores_missing_source_in_the_owned_successor_pane:
  RED CLI5 instead of0; GREEN PASS1/0.708s. Old source process proven gone,
  original pending work checked, exact settled successor pane/generation/composer
  guarded, original conversation resumed there without thread/task creation.
- test_cached_rollback_budget_charges_late_receiver_usage_once:
  RED second CLI0 instead of5 on new receiver usage, ignoring late spend;
  GREEN PASS1/0.869s. Confirm prior requested budget applied before computing
  current conserved budget from original allowance and fresh receiver total.
  In worked fixture: source1000/used50; receiver30 then40; native budget970 then960,
  remaining920 then910. Lost setter responses reconcile without repeated setters.

Positive recovery qualifications (not fabricated RED cycles): lost active pause
response PASS1/0.681s; same-tab return to original context PASS1/0.733s; lost source
restoration reply PASS1/0.846s. Initial same-tab return test expected one respawn
rather than outbound+return two; corrected fixture assertion, no production fix
claimed for that test mistake.

Rollback now holds the source ownership flock through stop/restoration/budget
mutation. Source/successor lease IDs and goal identity must match; native target
lease pointer is published as soon as child identity is known. Source identity/
monotonic counters are reread before budget mutation. Unknown pause/interrupt/
respawn/setter responses preserve their exact effect and require observation.
Original goal/objective/creation identity stays; receiver spend never replenishes
caps or original deadline. Normal handoff cannot reopen a rolling-back/rolled-back
owner. No capability/claim transfer, provider turn or shared service mutation.

## Validation and proof limits

Focused lifecycle/daemon/MCP checks PASS123/28.580s. After final successor-lease
pointer guard, handoff preflight suite PASS27/14.748s. git diff --check PASS.
Native transport boundary is injected in these tests; real PTY process generations
are used, but this is not installed/native product acceptance. External subtotal/
unreported usage reserve from checkpoint20 unchanged; no provider calls here.

Next: freeze/install candidate and run one combined selected preflight, native
bounded continuation and same-tab rollback packet. Harness must expose mode and
actual rollback readback, retaining all prior failures; unchanged limits250000
fixture total/preflight150000/source<100000/ten minutes/two assignments and fixed
parent deadline1791908966. Native MCP method and host route must be qualified on
settled source before successor admission. Full proof cost and remaining parent
headroom must cover both mode proof, review/remediation and release gates.
Consolidated fresh Standards/Spec review plus bounded remediation still unconsumed.
Nonnull refresh-goal installed proof, required local CI, combined skills/CLI/MCP,
integration/release/rollback/cleanup, clean main and issues248–251 closure remain.
Memory disposition: unavailable; no reviewed Codex Wake Graphiti target.
