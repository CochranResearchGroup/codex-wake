# Formatting after terminal server replacement

State: CLOSED
Owner: primary / ecochran76
Work item: LOCAL-P221
Priority: bug
Branch: fix/tab-format-reboot
Target: origin/main
Base: 95bbebb308d22eb81b9909717ed61358d16095e5

## Current State

CLOSED: PR582 merged4dfd8b08; exact0.22.0.dev8 installed after real UID1017
qualification. All319 package members and9 launchers match the merged package.
Working45tabs have zero native-option mismatches; new monitor is fresh with
settings preserved. All29 native generations,10 protected files and the supervisor
PID are unchanged. Prior prefix and supported rollback helper remain retained.
See [deployment receipt](../evidence/plan0221/deployment.json).

The original diagnosis used LOCAL-P221 because external mutation had not yet
been requested; the later PR/review/merge/install instruction authorized rollout.

## Scope and acceptance

Explicit enable must work after namespace replacement, preserve old originals,
and capture new originals before writes. Status explains stale custody without
mutating it. Rollback/resume/reenable and automatic refresh retain identity fences.
Revisiting an old namespace must reuse its original baseline. Prove rollback uses
the new server's originals and unrelated terminal settings/pane identity survive.

## Execution and boundaries

One serial primary lane: red public controller/tmux test, smallest fix, focused
format/controller regression, isolated CLI/package acceptance, local validation.
No independent agent lane is needed for this tightly coupled fix. No provider,
working install, dispatch, service restart or unrelated dirty-file changes.
At most one diagnosis/remediation pass; stop for a concrete unprotected seam
or unresolved baseline-custody failure. Retain this checkout until source review
and commit custody; review cleanup at source-validation closeout.

## Hypotheses and evidence

1. Persisted namespace baseline fence blocks explicit enable: fresh transport
   still raises stale_target after real server replacement (confirmed).
2. Old transport alone: initial harness raised workspace_changed; recreating
   transport reproduces the reported stale_target instead (ruled out).
3. Monitor interference: no monitor exists in the minimal reproducer (ruled out).

## Definition of done

Regression red before green; original restart loop green; old/new baseline
custody and rollback proven; local checks recorded with source commit and limits.
Source completion, publication and installed activation are separate boundaries.

## Validation result

100 formatting tests and34 related controller/target tests PASS on Python3.12.13;
CI scope test PASS, repository undefined-name lint, compile, policy wiring and
whitespace checks PASS. Packaged CLI restart/enable/monitor/rollback fixture PASS.
Initial plain-Python probe lacked msgspec; installed dependency environment fixed
that setup issue. Initial same-socket test setup hit a tmux shutdown race; use a
new disposable socket for deterministic permanent regression. An attempted
related selection named nonexistent test_stable_tab_operations; corrected to
actual test_controller_tabs/test_tab_targets/test_tab_targets_mcp, all34 PASS.
No test assertion was weakened. No comprehensive-suite, Python3.11 or native
Windows runtime claim. No deployment or provider mutation. Hosted CI skipped by
cost policy; local tests use Linux/WSL and existing candidate dependencies.

Three maintained controller regressions protect: server replacement and rollback,
read-only stale inspection plus old-intent/refresh fences, and returning namespace
plus retained-alias custody. CLI/package fixture additionally exercises the common
journal and monitor startup. No DEBUG instrumentation remains.

## Custody

Primary owns this isolated source-review checkout, created because main has
unrelated dirty work and is behind origin/main. No earlier lane was repurposed.
Registered inventory before creation116;117 after creation. Others' registrations
(including stale entries) are outside this task's cleanup scope. Retain this one
until review/integration; next review point is the integration decision. No remote
source publication or merge authority was inferred from the diagnosis request.

Exact commands, source commit, wheel identity and limitations: [validation](../evidence/plan0221/validation.md).

## Publication and installation authorization

Operator requested PR, review, merge and install on2026-11-11. This supersedes
this plan's earlier source-only boundary for the bounded P221 fix. Publish and
self-review against base95bbebb3; local validation replaces hosted CI. Release
0.22.0.dev8 from the exact merged commit, qualify that package as UID1017, retain
the prior prefix and rollback links, then select the new CLI and formatting
monitor. No native Codex binary/account-daemon upgrade or prompt dispatch.
Existing supervisor and native services retain their identities.

Standards review: no blocking documented-standard or baseline-smell finding.
Spec review: no blocking finding; explicit intent, namespace originals, alias
custody and old-intent/refresh fences satisfy LOCAL-P221. Schema change is additive
and documented. Serial primary review is proportionate for this26-line owner fix.

## Installed acceptance and cleanup

Release revision5f6f87c4 passed100 formatting tests (70.789s) and34 related tests
(12.392s), plus pinned repository lint, compilation and policy wiring. Standards
and Spec primary reviews found no blocking findings. PR582 merged4dfd8b08.

Exact wheel SHA256da11770ce8620dce2fc901157226f41030298abe69bac484082a6b466844993f.
Real UID1017 installed the complete candidate and prior public package, passed
7regressions and actual CLI/stdio/OAuth API acceptance, then verified
prior→candidate→prior→candidate launcher selection with durable policy and
no-dispatch daemon polling. All319 package members match merged source and both
installs. Test Python3.12.3 and working3.12.13 share the Linux kernel. This is a
Python Wake package change, not a native account-daemon binary upgrade; no new
native-history/provider acceptance is claimed. Initial sudo-root install commands
were denied and an inherited inaccessible cwd prevented uv setup; using the
already authorized UID1017 from /tmp resolved setup without changing permissions.

Working CLI links and completion now select the new immutable prefix. Supported
monitor stop/start selected the new code with exactly preserved settings; old
monitor exited. Supervisor/native services were not restarted. Fresh OS readback
verified29 native process generations unchanged, zero option mismatches across
45tabs, active supervisor with zero restarts. No model/provider request was made.

Private qualification, hashes, original links, cutover and rollback commands are
retained under user-scoped qualification/plan0221. Task checkout will be removed
after this documentation checkpoint has merged and remote custody is verified;
117 registered entries before cleanup,116 expected after, other entries untouched.
Memory disposition forbidden under the explicit memory-update request boundary;
no memory write is part of this publication/installation request.
