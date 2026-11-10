# LOCAL-P213 | Tab formatting performance diagnosis

Production first-enable/monitor cycles repeatedly returned workspace_timeout or
probe_deadline across42tabs. Expiring native styles then displayed STALE. The
30second monitor cycle setting did not alter the fixed20second native decoration
TTL; tuning the monitor alone therefore could not fix expiry. Production rollback
also timed out. Monitor stopped and exact42window original effective settings
restored via saved-baseline native batching; receipt in user-state
smart-format-activation/restoration-verified.json (1.816seconds).

Isolated feedback loop, no agent/model processes: private tmux42windows,
ControllerTabs.execute(tabs.format.enable/rollback), process-count assertion.
Unloaded old code6.907s enable/2.903s rollback,1window0.374/0.158s. The deterministic
spawn-budget check red at1728native subprocess calls; see process-count-red.log.
The 42window unloaded success does not disprove observed live timeout.

Primary cause confirmed: each option read spawned separate tmux processes for
explicit presence, value, effective value and parent; writes did the same plus
readback. Batched argv command queues retain all four observations and readback,
using random per-command output boundaries to preserve spaces/multiline strings.
All requested values validate before queued writes. No shell interpolation, broad
state mutation, TTL extension or freshness misrepresentation added. One process
per finite read/write batch replaces per-option process launches. Native identity,
linked-window and baseline policy checks remain with the existing owner.

42window original repro now275launches versus1728. First green2.627s enable,
0.775rollback. Repeated final timing in process-count-green.log.25focusedPython3.12
checks PASS19.729s;3causallyfocused3.11checks PASS1.862s. Public-seam regression
covers multiline literal option value, inherited baseline restoration and a finite
spawn budget. Existing linked-window, manual ownership, monitor and policy tests
pass. No comprehensive suite/hostedCI. Undefined-name lint, policy wiring and
whitespace pass. No production activation or deployment.

A separate42window formatting refresh budget probe (3.5seconds, representing the
formatting remainder of the default10second cycle) is retained in monitor-budget.log.
This isolates rendering from real native health discovery; it is not a guarantee
that the complete42tab live observation+render cycle will finish on a loaded host.
Health discovery probe_deadline remains an independently observed risk requiring
qualification before reactivation. Stale indication remains truthful rather than
being suppressed. Color dissatisfaction remains a UX requirement: no palette is
silently selected or reapplied. Plain mode or palette preview should be chosen
before any future activation.

No debug instrumentation in product. Private tmux server and sleep fixtures are
terminated in finally; reproduction scripts retained as explicit diagnostic
artifacts. Original production settings stay restored; monitor stays off.
Memory disposition forbidden: no explicit memory-write request.

Second causal correction: batching native calls alone still exceeded the3.5second
formatting allowance (partial at3.859s). Repeated serialization/fsync of the growing
workspace state per baseline/projection was load-bearing. Apply now persists the
complete set of original baselines before native writes, then commits batch
readback outcomes once. No baseline is written after its first native mutation.
Final isolated42window formatting refresh PASS1.143s; enable2.281s,rollback0.972s.
Final25focused3.12PASS20.853s;3focused3.11PASS1.862s. The process-budget regression
also bounds durable state-save count to prevent per-tab fsync regression.

Commands: PYTHONPATH=src python docs/dev/evidence/plan0213/process_repro.py41
and monitor_repro.py41 (space before41). Original red/green logs preserved.
Final source change is not installed or deployed. Actual loaded-host observation
and palette acceptance remain required; production remains rolled back.
