# Ticket520 automatic formatting validation

Base: bf1f6b5. Delivery: worker branch feat/tab-format-520; no production deployment.

Seams: public ControllerTabs/TabMonitor, native terminal option readback and native
format expansion. The existing monitor accepts trusted sampled observations;
there is no complete reliable terminal trait-event stream, so the default5s
monitor is the fallback. refresh_formatting also accepts trusted event snapshots
without fresh runtime probes. Rendering performs no shell or model work.

Red: `PYTHONPATH=src /home/ecochran76/workspace.local/codex-wake/.venv/bin/python -m unittest discover -s tests -p test_tab_format_monitor.py -q`
failed before implementation: missing expiry module and absent automatic formatting
(`/tmp/p210-520-red.log`).

Green focused: same harness with `-p 'test_tab_format*.py'`:6tests passed.
Monitor regression: `-p 'test_tab_monitor*.py'`:5tests passed. Neither is a full-suite
claim. No retries concealed. `git diff --check` and Python compilation passed.

Installed native expiry: `PYTHONPATH=src /home/ecochran76/workspace.local/codex-wake/.venv/bin/python scripts/tab_format_expiry_acceptance520.py --output docs/dev/evidence/plan0210/520-native-expiry.json`
passed on tmux3.4. Killed/reaped the owned monitor; retained format became STALE
and grey using nativeTclock with no Wake publisher; pane process preserved and
original settings restored. Attached-client screen rendering remains523 scope.

Forty-window isolated tmux measurement: all40 projected within10s budget,6.211s
elapsed. This does not prove a5s refresh cadence for40tabs. The monitor shares a
whole-cycle deadline between observation and formatting, caps128windows/cycle,
reports partial/capacity/deadline results, and uses at most one existing monitor.
Windows supports ordered finite batched read/write to avoid one bridge startup
per window; installed Windows verification is519 and final integration524 scope.

Managed session options: status-interval (positive<=5, preserving faster original)
and @wake-format-clock (%s). Both have durable write-ahead originals and exact
rollback including unset/inherited state. Other styles/options remain untouched.
Automatic application detects changed local styles/session values and yields;
full policy/manual-global-theme semantics belong522.

Memory disposition: forbidden; worker has no memory-write authority.
