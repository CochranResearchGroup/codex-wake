# R2 accepted Spec finding — review 1 / TDD remediation pass 1

Source base: `2e8896b`; branch `fix/session-review-summary`.
Ticket: CodexWake526; accepted finding R2, P2. No additional review conducted.

Public seam: `ControllerTabs.execute('tabs.session.list', {})` and human CLI
`render`. Existing `TabMonitor.refresh` harness injects the external probe and
clock; listing reads only the resulting cached snapshot. The native transport
snapshot is the existing session-inventory read; no extra native, provider,
model or monitor-refresh probe is added for summaries. No production monitor,
Windows job, installation, tracker write or memory write was performed.

Focused commands (both interpreters use this source via `PYTHONPATH=src`):

- `PYTHONPATH=src /tmp/codex-wake-p210-py312/bin/python -m unittest discover -s tests -p test_terminal_session_summary.py`
- `PYTHONPATH=src /tmp/codex-wake-p210-py311/bin/python -m unittest discover -s tests -p test_terminal_session_summary.py`

Red: both failed with `KeyError: 'health_summary'` before implementation.
Green: both passed the first fresh-cache/CLI scenario. The next vertical
identity case failed on both: replacement-container health was incorrectly
`{'responsive': 1}` rather than `{'unknown': 1}`. After binding cached target
generation to the current snapshot, both passed. Final focused selection:
2 tests passed on Python 3.12 (0.018s) and 3.11 (0.026s).

Harness corrections retained here: the initial command omitted `PYTHONPATH=src`
and could not import the new CLI module from the installed package; a later
incorrect digest import also failed collection. Neither is counted as a
behavior red. Corrected runs above observed the actual defects.

Adjacent focused regression, once per interpreter:

- `PYTHONPATH=src /tmp/codex-wake-p210-py312/bin/python -m unittest discover -s tests -p 'test_terminal_session*.py'` — 24 passed, 11.840s.
- `PYTHONPATH=src /tmp/codex-wake-p210-py311/bin/python -m unittest discover -s tests -p 'test_terminal_session*.py'` — 24 passed, 12.244s.
- `git diff --check` — passed.

The adjacent selection preceded addition of the second empty/no-monitor-state
case; the final focused runs include that case. Fresh known health, activity
and visible-error counts render together; expired observations become unknown
with stale freshness. Unobserved and empty destinations remain visible. Native
replacement cannot inherit observations based solely on an enrolled alias.
Derived summaries are excluded from registry persistence. Existing unavailable
session rows retain unavailable freshness and unknown tab count.

Hosted GitHub CI skipped per operator cost policy. This is a focused local
source validation, not a full-suite, installed-runtime or provider acceptance
claim. CodeGraph was unavailable in this worktree (no index); direct source
inspection supplied the bounded discovery fallback.

Memory disposition: forbidden — parent explicitly prohibited memory writes
for this bounded remediation pass; root owns the substantive closeout.
