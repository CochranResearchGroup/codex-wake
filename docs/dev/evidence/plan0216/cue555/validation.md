# Compact status cue spacing #555

Operator requested a color-coded single character without surrounding padding.
Named palettes now concatenate type badge and cue, with no separator before the
native name when a cue exists. Compact fallback uses the same spacing. Existing
idle separation, state colors, selected styling, leases and original baselines
remain intact. Example CX+ * name becomes CX+*name.

Focused affected selection: PYTHONPATH=src:tests /tmp/wake216-py{311,312}/bin/python
-m unittest test_tab_format_compact test_tab_format_presets
 test_tab_format_projection test_tab_format_rendering test_tab_format_monitor.
37PASSbothPython (6.543s/6.640s), no retries. Existing compact expected output
updated; no new test framework or exhaustive matrix. DiffcheckPASS. This is a
small reversible renderer edit; prior observer resource qualification is not rerun.
Exact installed palette/native rollback checks precede cutover. HostedCIzero.
