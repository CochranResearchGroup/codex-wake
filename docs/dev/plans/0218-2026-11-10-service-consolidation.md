# LOCAL-P218 | Efficient shared wake monitoring

State: OPEN
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

Design approved; implementation packet being established; no service or runtime-record
mutations. Source baseline: b6e93c2dada4eae08a869d569b5036defd2eaf39.
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
| #559 root ownership | none | ownership worker | pending | daemon, ownership module, ownership tests |
| #560 isolated scheduling | none | primary | pending | supervisor, scheduler, CLI, scheduler tests |
| audit ticket | none | audit worker | pending | audit module/script/tests |
| pilot ticket | all above | primary after validation | pending | qualification script, docs, integration |

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
