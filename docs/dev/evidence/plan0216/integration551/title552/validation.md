# Operational formatting pin repair #552

User authorized review/merge/deploy/activation. PR551 merged6f95f90;315installed
members match combined qualified source f19abaa4. Live46tabs/Slate alltiers:
60.189s,2.06017%onecore,46,145,536BownedRSS,freshsnapshot,noformattingfailures.
Nine launchers/completion,sevenaccounts,tenprotectedfiles,24nativeprocesses
preserved. Historical stale-namespace formatting baseline archived privately;
new namespace captured exact preactivation settings. Configure and rollback CLI
attempts refused stale_target while record remained enabled. Two real consecutive
lifecycle snapshots differ only by pane_title. No rejected mutation was blindly
replayed; source race reproduced deterministically on private tmux.

Issue552 is the bounded operational blocker. Red on Python3.12 through canonical
journaled local formatting operations: changing real pane title at every adapter
snapshot caused enable unknown/uncertain/stale_target. Minimal fix removes only
pane_title from formatting-specific target hashes; local formatting pin generation,
status/inspect and dispatch use the same target. Namespace/socket/session,window
roster,all other metadata and process births remain pinned. General lifecycle,
input and retained background formatting/observation hot paths are unchanged.
Golden PID replacement still refuses before rollback; saved baseline staysenabled.

Command: PYTHONPATH=src:tests /tmp/wake216-py{311,312}/bin/python -m unittest
 test_tab_formatting. Four tests PASS each (focused logs). Full selected tab checks PASS on both Python versions (232 tests each; exact
timings in tabs311.log/tabs312.log). Separate-UID exact dev4 installed
regression/surfaces remain pending. New version
0.22.0.dev4 distinguishes this operational fix. The prior resource gate is carried
only for unchanged observer hot paths, not a newly measured dev4 CPU claim.
No additional broad review or original-plan TDD counter reset is performed.

Primary bounded fix review: presentation_target copies snapshot containers without
mutating adapter state and excludes only pane_title. Both target-read and
formatting-dispatch paths use it; local journal admission now resolves that same
format target. All general lifecycle/input pins and exact process birth checks
remain unchanged. The real respawn regression proves refusal before restoration.
No additional source finding remains. Format clients must refresh status/inspect
targets after upgrade. Compileall and diffcheck also pass.
