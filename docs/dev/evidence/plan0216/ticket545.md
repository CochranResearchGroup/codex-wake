# Ticket545: independent scheduled health and visible-error checks

Owner /root/checks545; branch feat/observer-checks-545; base1d214d0.
No service changes, provider requests, or live captures performed.

Public interfaces: TieredChecks.run/configure/status, ObservationCache.observe and
configure_checks. Host-owned callbacks are external health/capture boundaries;
tests inject time and those boundaries, not private implementation state.

- Health keyed by exact client PID/start/boot, build and account; at least60s
  between background checks per agent, independent of thread changes. Explicit
  observe(explicit_checks=True) bypasses inventory replay/cadence within the
  existing overall deadline and per-probe maximum1s. Disabled tiers stay disabled.
- Errors active/dirty at least5s, inactive fallback at least60s. Error text is
  unconditionally redacted before caching even with a fixture-safe transport.
- Failed/unknown check cannot clear a prior error; last_observation retains only
  attributable classified redacted detail. Fresh absence/resolution clears it.
- All entries bounded1024/default; no per-tab process, raw capture, drafts or
  history retained. Deadline-deferred checks do not consume cadence.
- Activity=False hides dynamic activity but preserves native binding internally
  for independent exact health checks. Health/errors configurable independently.
- Source invalidation clears inventory while preserving exact-agent health
  cadence; a changed birth/build creates a new health key. Source availability
  projection and fair iteration remain lifecycle544 responsibilities.

Red/green commands:
PYTHONPATH=src /tmp/wake216-py312/bin/python -m unittest discover -s tests -p test_tab_observation_checks.py
Initial red: missing module; next red: private fixture message leaked by scheduler;
next red: activity-disabled inventory lost independent health. Each corrected in
its own vertical slice; final3tests PASS Python3.12 and3.11.

Focused checks both Python versions:
- test_tab_observation_checks.py:3 PASS
- test_tab_traits.py:6 PASS
- test_tab_observation.py:3 PASS
Undefined-name lint on changed modules/tests PASS; git diff --check PASS.
CodeGraph initialized in isolated worktree successfully18248nodes59088edges;
index untracked ignored, no shared index edits. Hosted CI skipped by policy.

Limits: about5s error target depends on caller invoking observation for active or
changed panes; inactive unsupported event sources use honest60s fallback. This
packet proves scheduler and public cache behavior; installed aggregate budgets
and source-status integration belong to tickets544/547.
