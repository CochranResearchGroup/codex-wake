# Issue427 historical Wake custody reconciliation

Parent: issue420; frozen specification: issue420 body. Owner: primary / ecochran76.
Source baseline: `5fcf2d65052c3316f84d821c6ff1d233e6746187`.

## Outcome and boundaries

The113 baseline Wake entries each have a retained/retired disposition, exact
HEAD, custody ref, owner, reason and next action in the private reconciliation
ledger (`reconcile420/427/disposition-ledger.json`). Seven newly active worker
checkouts are explicitly excluded. The primary checkout, installed packages,
services, resource state, credentials, histories and native repository were not
changed by this slice. Source input ownership remains with tickets422–426;
native ownership remains with428. The primary coordinates shared plan/catalog
projections and integration.

Thirty absent, unlocked registrations were removed individually with ordinary
`git worktree remove`, after HEAD/custody checks. Their refs and branches remain.
No existing checkout is retired at final readback. No ignored payload was erased.

The initial five clean physical removals used an incomplete visible-process
census: inaccessible process links were incorrectly treated as absent evidence.
That inactivity conclusion is invalid. All five paths were restored immediately
at their original branch and exact HEAD with clean tracked/untracked/ignored
status: allocation-spec, harness-backlog, self-refresh-delivery, v0172-delivery and
v0173-delivery. Removal and corrective restoration receipts are both retained.
A subsequent census records228 denied links across81PIDs (PID/UID/denial metadata
only). Current permissions cannot prove cross-UID inactivity. Every existing
historical checkout therefore remains intentionally retained, owner primary,
next action a future authorized owner census before physical retirement. The
source/build reference inspection covers user units, Wake configuration and user
launchers; it is not a complete system-wide absence proof.

## Semantic evidence

Ancestry alone was not used to infer absence. Provider PR/head/merge readbacks,
canonical ancestry,1246 accepted historical patch identities and per-path blob
correspondence are preserved privately. Fourteen entries are canonical ancestors,
34 have merged-head ancestry,40 have accepted patch correspondence, and14 are
historical stages of cumulative PR349. Remaining entries are explicitly owned
source inputs or historical research/deployment/qualification checkpoints.

Merged [PR349](https://github.com/CochranResearchGroup/codex-wake/pull/349)
(`ce1ad93`) has an identical tree to its published integration head. It carries
the cumulative HF06, exact refresh, task-brief and goal-control implementation.
For example, HF06 tip `5d34fc7` has byte-identical `permission_handoff.py` and
`permission_a2a.py` to that integration; `4356ec3` has identical scoped-refresh
source; `75789bd` has identical task-brief implementation. Later main introduces
additional scoped refresh request/effect guards. Closed, unmerged PRs311,327 and329
and open historical PR332 are therefore not themselves missing-behavior proof.
The historical guard branches are superseded by the cumulative PR280 source;
current public permission/recovery/strict-executor tests qualify the resulting
behavior. Old host400/health390 supplemental qualification commits retain their
custody refs; PR419 owns later controller source and qualification. Historical
OAuth research and resource-specification checkpoints remain preserved as
research history, not new implementation requirements.

The two untracked retro planning documents are preserved as explicitly historical
[snapshots](../evidence/issue0427/historical-0174-2026-10-25-retro-execution-controls.md).
Their still-needed intent is already in published issue350, closed Plan0175 and
merged [PR358](https://github.com/CochranResearchGroup/codex-wake/pull/358)
(`1a315643`, identical published-head tree): transparent notices, persistent
operator deactivation, bounded dispatch, preflight, request admission, validation
and completion funding. Issue350's OPEN tracker state is not an implementation
absence proof. No new feature or runtime acceptance claim is introduced.

## Historical authority projections

Plans0166/0167/0168/0169/0177/0178 now carry standalone deterministic state
headers, preserving their documented CLOSED/OPEN outcomes. COMPLETE in0169 is
normalized to CLOSED. Plan0190 is CLOSED for accepted source/specification scope;
its recorded production gates remain. Plan0176 gains Current State while remaining
OPEN: source integrations361/362 and terminal reconciliation363 do not establish
a successful resident refresh. Historical observations and failure evidence stay
in place. This is metadata reconciliation, not fabricated runtime completion.

## Validation

- Active planning audit: PASS, zero problems; all eight reported baseline defects
  resolved without broadening the audit baseline.
- Eighteen existing public unittest files:191tests PASS in87.670seconds, Python3.12.13,
  `PYTHONPATH=src:tests`. Coverage includes permissions, migration, handoff,
  recovery, refresh, task briefs, strict executors and controller host/health seams.
- First invocation found no pytest package; the next unittest invocation omitted
  the tests import path (four import errors). Both first failures are preserved;
  the corrected full selection passes. No source repair was required.
- `git diff --check`: PASS. Source/tests are unchanged from the baseline commit.
- Per-target removal, restoration, custody and final inventory readbacks are
  recorded privately. Hosted CI was not run; this is local Python3.12 validation,
  without the hosted Python3.11 matrix or any live deployment qualification.

Memory disposition: forbidden. This bounded delegated packet does not authorize
an additional persistent-memory update; the primary owns the parent closeout.
