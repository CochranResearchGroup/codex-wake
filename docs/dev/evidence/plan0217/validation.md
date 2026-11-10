# LOCAL-P217 validation

Source: `main` at `fa2363c24bf921ecf0bd8390739e96041e620e8f` plus
uncommitted P217 CLI presentation patch. Preexisting completion installer/docs,
config, glossary and Plan0216 work are separate and preserved.

## Behavior and regression evidence

- Public CLI red: `test_cli_presentation` initially failed because unflagged
  `accounts list` printed the JSON envelope. After implementation, five checks
  pass for readable redirected output, explicit JSON metadata, empty/error output,
  account details, nested history/owner visibility, and structured protocol errors
  (five tests total; the final test has three protocol subtests).
- Shared renderer owns text formatting; adapters retain operation execution,
  exceptions, authorization and exit codes. Existing specialized human views and
  explicit streams/frames are preserved.
- Combined focused selection: 327 tests passed in 60.732s. Command was
  `PYTHONPATH=src:tests uv run --no-project --with 'websockets>=17,<18' --with 'dbus-next>=0.2.3,<0.3' --with 'jsonschema>=4.26,<5' python -m unittest` followed by the affected controller/account/history/agent/job/tab/output modules (selection retained in the session tool record; log `/tmp/codex-wake-p217-final-focused.log`).
- Additional compatibility selection: 69 tests passed in 18.999s, log
  `/tmp/codex-wake-p217-consumers.log`. Existing machine consumers now explicitly
  select JSON without changing their assertions or mutation/authority arguments.
- Initial 247-test selection had 17 JSON-decoding errors in consumers relying on
  unflagged output; initial expanded 75-test selection had three more. These
  were deterministic output-contract migration failures, corrected with explicit
  JSON selection. No test expectation was weakened; these were not flaky retries.
- Independent review `/root/presentation_review` completed one bounded review.
  Standards: no separate violation. Spec: accepted findings for SSH errors,
  nested history content and explicit stream diagnostics. All three corrected;
  public CLI/formatter regressions and private installed checks pass.
- Worker `/root/output_audit` completed read-only audit, bounded test/script
  migrations and focused checks. Primary reconciled changes to explicit output
  flags only; no live acceptance scripts executed.

## Local checks

`uvx --from ruff==0.14.2 ruff check --select F821,F822,F823 src scripts tests .codex/hooks`,
`python -m compileall -q src scripts tests`, `python scripts/check_policy_wiring.py`,
dependency-qualified `python scripts/generate_command_reference.py --check`, and
`git diff --check` passed. Initial `python -m ruff` through an ephemeral `uv run`
environment failed to locate its binary; direct pinned `uvx` invocation passed.

Local Linux/Python 3.12.13 checks substitute for hosted CI under the cost policy.
Hosted Python 3.11 matrix, optional live/provider/native-daemon qualification,
and Windows execution were not run. Existing WebSockets deprecation warnings
remain; they do not represent a test failure. No timing budget is defined for
this specific output selection; measured focused/compatibility durations are above.

## Private installation

`uv build --wheel --out-dir /tmp/codex-wake-p217.Gz2NE8/dist`, isolated `uv venv`
and `uv pip install` produced a private installation. Public console-entrypoint
checks verified readable account list, full JSON generation metadata and fresh
Zsh/Bash completion in synthetic homes. Installed five presentation regression
tests passed in 1.686s. No provider, production account, daemon, monitor or native
build was changed. Working launcher still points to the existing
`/home/ecochran76/.local/share/codex-wake/releases/0.22.0.dev2-7010cbe` package.
Source/wheel/installed Python-member hashes and final wheel SHA256 are recorded
in the user-scoped qualification receipt; temporary prefix is a test environment,
not production deployment. These are unreleased source changes.

## Comprehensive result and final corrections

Local full Python discovery used isolated `XDG_CONFIG_HOME`/`XDG_STATE_HOME`,
empty `CODEX_WAKE_STABLE_TIME_CONFIG`, `PYTHONPATH=src` and the same dependency-qualified
`uv run --no-project` invocation with `--with 'mcp>=2.2,<2.3'`, followed by
`python -m unittest discover -s tests -p 'test_*.py' -q`. It ran 2338 tests in
555.834s, one skip, with 20 errors and two failures. This first run is retained;
it is not reported as a passing full suite.

Most failures were previously loaded machine-consumer tests whose flag fixes
landed while discovery was running. Three additional consumers (frontier attention,
harness callers, release driver) needed explicit JSON; all 12 checks in those
modules then passed in 2.102s. One planning test exposed preexisting OPEN Plan0214
missing its required Current State heading. Added a source-grounded status section
without closing that plan, changing runtime claims or enabling its monitor.

Final corrective run: `python -m unittest test_command_workflows
test_frontier_attention_callers test_harness_callers test_release_driver
test_tab_contract test_tab_format_autostart test_tab_format_cli_status
test_tab_format_policy test_tab_formatting test_tab_format_presets
test_tab_format_process_budget test_tab_reattach_public test_local_validation -q`
under the dependency-qualified source environment passed all 64 tests in 24.129s.
Every full-discovery failure is covered by that passing corrected selection.
Full discovery was not repeated after deterministic consumer/header repairs.
Active-only planning audit now reports `ok: true`, no problems; no baseline waiver
was added. Earlier receipts/logs remain preserved.

Final private wheel SHA256:
`42cab43f56f7887e595890a6f13556bfaf1a9b19c2120c4f6d36e1e4ba6b7bdc`.
All 305 source/wheel/installed Python members match. Durable machine receipt,
build/install logs and test logs are under
`~/.local/state/codex-wake/qualification/plan0217-20261110/`.
Memory disposition: `forbidden`; session developer instructions allow memory
updates only on explicit user request. No memory write was attempted.
