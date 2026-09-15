# Local runtime wake productization

State: OPEN
Lane: P51-C4
Issue: #62
Branch: `feat/issue-62-runtime-wake-productization`
Target: `main`
Integration: `squash`

## Objective

Expose the accepted process-exit and user-systemd transition sources through
the supported readiness, status, support, documentation, packaging, and
provider-free lifecycle surfaces without changing their frozen identity,
authorization, observation, occurrence, or dispatch contracts.

## Current state

Process lane #60 is accepted through PR #71 at canonical commit
`54311f35f9e3b6dd0c21be3d0beaa2eb443616a3`. Systemd lane #61 is accepted
through PR #73 at canonical commit
`f41ef0ba6d5b37ab85bea7a1cebbc9bd6b0ad748`. This join is implemented and
reviewed at checkpoint `44244785cfa123a3d234989f23b2dae4201a9dca`.
Readiness, status, support, documentation, and the installed-wheel fixture are
integration-ready; GitHub CI and canonical-main integration remain.

## Scope and write surface

- Central source-health projection and bounded support redaction in
  `src/codex_wake/signal_support.py` and focused tests.
- Supported aggregate status integration in `src/codex_wake/cli.py` and CLI
  tests. Doctor and product-readiness continue to consume the shared
  `signal_readiness` projection.
- Operator documentation and CLI help for the exact `process-exit` and
  `systemd-unit becomes` recipes, their evidence, limits, recovery semantics,
  and excluded authority.
- A disposable installed-wheel lifecycle smoke that uses injected fixed process
  and session-manager observation boundaries. It may register, reconstruct,
  observe, match, retire, and clean records, but must not dispatch or touch the
  normal installed runtime.
- Packaging, comprehensive Python, plugin, compilation, planning, and CI
  validation.

Any change to the runtime-source schema, adapter identity, authorization,
occurrence, journal, dispatch, production observer call plan, or source
configuration contract stops for a separately reviewed correction.

## Readiness and privacy contract

- Project each active runtime source as exactly one of `ready`, `unavailable`,
  `invalidated`, or `unsupported`; `unobserved` remains an honest pre-readiness
  state and must never be promoted to ready from a stale or aggregate receipt.
- Exact instance health may establish readiness. Missing or aggregate-only
  health may warn or block but cannot establish an instance-ready claim.
- Process boot/PID/start-tick/owner identity and raw systemd unit names are not
  emitted by aggregate status or support export. Stable bounded fingerprints,
  source kind, state class, counts, and allowlisted diagnostic codes are the
  support identities.
- Prompt bodies, target secrets, process command/environment data, raw D-Bus
  payloads, arbitrary properties, and provider credentials remain excluded.
- Dispatch readiness stays a separate fact; lifecycle smoke disables dispatch.

## Acceptance criteria

- CLI help and operator documentation give exact registration/configuration,
  observation, lifecycle, cleanup, recovery, evidence, and non-authority
  semantics for both source types.
- A fresh daemon reconstructs both durable source types, and readiness, doctor,
  product-readiness, status, and support export share bounded source-health
  semantics without stale ready claims.
- Deterministic tests prove `ready`, `unavailable`, `invalidated`,
  `unsupported`, and pre-observation behavior plus process/unit redaction.
- A wheel installed in a disposable virtual environment registers both sources,
  reconstructs them in a fresh process, observes one provider-free transition
  apiece, matches once, retires, and cleans up with dispatch disabled.
- Focused and comprehensive tests, Python 3.11/3.12 CI, the OpenClaw plugin
  tier, wheel build/install, compilation, diff, planning, and lane checks pass.

## Non-goals and effect boundaries

No live process mutation, live session-bus or system-manager access, unit
control, arbitrary D-Bus access, public ingress, provider mutation, live
dispatch, installed-user-runtime mutation, global install refresh, release,
tag, or deployment. This issue does not consume the one P51 installed-canary
attempt; that remains isolated in #63.

## Execution and model routing

The primary owns the shared architecture, CLI integration, installed-wheel
receipt, GitHub custody, merge, and acceptance. One `gpt-5.6-terra` medium
worker may implement the bounded readiness/redaction slice after this plan is
published. A second `gpt-5.6-luna` medium worker may inventory documentation and
package-smoke gaps on disjoint files. One fresh `gpt-5.6-luna` medium reviewer
performs a read-only adversarial review after the combined candidate is green.
No nested delegation; one bounded repair cycle.

## Validation and stop rules

Start with focused red tests for source-state classification, exact-instance
health, redaction, status integration, fresh-process reconstruction, and the
installed lifecycle. Then run the comprehensive Python and plugin tiers, build
and install a wheel in a fresh disposable environment, compile changed Python,
run diff/planning/lane checks, and require both GitHub Python-version checks.

Stop if productization needs a new observer capability, wider resource
selector, changed durable descriptor, raw process/unit disclosure, dispatch,
normal-runtime mutation, or a live resource. Preserve every failed receipt and
classify it before a bounded correction. #63 remains blocked until this issue
is merged, closed, and read back on canonical `origin/main`.

## Validation evidence

- Focused readiness, process, systemd, configuration, daemon, monitor,
  product-readiness, and CLI tier: 162 tests passed.
- Comprehensive Python tier: 414 tests passed.
- OpenClaw plugin tier: 12 tests passed.
- Compilation, diff, and active planning audits passed.
- A clean disposable virtual environment installed wheel SHA-256
  `93e36f45aee64d827aa67dece32329dbae8633b011f854ed569a6856866ee39e`
  with `dbus-next==0.2.3`. The installed product smoke registered both runtime
  arms in phase A; a fresh phase-B Python process reconstructed the persisted
  process descriptor and `SystemdSourceStore` configuration, injected bounded
  provider-free observations, matched once through each source-owned runner,
  deduplicated repeats, retired and cleaned both records, and reported
  `dispatch_attempted: false`.

## Review and repair receipt

The single adversarial review cycle initially failed three material checks:
the installed smoke used one process and the generic evaluator, daemon health
dropped source diagnostic causes, and aggregate freshness could validate an
older instance receipt. The bounded correction split smoke registration and
reconstruction across installed-wheel subprocesses, routed evaluation through
the source-owned runners, added allowlisted optional diagnostic and observation
time fields to reconciliation health, emitted reconstruction-failure rows, and
required fresh exact-instance timestamps. Verification then found and corrected
one introduced inconsistency where `*_READY` was labeled a terminal failure.
The final reviewer verdict is PASS, with focused correction verification green.
No live process, session bus, dispatch, installed-user runtime, provider,
release, tag, or deployment effect occurred.

## Next action

Publish the reviewed checkpoint, reconcile P51-C4 as integration-ready, open
the linked pull request, and squash-merge only after Python 3.11/3.12 CI passes.
