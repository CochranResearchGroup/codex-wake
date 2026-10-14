# Correction/reset source checkpoint

2026-10-14; branch feat/agent-lifecycle; full plan OPEN.

Explicit reset retains all cumulative actor spend, original deadline and cycle
history. It replaces caps only with an exact operator authorization revision and
settled known actor state. Public CLI cap reset to100 with prior spend40 reports60
remaining; replay leaves the same three authorization records. Extensions also
reconcile exact replay without creating a second grant.

Durable native goal aliases prevent charging the same successor goal once under
its preflight actor and again when it becomes a source. Public ledger worked
example preflight10+goal20 remains30 after restart/source snapshot replay.

Correction is an owned queued assignment, not just a cycle counter. A correct
review must supply criterion/path/hash evidence within host correction_scope.
The controller retains the original reservation, deadline and immutable source
checkpoint. Correction tasks have unique stable identities; previous reviews
remain in the receipt. Public CLI fixture repairs the actual declared file,
re-reviews it and prepares continuation after60 total preflight tokens. Repeated
rejection executes exactly two corrective assignments (90 cumulative tokens),
then stops without a goal. Terminal replay creates no fourth queue item. A path
outside host scope cannot consume a correction cycle or create an assignment.

Red/green:

- test_explicit_reset_replaces_caps_without_erasing_spend_or_cycles: missing
  method failed, then passed with preserved spend40 and remaining20.
- test_successor_goal_and_preflight_are_charged_once_when_successor_becomes_source:
  missing binding failed, then passed with one30-token debit.
- test_bounded_correction_runs_owned_packet_then_accepts_actual_repair:
  initially blocked; passed after real owned assignment wiring.
- test_repeated_rejection_stops_after_two_owned_correction_cycles: first failed
  because duplicate task text made native assignment evidence ambiguous; stable
  correction identity fixes this without retrying uncertain queue effects.

Focused selection72 tests passed22.251s after scope and terminal-replay checks;
provider-free harness supervision is included. Compileall, policy wiring and
diff whitespace passed. Executable MCP smoke passed with18 named tools,11 calls,
zero native turns/notifications and owned fixture cleanup. CI on e9a9cc5 passed
its unit stage but failed the installed smoke's stale17-tool assertion on both
Python versions; the assertion now explicitly includes configuration at18.
Retained logs: /tmp/plan0156-ci-e9a9cc5-failed.log,
/tmp/plan0156-correction-final2.log, /tmp/plan0156-mcp-smoke.log.

Worker/root/native_harness_revision changed only the installed acceptance script.
Its plain-Python supervision attempt failed at import (missing PYTHONPATH); the
primary's environment-valid selection passed. Primary inspected and integrated
the result. Requested model/effort and token counter unavailable; retain a
conservative100,000-token external reservation. No native effects were attempted
by that worker. Actual selected instruction catalog support and both native modes
remain unverified. Source, installed acceptance and release are separate gates.
