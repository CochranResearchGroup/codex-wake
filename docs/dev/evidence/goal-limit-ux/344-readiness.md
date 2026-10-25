# #344 watcher readiness implementation evidence

Source branch: feat/goal-limit-ux-implementation; integration base37a5cbb,
prerequisite16c2501. Primary owns shared controller/CLI/MCP hooks.

Public seam: enroll/show plus real independent watch loop and actual owned Unix
native protocol fixture. First-poll acknowledgement binds receipt generation,
enrollment revision and independent controller generation. Only observations from
the completed poll can be acknowledged; concurrent changed enrollment is excluded.
Duplicate enrollment preserves revision, counters and deadline. Readiness removes
engagement on process death, stale heartbeat/sample or changed watcher generation.

Red: `PYTHONPATH=src:tests .venv/bin/python -m unittest test_goal_engagement -v`
failed missing engagement; green same command after implementation passed2 cases.
Added public CLI/native diagnosis agreement and missing-history non-enrollment proof.
`PYTHONPATH=src:tests .venv/bin/python -m unittest test_goal_engagement -q` passed4.

Watcher service seam: configured systemd command/readback through injected runner.
Masked/wrong-root refusal, authenticated start without engagement claim, distinct
watcher-start authority. Red `test_goal_watcher` failed missing module; green3pass.
Separate-standing-permission regression red failed because enrollment permission
incorrectly allowed model start; green after separate action4pass.

Regression selections:46 original supervision/maintenance plus new engagement
cases passed in60.076s; later60 mixed supervision/maintenance/permissions/CLI/
engagement/watcher tests passed52.479s.16 session-permission/watcher tests passed
3.334s. Undefined-name lint, policy wiring and diff checks passed.

Runtime/native/frontend presentation remains a separate required acceptance gate.
No #344 closure, installed UX, rendered startup, production service start/unmask,
or resource renewal is claimed by these tests. Manual resource monitoring is
operator-authorized; service remains masked.
