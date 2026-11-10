# Due visible-screen capture batching

Named risk: one transient native client per pane makes the once-per-minute
100pane inactive error pass exceed the idle CPU allowance. Active/dirty passes
also spend child CPU despite unchanged per-pane cadence. This is #541 shared
observation integration, not a new provider or terminal-output subscription.

ObservationCache now selects only due error checks through the same public
TieredChecks.is_due policy used by run(). A typed same-user tmux adapter batches
current-visible-screen reads in groups of16 using existing random frame markers.
History is not requested. Ownership/privacy are checked before reads and again
by the existing classifier. Only classified redacted traits enter observation
records; the transient raw map is consumed once and released in this pass.
Aggregate retained raw bytes are capped1MiB; failed/missing/over-budget groups
return unknown, never empty screens or fresh negatives. No automatic fan-out
retry occurs. Generic/psmux backends retain their existing guarded path.

RED public native fixture: three due panes caused3capture clients instead of1.
GREEN:3due panes share1client; at6seconds only1dirtypane adds1client; failed
3pane batch adds1attempt and returnsunknown for all, retaining the prior redacted
positive error. No literal fixture message appears in any observation. Python
3.11/3.12 focused native fixture PASS; cache/tier8tests and existing traits11PASS.
No live source, provider, model, input, focus, size or session effects occurred.

Commands: PYTHONPATH=src /tmp/wake216-py31x/bin/python -m unittest discover -s tests
-p test_tab_error_capture.py; corresponding test_tab_observation*.py and
 test_tab_traits*.py selections. Undefined-name lint and whitespace passed.
This proves the batching invariant, not the final60second installed CPU gate.
