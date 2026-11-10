# Monitor CLI uncertain/null readout repair

The installed diagnostic stop effect succeeded but its response journal retained
an uncertain operation with null result. The new human renderer dereferenced that
null and printed a traceback. This packet changes only the CLI presentation
adapter plus its public regression; no monitor lifecycle behavior changes.

A named public CLI regression uses the real retained-operation journal and a
ControllerTabs adapter that loses its response after stop. Before the fix it
reproduces AttributeError in render_status on the null operation result. After
the fix the human readout says the operation is uncertain and points to
`tabs monitor-status --json`. The exact same retained request in JSON mode still
returns the original null result and uncertain phase. Both modes retain exit3;
the renderer does not claim that uncertainty proves a stopped or running state.

The adapter passes only an actual monitor-status payload to the detailed status
renderer. Missing results and partial/uncertain/held operations use a concise
operation readout. JSON output and exit-status implementation are unchanged.

Validation: PYTHONPATH=src:tests /tmp/wake216-py312/bin/python -m unittest
test_tab_monitor_presentation, equivalent py311 command; one regression passes on
each. Ruff F821/F822/F823 on changed files and git diff --check pass.

Memory disposition: forbidden; no explicit memory-write request.
