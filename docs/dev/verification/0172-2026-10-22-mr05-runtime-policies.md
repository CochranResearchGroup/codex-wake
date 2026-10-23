# MR-05 runtime policy source packet

Work item: CW-MR-172/MR-05. Worker `/root/mr05`; primary `/root` owns
reconciliation, shared CLI/MCP integration and acceptance. Branch
`feat/mr05-runtime-policies`, base `36412c4`; dedicated worktree
`/home/ecochran76/workspace.local/codex-wake-mr05`. No push/merge, installation,
service/grant changes or live/provider input was performed.

## Source behavior and compatibility

`RuntimeAdapter.resolve/observe/submit/reconcile` signatures stay unchanged.
`RuntimeSubmission.pre_io` defaults false and only positive adapter evidence can
set it. Constructor policy selection is optional and defaults wait. Both built-in
adapters refuse queue/interrupt before host effects: dequeue expiry and owned-turn
cancellation remain unqualified. Grok CLI accepts those selections and refuses
before host lookup/retention. Primary owns equivalent native CLI and MCP wiring.

Operator-only `grok bind --allow-terminal-input --allow-terminal-fallback` enables
a frozen host binding profile. It selects `native_preferred`; Grok1.0.40 has no
qualified native exact-open route, so native unavailability is definitive before
any native submission I/O. Only this outcome, with both host permissions, may
select the existing qualified terminal route. Ordinary bindings retain the
original direct terminal route. This does not qualify Codex terminal input.
The new method remains runtime envelope1/schema7; older validators reject the
unknown method and hold rather than dispatch it. Original target, profile digest,
deadline and durable submission marker remain retained.

The reusable fallback seam returns the original accepted/uncertain outcome or
missing pre-I/O proof unchanged. It never treats missing reconciliation evidence
as not-sent. Core uncertain recovery reconciles the original marker without
replaying or switching. Terminal outcomes retain `terminal_observation` and
`execution=not_observed`; no receiver/work claim is manufactured. Existing locked
process/session/version/composer/deadline checks still guard fallback input.

## Focused evidence

TDD public seams: adapter submission, CLI admission, CLI→durable daemon dispatch.
New `tests/test_runtime_policies.py` protects pre-effect policy refusal, profile
admission, strict native-unavailable/pre-I/O evidence, weak observed evidence,
protected composer/process/session/version and uncertain no-replay recovery.

Red: `PYTHONPATH=src python -m unittest discover -s tests -p test_runtime_policies.py`
first failed on absent `busy_policy` constructor (3 subcase errors). Subsequent
vertical fallback cycle failed on missing runtime_policies module, then preferred
route cycle failed on absent `preferred_method` constructor. Each passed after
its implementation. Initial Grok regression using system Python had 2 errors
because jsonschema was unavailable; no package was installed.

Final focused interpreter: `/home/ecochran76/workspace.local/codex-wake/.venv/bin/python`,
`PYTHONPATH=src`, unittest discovery:

- `-p test_runtime_policies.py`: 7 PASS (0.197s).
- `-p test_grok_runtime.py`: 9 PASS (0.944s).
- `-p test_native_delivery.py`: initial 15 tests had 2 failures, submitted0 vs1
  in persisted-due and explicit-resume cases. Exact base36412c4 archived into a
  temporary tree reproduces the same failures (scheduling_time_unavailable).
  Primary-requested isolation (`CODEX_WAKE_STABLE_TIME_CONFIG=''`, temporary
  `XDG_CONFIG_HOME`/`XDG_STATE_HOME`) passes all15 in0.415s. No tests or production
  time guards were changed to conceal those environmental failures.
- `git diff --check`: PASS.
- F821/F822/F823 lint attempted with that interpreter: unavailable (`No module
  named ruff`); primary validation environment must run this check.

Full conservative suite, isolated artifact, shared caller integration, installed
and live acceptance are unexecuted here. The old probe authority was consumed;
this source packet supplies no new live authorization. MR-06 remains a distinct
acceptance gate.

Memory disposition: `not_durable` for this intermediate delegated handoff; primary
must qualify and record the reconciled outcome once rather than persisting a
worker's unaccepted implementation as a project decision.
