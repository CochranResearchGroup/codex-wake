# LOCAL-P218 | Efficient shared wake monitoring

State: CLOSED
Ticket: https://github.com/CochranResearchGroup/codex-wake/issues/558
Owner: primary / ecochran76
Priority: P1
Dependencies: none; operator confirmed the complete design
Branch: feat/service-consolidation-218
WIP limit: one implementation slice

## Outcome and acceptance

Reduce redundant monitoring and measured polling cost without weakening wake
durability, existing per-root cadence, deadlines, dispatch settings or authority.
The operator accepted preserving responsiveness and using a shared supervisor
for ordinary repository monitors, retaining separate HTTP controller, webhook
listener and refresh-worker lifecycles with justified isolated exceptions.
Service count is an outcome to measure, not a quota.

## Current State

Implementation packet CLOSED: children559–562 are tracker-resolved, integrated
and validated on feat/service-consolidation-218. One broad review and one bounded
TDD remediation are complete. No working service or runtime-record mutations.
The requested implement-spec delivery target is the validated branch; working-host
cutover remains separate and the SoyLei configuration overlap is still present. Source baseline: b6e93c2dada4eae08a869d569b5036defd2eaf39.
Existing unrelated config, glossary and Plan0216 changes remain untouched.

Read-only evidence lives outside Git at
`~/.local/state/codex-wake/diagnostics/service-efficiency-20261111/`:
inventory.json, resources.json and ownership.json. The audit counted 28 unit
definitions and 11 running units, including seven dedicated repository monitors.
A 12.055-second sample measured 62.19 percent of one CPU core and 230.83 MiB
across those units; supervisor 38.16 percent, mail-receipts 15.44 percent.
This is a short observation, not an idle baseline or causal attribution.

SoyLei has an enabled supervisor registration and an active dedicated monitor
for the same root; duplicate delivery has not been demonstrated. Four enabled
but skipped units have missing working directories; two retain existing wake
roots. Missing worktrees do not establish permission to remove runtime state.

Bounded read-only worker `/root/consolidation_facts` verified current source:
supervisor polling is serial; its global sleep follows the complete pass;
per-root cadence and worker limits are absent. Poll exceptions have root-local
health, but a hanging poll can delay other roots and setup failures can escape
the poll exception boundary. Record-level locks do not establish exclusive
monitor ownership. Primary accepts these source-backed constraints.

## Accepted design constraints

- Retain explicit root enrollment; never discover arbitrary workspaces.
- Preserve each root's current cadence and dispatch configuration. Graphiti's
  60-second cadence must not become one second on migration.
- Preserve durable requests, identities, deadlines and existing authority;
  consolidation never grants dispatch permission or uncertain-effect retries.
- Keep controller, webhook and refresh lifecycles separate. Retain isolated
  monitor exceptions where measured behavior or authority boundaries justify it.
- Bound concurrent root polling; do not allow overlapping passes for one root.
- Make root ownership and handoff inspectable. A lost or timed-out owner must
  not authorize overlapping effects or blind replay.
- Keep caches derived and invalidatable by out-of-process record changes.
- Preserve account/native daemons, attached sessions and masked protections.

## Confirmed failure boundary

The operator confirmed that a hanging root must be containable without restarting
other roots. Select an execution boundary that can isolate a blocked poll; bounded
threads alone cannot guarantee cancellation. Preserve uncertain in-flight effects
for reconciliation rather than blindly killing and restarting delivery work.
The exact worker mechanism follows the accepted failure boundary, not vice versa.

## Execution ledger

Spec: docs/dev/specs/0218-service-consolidation.md and GitHub #558.
Integration base/fixed review point: b6e93c2dada4eae08a869d569b5036defd2eaf39.
User authorizes ticket publication, delegated implementation, closure, one broad
review and one bounded TDD remediation pass. Seams: existing supervisor/daemon
entrypoints plus the read-only audit command; existing public seams preferred.

| Ticket | Blockers | Owner | State | Scope |
| --- | --- | --- | --- | --- |
| #559 root ownership | none | /root/ownership559 | validated | daemon, ownership module, ownership tests |
| #560 isolated scheduling | none | primary | validated | supervisor, scheduler, CLI, scheduler tests |
| #561 audit | none | /root/audit561 | validated | audit module/script/tests |
| #562 pilot | #559, #560, #561 validated | /root/pilot562 | validated | qualification script, docs, integration |

No overlapping worker write scopes; shared ownership result is a PollResult
with an observable skip reason. Scheduler accepts existing result serialization.

## Scope and execution sequence

1. Establish a repeatable read-only resource baseline and exact SoyLei ownership,
   dispatch settings, pending/firing state and supported rollback. Resolve its
   duplicate monitor configuration with one verified owner and no changed wake
   records. A stale health file alone cannot prove ownership or safe takeover.
2. Add per-root scheduling and bounded failure isolation through the actual
   supervisor interface, covering fairness and no same-root overlap. Profile
   record scanning before choosing caching or other polling optimizations.
3. Migrate one ordinary monitor as a pilot. Preserve effective configuration,
   qualify restart and rollback, then migrate additional eligible roots serially.
4. Retire proven-obsolete service definitions only after reference and ownership
   checks. Preserve associated wake state and the retained webhook until its
   external-source responsibility is reconciled.

