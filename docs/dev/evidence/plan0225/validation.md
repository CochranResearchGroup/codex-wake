# LOCAL-P225 validation and review

Base: `34194dbf7cc2fe54c44f9c6e8c7997ef22c52797` (fetched origin/main).
Candidate: this branch's five Python member changes plus tests/docs. The source
commit is recorded in the plan's closeout after the implementation checkpoint.

Private qualification prefix:
`~/.local/state/codex-wake/qualification/actionable-cli-output/`.
`PY` below is its `venv/bin/python` (Python3.12); `PY311` is `venv311/bin/python`.
Both were created with the respective `python3.12/3.11 -m venv`, then installed
using `-m pip install -e '.[dev]'` (3.12) or `-m pip install -e .` (3.11).

## Red to green

Commands use `PYTHONPATH=src:tests $PY -m unittest` followed by each selector:

- `test_tab_format_policy.WorkspacePolicyTests.test_explicit_enable_restores_workspace_preference_and_keeps_rollback`:
  RED disabled instead of applied; GREEN1/0.535s. Initial system Python setup
  lacked msgspec; the private declared-dependency environment corrected setup
  before the actual red reproduction.
- `test_tab_format_policy.WorkspacePolicyTests.test_global_optout_dominates_workspace_override_and_inspection_keeps_details`:
  RED missing reason; GREEN workspace policy selection6/1.696s.
- `test_tab_format_cli_status.FormattingCLIStatusTests.test_global_optout_explains_block_and_lookup_preserves_nonzero_outcome`:
  RED initial command/lookup returned0 and printed journal metadata; GREEN with
  existing presentation checks6/5.884s.
- `test_tab_result`: RED10 failing subcases (unsupported/direct disabled/stale
  outcomes and blocked pause); GREEN1/0.001s.
- `test_cli_presentation.CLIPresentationTests.test_tab_summaries_defer_to_failure_details_for_partial_payloads`:
  RED session/monitor summaries hid partial outcomes; GREEN combined presentation,
  monitor and summary selection9/2.835s.
- `test_tab_format_cli_status.FormattingCLIStatusTests.test_status_summarizes_state_and_inspect_keeps_native_options`:
  RED raw inspection dump; GREEN1/1.720s.

## Final source and package checks

Focused selection:
`test_tab_format_policy test_tab_format_cli_status test_tab_result test_cli_presentation test_tab_monitor_presentation test_terminal_session_summary test_tab_contract test_tab_format_scope test_tab_formatting test_tab_format_autostart test_tab_format_monitor test_terminal_session_cli test_tab_reattach_public test_tab_profile_create`.

- `PYTHONPATH=src:tests $PY -m unittest <focused selection>`:67 PASS/39.175s.
- `PYTHONPATH=src:tests $PY311 -m unittest <focused selection>`:67 PASS/65.289s,
  log `python311.log`. This includes the review corrections to preference
  persistence and error presentation precedence.
- `PYTHONPATH=src:tests $PY -m unittest discover -s tests -p 'test_tab_*.py'`:
  269 tests/172.471s,268 PASS and one inherited cadence failure; full original
  output retained in `python312-tabs.log`. No retries overwrite that result.
- Final 3.12 non-tab presentation selection:
  `PYTHONPATH=src:tests $PY -m unittest test_cli_presentation test_tab_monitor_presentation test_terminal_session_summary`:
  9 PASS/2.271s, log `python312-presentation.log`.
- `$PY -m pip wheel . --no-deps -w <prefix>/dist`: PASS. Wheel SHA256
  `76b9c4edf7ec51d7dc25f59b42f91c4ba3f8e82341ea5583582d300afac7d47f`.
  Installed in private `installed/` venv using its Python's `-m pip install WHEEL`.
- `PYTHONPATH=tests <prefix>/installed/bin/python -m unittest test_tab_format_cli_status test_cli_presentation test_tab_result`:
  10 PASS/9.899s, log `installed-tests.log`. Public subprocesses use the installed
  entrypoint module, not candidate source imports.
- `$PY -m ruff check --select F821,F822,F823 src scripts tests .codex/hooks`: PASS.
- `$PY -m compileall -q src tests .codex/hooks`: PASS.
- `$PY scripts/check_policy_wiring.py`: PASS.
- `$PY scripts/generate_command_reference.py --check`: PASS.
- `git diff --check`: PASS.

## Inherited failures and limits

The expanded suite's failure is
`test_tab_monitor_publication.MonitorPublicationTests.test_quiet_owner_keeps_tick_cadence_until_longer_snapshot_heartbeat`:
its nine-second heartbeat observation deadline expires. The identical test also
fails on the unchanged installed0.22.0.dev11-32eb90f package (1/9.205s), log
`cadence-installed-baseline.log`. Byte comparison of every package Python member
finds only this patch's five changed members; monitor/observer/publication code
and this test are unchanged. This is an inherited failure, not a clean full-suite
pass or a pass-on-retry. No timing threshold was weakened and monitor work remains
under its existing plan. The 172.471s expanded run stays inside the180s presubmit
bound; the3.11 selection exceeds the60s feedback target but stays inside presubmit.

Active planning audit command:
`$PY /home/ecochran76/.codex/shared/skills/repo-policy-selector/scripts/audit_planning_contract.py --repo-root . --active-only --json`.
The audit reports only two inherited deterministic-state findings in P220/P224;
their combined `State: CLOSED. Owner: ...` headers are already present in the base
and untouched.20 historical findings remain explicitly accepted by the existing
baseline, with0unused baseline entries. `planning-initial.json` preserves the
full initial report. P225 introduces no finding. These are reported gaps rather
than a claim that the repository planning audit is clean.

Hosted CI runs:0. Applicable local checks substitute for hosted CI. Differences:
local Cooper Linux/shared host, isolated Python3.11/3.12 venvs and disposable tmux;
no GitHub Ubuntu runner, full repository/native/provider/legacy-package matrix,
Windows rendering or live formatting reactivation. Existing WebSockets warnings
remain warnings. No OpenClaw work, production monitor/service change or install.

## Standards review

Primary serial review of `git diff 34194dbf -- src tests docs/agents` against
AGENTS and policies0003/0005/0006/0016/0021; no independent-review claim.
No unresolved documented-standard violation. Kept existing owners, target fences,
baseline custody and explicit JSON behavior. No new CLI or parallel renderer
framework. Root checkout's unrelated work is preserved.

## Spec review

Compared against LOCAL-P225 acceptance and the user's original disabled-enable
example. Two review findings accepted and remediated: persist the explicit
workspace preference even when a subsequent manual-style hold stops application;
keep top-level error presentation ahead of retained summaries. Disabled output
also omits irrelevant preference dumps and explicitly requires a fresh intent
after fixing policy. Final focused/installed checks cover the affected seams.
No outstanding source-acceptance blocker; global opt-out and live installation
remain separate. Accepted findings: Standards0; Spec2, both corrected.
