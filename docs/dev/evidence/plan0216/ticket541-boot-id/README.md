# Ticket541 host boot identity read budget

Source base: de2346d30e8b564a0266ed417550ed9edb7bcc2a.
Focused development selection, no hosted CI or production effects.

`PYTHONPATH=src /tmp/wake216-py312/bin/python -m unittest discover -s tests -p test_process.py`

Red: 10 boot-ID filesystem opens for 10 identity queries; expected at most one.
Green: four tests pass on Python3.11.15 and3.12.13. Every identity still reads
its current PID stat; only the real host `/proc` boot identifier is cached after
successful nonempty retrieval. A Linux process cannot survive a reboot. Alternate
proc roots remain uncached and a changed fixture boot ID is observed immediately.

`PYTHONPATH=src /tmp/wake216-py312/bin/python -m unittest discover -s tests -p 'test_tab_observation*.py'`

Both interpreters: eight pass, including live child-spawn detection before cache
expiry and changed-birth invalidation. No retry or test exclusions.

Boundary microbenchmark: five samples of10000 real same-process
`process_identity(os.getpid())` calls, `time.process_time()` CPU denominator.
Median before0.513190265s, after0.245616045s (~52% reduction). This is a narrow
identity-cost diagnostic, not100-tab monitor acceptance or an acceptance estimate.
Raw samples in before.json and after.json; exact loop performs10000 calls inside
five timed samples after importing `process_identity`.
