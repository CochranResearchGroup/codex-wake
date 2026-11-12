# LOCAL-P223 native tmux crash diagnosis and repair

Base92c00a0d8495f2d7d386cd7d85cd4f610e8f6ded. Ubuntu tmux3.4-1ubuntu0.2,
buildid9acf9f6bda37b86ea0353d7286f05bfa47610d05. Both production crashes at
21:43:27 and21:50:18 were SIGSEGV at binary offset4ce75. Exact-build debug symbols
map it to control.c:924, an inlined pane-subscription timer helper dereferencing
c->session after it becomes NULL. Current kernel evidence identifies native SIGSEGV; no associated OOM kill.

## Tight native loop and correct regression seam

Private disposable two-session harness: a stalled subscribed control client loses
its attached session. The server crashes and destroys the unrelated survivor.
Repro offset4d521 maps to the same control.c:924 in another inlined copy.
No-subscription control survives; subscription/no-stall control survives. No
formatting writes, systemd or production state are needed for this reproduction.
Only fixture child processes were deliberately paused, never a live client.

`PYTHONPATH=src:tests python -m unittest test_tab_tmux_feed.TmuxFeedTests.test_stalled_client_losing_its_session_cannot_crash_surviving_session -v`

RED on actual production feed code: server crashed, survivor lost (1.648s).
GREEN after removing native wildcard subscriptions. All6feed regressions PASS
4.590s, retaining pane identity, session environment, metadata updates, reconnect,
limits, single-client ownership and cleanup.

## Focused validation and retained failures

`python -m unittest discover -s tests -p 'test_tab*.py' -q`:
264tests in198.759s,261PASS and3failures under heavy host load. The first UID1017
22-test run also retained one late-startup6-second wait failure. Targeted late
socket and lease replay PASS0.641s/0.251s, classified as timing-sensitive, not
silently accepted retries.

Corrected fixture readiness: wait for the shell's exec transition before quiet
lease assertions; wait for an applied monitor cycle before asserting deferred
session settings; late discovery allows two configured whole-cycle budgets
(default10s each), since it is readiness acceptance rather than a latency test.
All formatting, pane, status-interval, command-count and lease assertions retained.

`python -m unittest test_tab_format_autostart test_tab_format_monitor test_tab_tmux_feed -q`:
21PASS13.722s after readiness correction. Broad validation plus focused remediation;
no claim that the initial broad run was all-green. Product patch is unchanged
through this fixture correction. No further broad/review loop.

Pinned ruff0.14.2 undefined-name checks over src/scripts/tests/hooks, compileall,
policy wiring and git diff whitespace checks PASS. Serial primary Standards and
Spec review found no remaining blocking finding. No temporary debug logs added.

## Complete installed package

0.22.0.dev10 wheel SHA256:
3133816f537ff43cbfb7b6d9babc9c733e0e7adb3b6ba41241fb0a1222e6ff92.
Real UID1017 corrected22-regression selection PASS, including the actual-feed
server-survival regression. Installed CLI/stdio/OAuth API controls and prior/new
package rollback/reselection with durable policy/no-dispatch polling PASS. Exact
package/source identity and live quarantine are bound in the installation receipt.
No native tmux/Codex package upgrade, provider call or host reboot. Linux/WSL shared
kernel; no full-suite, Python3.11 or native Windows claim. Hosted CI skipped by
cost policy. Previous package is a byte-exact public-package repack, not its
original wheel. Raw native/process/crash artifacts and first failures stay in the
private incident/qualification directories, outside Git.

## Live containment

Evidence saved before effects. Verified current tmux server was outside the
monitor service's cgroup. Disabled formatting globally; disabled/stopped startup;
restored selected workspace originals with supported rollback, zero failures.
Existing Byobu server retained. Do not re-enable production automation during
this incident. Installation keeps the quarantine; reactivation is a separate
operator decision. Disabled unit is pinned to the fixed package during rollout.
