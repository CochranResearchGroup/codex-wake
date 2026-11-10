# Ticket546 durable checkpoint cost

Bounded delegated performance repair from de2346d30e8b564a0266ed417550ed9edb7bcc2a; product commit46405a84. No broad review or post-review remediation was run.

The steady active profile attributed18 formatting state saves in10 ticks, including JSON serialization of the363KB state. `TabFormatting.apply` saved before every pending native write although its existing originals were already durable. It now retains the prewrite checkpoint whenever any original was newly captured; updates with existing originals retain the final checkpoint only. Native custody checks, lease sequencing, manual override holds and rollback are unchanged.

Public seam: `refresh_formatting` against disposable real tmux; the existing two-dirty-window test additionally counts operating-system fsync calls. Red command: `PYTHONPATH=src:tests /tmp/wake216-py311/bin/python -m unittest test_tab_format_process_budget.FormattingProcessBudgetTests.test_two_dirty_windows_share_native_batches_and_keep_current_lease` failed with2 fsync calls vs allowed1. Identical green command passed in.218s after the fix. It also verifies two native RUN projections, unchanged lease, selective PID reads, native process budget and successful rollback.

Focused validation commands: `PYTHONPATH=src:tests /tmp/wake216-py311/bin/python -m unittest discover -s tests -p 'test_tab_format*.py'` PASS70 tests18.957s; the same command with `/tmp/wake216-py312/bin/python` PASS70 tests18.500s. Full logs `/tmp/checkpoint546-py311.log` and `/tmp/checkpoint546-py312.log`. `git diff --check` passed. Native tmux3.4, Python3.11.15 and3.12.13; local checks only, no hostedCI.

Observed improvement is one fewer atomic durable state write for this dirty refresh. These focused checks do not establish the100-tab CPU acceptance gate; combined exact-source qualification remains with the primary owner and ticket547. No production installation or service effect. Memory disposition remains with primary closeout; no memory writes attempted in this lane.
