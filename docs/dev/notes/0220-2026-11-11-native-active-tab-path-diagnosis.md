# Native active-tab wake diagnosis

Scope: [Plan0220](../plans/0220-2026-11-11-native-active-tab-executable.md).
Source base:7af9b29, matching installed0.22.0.dev7 package.
Branch:fix/native-wake-existing-tab-readiness. Primary/root dirty work is preserved.
No commit, publication, working installation change or native submission occurred.

## Feedback loop and minimisation

The installed native adapter's exact-self attachment observation passes from the
interactive process and fails from a transient systemd user service. The read-only
probe calls the actual `_codex_adapter` factory, resolves the existing target,
observes it and asserts `supported('existing_tab', observation)`. It sends nothing.

Command already run: `/var/tmp/auth323-wake-repro` on the incident workstation.
Original result: `existingTabSupported:false`, capability `unavailable`, reason
`active_attachment_unavailable`; assertion ATTACHED_SELF_CANNOT_RECEIVE_EXISTING_TAB_WAKE.
The deterministic loop takes approximately2seconds. Private probe/input/logs and
candidate receipt are retained in the incident's user-scoped `wake-diagnosis`
debug directory, outside Git. It is a diagnosis artifact, not an unattended wake.

Minimisation removed original expiry and resume policy. Removing transport
produced a different unsupported-runtime failure, so transport was restored.
Removing startup policy removed the active-tab check, so it was restored. The
remaining inputs are the exact target thread, endpoint, executable, native
transport and active-tab policy. Interactive and explicit-endpoint controls pass.

## Ranked hypotheses and probes

Before instrumentation: (1) missing executable lookup on service PATH,
(2) missing tmux socket context, (3) different native endpoint discovery,
(4) separate effects-lock contention during cancellation. Each predicted one
specific environment/observation change would alter its symptom.

The service PATH finds tmux but cannot find Codex. Adding only the operator-local
executable directory turns the same installed-code service probe green, without
TMUX or endpoint changes. This confirms hypothesis1's executable-lookup cause.

`CodexRuntimeAdapter.observe` called session inventory with unresolved `unix://`.
That inventory rediscovered the endpoint without the wake's `codex_cmd`, relying
on PATH. Ordinary thread observation already retained the pinned executable.
The discrepancy made an existing exact attachment appear unavailable to the
monitor. Scheduling armed/monitor-ready evidence did not establish delivery.

## Regression and fix

`tests/test_active_tab_executable.py` exercises the real native factory→runtime
observer→session inventory chain. Its synthetic locator refuses PATH discovery
and accepts only the target's pinned executable; metadata attachment evidence is
explicitly synthetic. Before the fix, the pinned-executable case failed and the
explicit-endpoint/unbound controls passed. After the fix, all3 pass in milliseconds.

The fix resolves `unix://` using the target's existing exact Codex executable,
then gives session inventory the resolved endpoint. Explicit endpoints retain
their path; absent/ambiguous attachments remain unavailable. Permission, busy
policy, attempt, queue, replay and acknowledgment semantics are unchanged.

The original full target was replayed read-only under identical systemd context:
installed code remains red (about2.3seconds); source candidate is green (about2.6),
and the built wheel is green (about2.7). All show zero submissions. This proves
the source repair at the observation boundary, not an actual delivered wake turn.

## Cancellation disposition

Live lock inspection identified the scheduler process holding the exact shared
effects lock. The existing cross-process control regression deliberately refuses
cancellation while the effects gate is held, preserves the pending record, then
permits cancellation after release. The24 control tests pass. This explains the
observed EAGAIN without proving a separate stuck-lock defect. No lock was deleted,
shared process killed, gate bypassed or uncertain intent replayed.

## Validation and custody

Local Python3.12, Linux/WSL; no hosted CI. The Python3.11 hosted matrix and actual
native dispatch are not qualified by these checks. Existing websocket deprecation
warnings in session tests remain outside this fix.

- `PYTHONPATH=src python -m unittest discover -s tests -p test_active_tab_executable.py -v`:3 pass after one RED.
- `... -p 'test_native*.py'`:72 pass.
- `... -p 'test_*session*.py'`:76 pass.
- `... -p 'test_*permission*.py'`:50 pass.
- `... -p 'test_wake_control*.py'`:24 pass.
- `... -p test_runtime_policies.py`:8 pass. Total233.
- Pinned Ruff0.14.2 F821/F822/F823 on changed Python, compileall,
  `python scripts/check_policy_wiring.py`, `git diff --check`:PASS.
- `uv build --wheel`:PASS; wheel contains byte-identical repaired runtime source.
- Systemd read-only original-target probe using that wheel:PASS, zero submissions.

The wheel is an unreleased local same-version candidate, retained by content hash
outside Git; it must never overwrite the existing immutable release in place.
Candidate/source hashes and absolute workstation locators are in the private
candidate receipt. Source remains uncommitted in one dedicated linked worktree;
retain it for review/adoption. No unrelated checkout or service was changed.
No DEBUG instrumentation was added to product source. Probes are intentionally
retained in the clearly marked private diagnosis directory for reproducibility.

Remaining acceptance: separately authorized package adoption followed by one exact
self wake that resumes automatically after idle, with actual delivery evidence.
Do not claim that the expired historical intent or earlier missed Deny watch was
repaired retrospectively. Memory disposition is forbidden: no user memory-update
request; zero Graphiti writes under the developer memory policy.

## Explicitly approved installation continuation

The operator subsequently approved installing the candidate and one automatic
exact-self continuation. The prior immutable prefix remains intact. A separate
prefix contains the approved wheel and baseline dependencies with all9 launchers.
The fixed runtime source matches the staged source hash. No native Codex account
daemon binary or private history was changed.

