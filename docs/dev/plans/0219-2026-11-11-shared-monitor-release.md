# LOCAL-P219 | Release and qualify shared monitoring

State: CLOSED
Ticket: https://github.com/CochranResearchGroup/codex-wake/issues/558
Owner: primary / ecochran76
Priority: P1
Branch: chore/shared-monitor-release-219
Dependencies: PR564 merged775daf53347e8d72d138b4eccd1c31a4919780ff
WIP limit: one

## Current State

CLOSED. Feature PR564 merged775daf53; release PR567 merged7af9b29f.
Exact0.22.0.dev7 installed at
`~/.local/share/codex-wake/releases/0.22.0.dev7-7af9b29` with319source/wheel/
installed members equal. All9launchers and Zsh completion refreshed;7accounts,
tenprotectedfiles,stock and27nativeprocess generations preserved. Controller,
refresh/webhook and unrelated services retain their existing processes.

Supervisor now loads dev7 with2bounded workers,14enabled roots all ready.
SoyLei overlap removed. Agent-browser,Graphiti and both Odollo monitors migrated
serially after individual acceptance; their old units remain retained, inactive
and disabled. Graphiti cadence remains60seconds, others1second. AuraCall and
mail-receipts retain independent services because CODEX_WAKE_DISPATCH_MODE is a
custom environment setting not represented in shared registrations.

Running Wake services11→6, enabled15→10;28definitions retained and no wake roots
or protected masks deleted. Short service-cgroup samples:before8.394s CPU57.49%
ofonecore/memory211705856bytes;after2workers12s CPU54.18%/169148416bytes. The
intermediate4worker configuration used330686464bytes, so it was reduced after
measurement. Shared-kernel/workload variation and different observation windows
preclude long-term causal performance claims.

## Scope and acceptance

Release dev7 on merged main. Qualify the exact immutable wheel under real Linux
UID1017 with installed monitor migration/restart/rollback, actual native saved
history/profile/client surfaces, old-package rollback, process/resource census
and representative steady-state synthetic polling economics. Preserve exact
baseline package and executable identities, all initial failures and limitations.
Shared-kernel timing and synthetic providers are not production acceptance.

Install only qualified complete merged package to versioned user prefix, retaining
all9launchers and Zsh completion. Preserve credentials/configuration, native
process generations, stock and unrelated services. Prepare reversible service
configuration and recorded children before replacing any monitor process. Pilot
SoyLei single ownership only after package, performance and child-preservation
checks pass; preserve cadence, dispatch settings and wake outcomes. Do not retire
other units or migrate additional roots without their individual acceptance.

## Validation and closeout

No second broad review: earlier one review/one TDD pass remains final for source
features. Run changed-surface checks and exact installed/runtime qualification.
Hosted paid CI excluded. Preserve stage/build/install/cutover as separate proof
boundaries; any failed/unknown required gate blocks its dependent live operation.
Record commands, hashes, rollback, final source/runtime readback and cleanup.
Memory disposition forbidden absent explicit memory-update request.

## Acceptance, provenance and rollback

Current-main conflict was one append-only runbook hunk; both closeout intents
retained. Combined monitor/tab113checks PASS26.557s; release64checks PASS6.826s;
pinned Ruff and policy wiring PASS. Earlier one broad review and one bounded TDD
pass remain final for feature source; no second review loop or paid hosted CI.

Exact merged wheel SHA256:
`0ab02e96cabdee925b8ae187a6a0b746d06c95e22775919b5d626ba02a903379`.
Real UID1017 qualification:9monitor migration/crash/reconcile/rollback checks,
11actual native/profile/history/launcher checks,5CLI/stdio/API/OAuth transport
checks, and dev6→dev7→dev6→dev7 launcher rollback with actual saved-TUI reopening
and13history files preserved. All319package members equal merged source and
UID1017 install; final owned native process census empty. Native test providers
were scripted localhost fixtures inside isolated networking, not external
inference. Native executable packages were not upgraded. UID1017 used CPython3.12.3
and working installation3.12.13 on the same Linux kernel; limitations explicit.

Initial failed probes retained: unreadable input directory, inaccessible inherited
cwd, and missing installed bin onPATH. Corrected launcher environment passed the
same immutable wheel. A diagnostic helper initially shadowed stdlib profile; it
was renamed before profiling. A per-root rollback preparation helper read an
unsupported PID key; migrations continued under existing guards and completed;
retained rollback now targets the exact qualified pre-installation dev6 package,
not a reconstructed original per-monitor loaded prefix. No raw history, credentials
or working record backups were published to Git.

Working cutovers used supported root delivery pause/guards; existing pause state
and authority retained, no owned-turn interrupt. Initial supervisor/SoyLei handoff
5.082s, all10temporarypauses restored;4individual roots each2.6–3.2s; final pool
capacity adjustment5.876s with14temporarypauses restored. Each stage checked
fresh root owner health, no reconciliation marker, native generations and
retained original unit/registration configuration. KillMode=process installed
before owner replacement; no native child cgroup teardown. Rollback helpers keep
exact package/unit/registry custody and never overwrite evolving wake records.

Private evidence and rollback commands:
`~/.local/state/codex-wake/qualification/plan0219/` contains qualification.json,
deployment-intent.json, cutover-intent.json, remaining-roots.json, pool-tuning.json,
live-before.json/live-after-two-workers.json, UID1017 receipts, deploy.py,
cutover.py rollback and migrate_roots.py rollback UNIT. Future uncertain outcomes
must be reconciled through the supported exact-token control, not manually cleared.

Next source opportunity is per-root dispatch-mode representation before either
remaining dedicated monitor can migrate; this packet does not infer that
configuration or retire historical definitions. Old release prefixes, branches
and rollback receipts are retained. Only this task's clean, published checkouts
are eligible for removal; original dirty checkout remains untouched.
Memory disposition forbidden by session explicit-request rule; non-write receipt.
