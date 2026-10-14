# Plan0156 checkpoint11 — source pause accounting and late expiry

Parent ACTIVE; branch feat/agent-lifecycle, base258e0ca. Latest readback root
1303297 tokens/14421 seconds plus external125341 = conservative1428638 tokens.
Original two-million/six-hour ceiling1791839017 unchanged. No provider assignment
or installed/shared-service change. Issues and full acceptance remain open.

Cycle47 public CLI RED overgranted920 when source pause increased usage50→53;
GREEN recomputes conserved allowance from observed paused source, producing917.
Pause must preserve thread/objective/budget/creation identity and nondecreasing
native counters. An allowance that no longer fits holds before successor effects.
RED /tmp/plan156-handoff47-red.log; GREEN4 tests PASS2.288s in
/tmp/plan156-handoff47-green.log. Supplemental existing-expiry qualification:
preflight crosses original deadline; no successor goal is prepared. This check
was GREEN against the existing guard, not a new RED/GREEN implementation cycle.
Five composite checks PASS2.224s in /tmp/plan156-handoff-expiry-qualification.log.
57 focused lifecycle checks PASS11.519s in /tmp/plan156-checkpoint11-focused.log.

Next bounded seam: independently enforced continuation deadline in the existing
codex-waked lifecycle poll, with persisted exact owner/goal identity, restart
reconciliation and pause/interrupt of only owned activity. Native goal API has no
wall-time field or atomic transfer. Existing before-effect checks are admission
fences and cannot establish enforcement after activation. Activation stays held.
No new autonomous scheduler or per-agent daemon is authorized by this design.
Private runtime acceptance must identify prefix and preserve unrelated services.

Checkpoint10 carries the complete remaining gates: actual successor/selected
workflow/resource acceptance, same-tab, rollback, handoff MCP, pending-work
preservation/routing, one combined fresh review/remediation, required local gates,
PR/main integration/release, installed acceptance/rollback/cleanup, clean main and
evidence-backed issue closures. Source checkpoint writer02 window stays expired.
Memory disposition unavailable; checkpoint-01-memory.json receipt retained.