Real Linux test UID1017 qualified isolated candidate launcher/schema/daemon
no-dispatch polling, old-package rollback and candidate reselection, plus all3
attachment regressions. The test user could not directly enter the operator's
private prefix, so only package/dependency code was transferred into its isolated
fixture prefix; no private history or credential state was copied or permissions
weakened. Test Python3.12.3 and working3.12.13 share the host kernel; these checks
do not assert native account-daemon upgrade/history acceptance, which is unchanged.

For working handover,14 enabled registry entries were temporarily admission-held
and all in-flight polls drained. The first pre-switch assertion encountered the
Python shebang argv form, before any launcher/service mutation; it was corrected
to select the existing CLI argument. Then all9 managed launcher links and the
supervisor override selected the candidate. The old supervisor exited cleanly;
new supervisor/children use the new prefix, with zero automatic restarts. All14
registry files were restored byte-for-byte. No uncertain-poll hold or root policy
was bypassed; unrelated native/controller services were not restarted.

The installed service-context observation passes without a PATH workaround. A
new, single exact-self file wake is armed with a ready monitor for acceptance.
It uses the already-live exact thread and existing-tab route, fixed20-minute
expiry and a new synthetic completion marker. Registration/readiness are not
actual delivery evidence. Its original wake ID, checkpoint and rollback/source
receipts are retained in the private automatic-acceptance packet. End the turn
for the monitor to observe idle; qualify actual delivery only on continuation.


## Automatic installed acceptance PASS

The new marker fired and the scheduler observed the exact recipient idle with
active_tab supported. The resumed native turn carries the original wake ID and
native submission marker; fresh record inspection matches both and shows exactly
one submission, route existing_tab, native queue acceptance, and no policy hold.
A scheduler-generated wake event is present on this actual continuation. The
source repair is therefore qualified for this bounded installed automatic wake,
not merely for scheduling or an observation-only probe.

The fixed supervisor remains active with zero automatic restarts. A supported
native reconciliation command returned zero with result skipped; independent acknowledgment and
execution fields still read not_observed. They are not rewritten or inferred
from model receipt. Private verified.json records the distinction between the
observed automatic turn and the separate protocol receipt fields.

No additional wake, Slack send, credential use, approval mutation, shared native
restart or provider operation occurred. Candidate/old prefix, rollback receipts
and dedicated source worktree remain retained. Source is uncommitted/unpublished;
no release declaration or cleanup of unrelated lanes is implied. Plan0220's
operator-approved source/installation/single-continuation scope is complete.

## Authorized PR publication review

The operator requested PR review, merge, deployment and testing. Reconciled
origin/main3f8a18fa, preserving dev7 installation/consolidation provenance.
Standards review against repository policy and Spec review against Plan0220
found no remaining blocker in the bounded fix. The explicit-endpoint and
unbound-recipient controls preserve attachment authority; no retry/dispatch
policy or cancellation lock is weakened.

Pinned Ruff0.14.2 undefined-name checks across src/scripts/tests/hooks, compilation
and policy wiring pass. The earlier233 related checks and one automatic installed
continuation remain qualified. All317 Python source files match the installed
candidate byte-for-byte. A broader whole-suite run is in progress and has reported
failures; its report must be diagnosed before merge. It is not represented as
passing validation. Hosted CI is skipped under operator cost policy.

## Final source publication qualification

Operator authorized PR review, merge, deployment and test. Product code on
74aa5e47 plus the test-only remediatione1a44893 is qualified. Standards and Spec
reviews against main3f8a18fa/Plan0220 found no remaining blocking finding.

The first whole-suite run omitted CI configuration isolation:2432 tests,23
failures/1error, all in refresh fixtures reading the working registry. One-variable
replay: inherited config FAIL, isolated XDG_CONFIG_HOME alone PASS, isolated
XDG_STATE_HOME alone FAIL. All29 refresh tests pass under CI isolation. No
registry or safety guard was changed.

Corrected full command uses isolated XDG_CONFIG_HOME/XDG_STATE_HOME, empty
CODEX_WAKE_STABLE_TIME_CONFIG, PYTHONPATH=src and Python3.12.13 unittest discover
-v -s tests -p test_*.py. Result:2432 total,2430 PASS,1skip and one Grok retention
fixture timeout. Public subprocess/socket reproduction intermittently fails the
terminal assertion after a10s output wait. The multi-megabyte fixture now uses
the documented bounded30s output wait; all event/byte/truncation/identity assertions
are unchanged. Two complete focused reruns PASS (20.165s and11.875s). This is broad
validation plus focused remediation, not a claimed single all-green broad run.
Aggregate qualification:2431 PASS,1 retained skip, no unresolved test failure.
No third broad rerun is needed for this test-only wait change; product code did
not change. Logs/digests and qualification receipt are retained privately.

The three new active-tab regressions also PASS on Python3.11.15; the whole3.11
suite was not run. Pinned Ruff, compilation and policy wiring PASS. Hosted CI
was skipped under operator cost policy. Parked OpenClaw plugin work/tests were
not resumed. No native account-daemon upgrade or Windows acceptance is claimed.

All317 Python source files and9 managed launchers match the installed candidate;
supervisor active with zero automatic restarts. Previous automatic continuation
and matching original native submission remain the bounded delivery evidence.
Independent native acknowledgment/execution fields remain not_observed. Source
publication binds the existing qualified package; no second wake, Slack resend,
vault use, approval mutation or provider action is needed. Old package, rollback
receipts and source history remain retained. Memory disposition forbidden under
the explicit-request boundary; zero Graphiti writes.