Primary owns design, ownership transitions, integration and acceptance. Source
inspection and independent review may be parallel; schema, scheduler changes and
live ownership transitions are serialized. Each independently mergeable slice
needs a matching GitHub issue, bounded branch and active-lane registration before
implementation. This draft supplies local intake without mutating the tracker.

## Acceptance evidence

- Deterministic checks show each root retains its configured cadence and dispatch
  settings; a slow or failed root does not prevent another ready root progressing.
  Timing budgets must be explicitly defined against measured current behavior;
  existing one-second sleep is not a one-second delivery guarantee.
- Two competing monitors and restart/takeover scenarios exercise the actual
  ownership interface without duplicate active poll owners. Unknown delivery is
  retained for reconciliation; tests do not claim universal exactly-once effects.
- Representative synthetic backlogs reproduce measured hot paths through public
  monitoring interfaces. Record workload, source revision, elapsed time, CPU,
  memory and latency before/after; show lower polling cost without cadence loss.
  Do not call a production poll solely to benchmark: it may dispatch.
- Qualify migration and rollback in disposable state, then verify installed
  commands and exact live service ownership under applicable deployment gates.
  Preserve unrelated sessions and runtime state throughout.
- Record local check commands, results and environmental differences; hosted
  paid CI is excluded. Selected checks are not the full suite.

## Non-goals and definition of done

No account/native-daemon consolidation, pending-wake deletion, deadline extension,
provider permission expansion, unconditional four-service target or wholesale
runtime-store migration. No implementation or cutover during design intake.

The design phase ends with resolved failure boundary and explicit shared-design
confirmation. Implementation closure separately requires measured acceptance,
review, exact integration/install evidence where applicable, tested rollback and
current owner/resource readback. No performance improvement is claimed yet.

Memory disposition: forbidden; session instructions require an explicit user
request before memory updates. No memory write is authorized by this design task.

## Dependency validation checkpoint

#559 integrated as 8f87a6d8 (worker507a6249), #561 as2ee87e63 plus17a73faa
(worker3eb99d44/413ddd65), #560 as54d3b0e5. On integrated source, declared
Python3.12 environment installed from .[mcp,dev]: scheduler5 PASS2.941s,
ownership7 PASS1.219s, CLI66 PASS15.701s, audit2 PASS0.892s; existing supervisor13
PASS1.027s. Pinned Ruff undefined-name checks pass. Initial CLI/scheduler CLI
runs in dependency-free interpreter failed missing websockets; those results
are retained, not product failures erased by retry. Full logs outside Git under
qualification/plan0218. #562 may now start. Working services remain unchanged.

## Final source acceptance and limits

Children559,560,561,562 CLOSED with readback receipts; parent558 remains open
under the to-tickets parent-preservation contract. Integration includes worker
results507a6249,3eb99d44/413ddd65 and8b0d061c; all primary-owned review corrections
are8d5a4e0b. Review record: docs/dev/evidence/plan0218/review.md. Exactly one broad
review: Standards1 accepted P2 custody judgment and Spec1 accepted P1 root-path
isolation defect, both resolved in one bounded red/green remediation pass.

Final focused command (PYTHONPATH=src:tests):
`python -m unittest test_supervisor_scheduling test_monitor_ownership test_supervisor test_daemon test_service_audit -q`
PASS61 on Python3.12 (8.261s) and3.11 (8.755s). Earlier CLI66 PASS15.701s.
`python -m unittest test_command_contract -q` PASS3 (1.006s) after regenerating
coverage. Pinned Ruff F821/F822/F823, compileall, policy wiring and CI-scope check
PASS. Initial dependency-free probe failures are retained outside Git.

Comprehensive diagnostic run:2423 tests/860.451s,1failure/1skip. The failure was
stale generated command coverage; reproduced red, refreshed one coverage entry,
then all3 contract checks green. No second comprehensive run or broad review.
Run began at1c72de30; late review corrections were applied while it was running,
so this is not a pure final-tip comprehensive acceptance claim. Final changed
modules are covered by the selected61 checks and corrected-wheel qualification.
Hosted CI was skipped by operator cost policy. OpenClaw plugin code is unchanged;
its separate npm lane was not run under the standing project pause.

Exact corrected package source8d5a4e0b, wheel SHA256
b3bb729891bb01d92ad8b78ff5caa6744eaf887a6d168105668a7106587e6824:
318package members match source/wheel/isolated installation. Corrected installed
pilot9checks PASS13.355s; final owned live-process census empty. Baseline package
is b6e93c2d, not the working service package. Raw qualification, comparisons,
initial failures and readbacks stay outside Git in qualification/plan0218.

Earlier exact18poll comparison:6old dedicated processes139.0MiB sampled summed
RSS/.628CPU-seconds; new2workers+coordinator/helpers83.9MiB/.376CPU-seconds.
Oldserial22.5MiB/.036CPU-seconds remains cheaper; pool wall time was higher.
These are short synthetic cold-run comparisons, not production steady-state
savings, exclusive memory/PSS, or proof for native/provider backlogs.

Working-host services were not migrated, disabled or removed. No native build
upgrade or real Linux test-user deployment gate is claimed. Preserve those gates
before installation/cutover; docs/dev/service-consolidation.md owns the rollback-
ready operating procedure. Scope adjustment: this implementation packet delivers
controls plus disposable qualification; live SoyLei remediation/retirement in the
original sequence remains an explicit future operational boundary.
