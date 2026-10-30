# Legacy migration preview and disposable cutover — issue 398

Authority: issue 398 under specification 393, reusing absorbed Profiles
`plan_migration` / `apply_migration`, accepted disposable package work in closed
378, account/history owners 395/396 and common durable operation owner 401.
Production activation and unattributed legacy writer dependencies remain
exclusively issue 380. Base `c8c483cf24da8e235a33e3e015096309e5e56292`;
worker `feat/controller-migration398`, `/tmp/codex-wake-migration398`.

## Stable public owner and configuration

`ControllerMigration(config_path, *, root, host, environment,
writer_probe=None).scope_target()` returns stable host/environment/migration_id
and optional fixture_id. `execute(migration.preview | migration.apply |
migration.rollback, arguments, authorize=None)` returns a payload. The trusted
authorization callback is rechecked before privileged filesystem steps; it is
not a caller argument. Primary owns shared CLI/API/MCP registration, grant
schemas and ControllerRuntime mutation admission; this owner does not duplicate
intent/idempotency/accounting stores. Its private domain receipt records only
filesystem provenance needed for rollback, with credential metadata rather than
credential contents.

Fixed host `controller-accounts.toml` retains `[profiles]` for the existing
account homes and shared source. Example migration table:

```toml
[migration]
scope_id = "legacy"
scope_root = "/explicit/authorized/scope"
candidate_root = "/explicit/authorized/scope/candidate"
pointer = "/explicit/authorized/scope/active-config"
legacy_config = "/explicit/authorized/scope/legacy-profiles.toml"
```

`fixture_root` is accepted as a compatibility spelling of scope_root. Preview
inventories only configured source/account/candidate/pointer/legacy-config roots,
not an entire common ancestor. It reports indirect resolution chains, external,
dangling/cyclic unknown dependencies, writer coverage/holds, native owning
history qualification, proposed reused Profiles actions and a request target
with `migration_revision`. Scope grants should bind stable migration identity;
per-request expected_target pins the changing plan revision. Apply and rollback
reuse the same stable grant without fresh consent.

Preview does not require a disposable marker: real explicitly configured stores
can be inventoried without relabeling them fixtures or authorizing mutation.
Every preview reports production_effect_status=not_authorized and issue380.
Effects require a real canonical scope root with marker
`.codex-wake-migration-fixture.json` containing schema_version=1,
purpose=codex-wake-migration-fixture and an exact fixture UUID. The provenance
root must stay outside that disposable target. Candidate/shared/account roots
must be disjoint and inside scope. Unsupported paths, special/large files,
shared mutable policies, private account/history ambiguity and incomplete writer
coverage remain holds.

The default writer probe is bounded same-user `/proc` open-write-descriptor
inventory; it never reads command lines, provider credentials or file contents.
Unobservable processes/descriptors mean UNKNOWN, not idle. This host currently
returns UNKNOWN; production is therefore not declared quiescent. Disposable
acceptance may inject a trusted controlled-fixture writer witness at the host
seam, separately from proving positive actual child write-descriptor detection
and unknown-hold behavior. No client field disables the census.

## Effects and preservation

Apply requires exact expected_target and no preview holds. It seeds only
config/skills/rules in an isolated candidate using the absorbed Profiles planner
and executor. Qualified private account directories relocate by same-filesystem
rename; credentials and native histories keep their inodes. Original account
paths become explicit compatibility links, preserving absolute native rollout
locators while native reads resolve inside the owning candidate namespace.
Original shared state, including unassigned shared histories, is retained and
never blanket-copied or attributed to an account. Mutable shared account links
and unqualified native history remain held. Native auth/OAuth/token/password/
keyring/secret files are not opened or copied.

The candidate registry preserves all parsed host policy except the explicit
profile root change; unsupported/lossy rewrites and embedded credential fields
are held. One fixture-local configuration symlink switches after candidate
account/history qualification. No native process, package, service or governor
is launched or restarted, and no allowance or accounting owner is renewed.

Rollback requires an attributable completed receipt, exact current target,
unchanged candidate afterimage, original shared store, compatibility links and
active pointer. It restores owning directories and the prior pointer, then
removes only its unchanged candidate. Any post-cutover work causes refusal even
if the caller obtains a fresh target revision. Interrupted apply/rollback retains
an uncertain domain receipt; the shared durable operation owner fences replay.
A partial effect is never automatically retried or destructively rolled back.

## Core TDD and pending installed acceptance

Command: `PYTHONPATH=src /home/ecochran76/workspace.local/codex-wake/.venv/bin/python -m unittest discover -s tests -p test_controller_migration.py`.
Red missing owner -> green preview. Red unsupported migration.apply -> green
apply/rollback with credential inode and original shared bytes preserved. Red
link-cycle exception -> green visible unknown dependency hold. Seven focused
tests pass in 1.841s, including real child open-write-FD detection, unknown census,
stale plans, changed rollback target, unmarked preview/production refusal and
interrupted effect no destructive retry. Ruff 0.14.2 passes.

Shared registration and installed actual transports are pending in this core
checkpoint. This note does not claim issue completion, production authorization
or source-only acceptance. Supplied frozen issues and current owners are the
implementation authority; no external memory lookup adds authority here.

## Scoped admission checkpoint

`MigrationAuthorization(authority, migration, *, runtime=None).execute(token,
operation, arguments)` now owns preview scope admission and delegates mutations
to the existing ControllerRuntime. Preview requires migration.observe; effects
require admin and stable host/environment/migration_id plus fixture_id for a
marked fixture. Grants intentionally need not contain migration_revision. Each
request independently pins expected_target and the durable _request target.
The same real OAuth grant previews, applies, replays the original operation and
rolls back the changed target revision. Read-only and wrong-scope grants refuse
mutation before effects. Runtime absence refuses effects.

Per-step callbacks pin host policy bytes and stable scope, never the mutable
pre-apply filesystem snapshot. Own successful cutover/rollback therefore does
not invalidate the reusable grant or final delivery. Revalidation after a writer
probe closes the observed mid-probe revocation window: red test showed cutover
occurred after a probe revoked the token; green checks authority again before
the next filesystem step. Partial qualification loss yields the common durable
operation's unknown/uncertain state, and replay returns that original operation
without dispatching again. Candidate registry/accounting preservation is also
asserted through public filesystem outcomes.

Auth-scope and administrative runtime schema commits supplied by the coordinator
are separate dependencies, not worker changes. Eleven focused migration tests
pass; shared registration and full installed acceptance remain the next gate.

## Read-only inventory hardening checkpoint

Inventory fingerprints now use file type/device/inode/size/mtime/ctime and link
chains, not arbitrary file contents. Native credential stores can have unknown
names; metadata inventory never opens those files. Only the configured policy,
disposable marker and native history owners/header qualification are read.
Native WAL history is reported as requiring its quiescent owner before opening
SQLite connections, so preview never recreates WAL shared-memory sidecars,
checkpoints or converts a native database. This remains an explicit dependency,
not a migration fallback.

A real writer-positive test exposed a process-enumeration race: a process that
vanished during /proc stat caused an unknown scan to discard all positive
observations. Vanished entries are now ignored as gone, permission failures stay
unknown, and observed writer evidence is preserved. The original failed positive
assertion is retained in the session evidence, followed by focused repaired
writer detection and the full migration selection. Twelve focused tests pass in
3.795s; the native WAL test also verifies no sidecars appear. Production writer
qualification still remains issue380; a changed or unobservable process is never
silently described as idle.

A focused registry-preservation red/green test also distinguishes public model
output-token limits and native credential-store mode settings from embedded
credential values. Valid policy survives exactly; actual env/API-key credential
fields, including nested lists, remain held rather than being copied. Thirteen
focused migration tests now pass in 3.015s.

## Shared registration and candidate use

The shared CLI/native-MCP/HTTP/OAuth-MCP/remote-CLI registration now dispatches
through MigrationAuthorization and the existing durable administrative runtime.
The trusted native runner can inject migration_writer_probe only as host context,
never a tool argument. Default census behavior is preserved.

Normal account/profile/history/build entrypoints now resolve the configured
candidate only through controller_registry: exact declared pointer and candidate,
valid disposable marker, one private applied receipt, unchanged routing policy,
and qualified owning compatibility links. Arbitrary pointer targets or missing/
changed receipts are refused. Original host routing policy remains untouched;
active policy is read from the qualified candidate. Cached service account owners
resolve again per operation, so cutover is actually consumed rather than leaving
clients on stale legacy paths. The public account/history test first failed on
the old compatibility link, then passed for both newly constructed and cached
owners after this loader. Rollback returns normal consumers to the original root.

Validation of this shared checkpoint: 73 existing controller tests pass in
30.999s, including the expanded migration/native history behavior. No Flow406
untracked work or other lane source is imported or changed.

Final no-argument profile usability red/green qualification found that the saved
current-account selector also needs preservation. Only its qualified canonical
account ID is seeded into the candidate (an explicit preview selection action),
never credential contents or shared histories. An unknown selected account holds
qualification. The original selector remains untouched and rollback preserves
normal no-argument selection as well as explicit account entrypoints.

The selector qualification includes non-default shared-directory settings. A
second red showed the default planner path would ignore an explicitly configured
shared directory; candidate planning now reuses the complete absorbed Settings
value with only state_root replaced. Custom prefixes/shared paths and policy
remain intact. Absolute/escaping shared paths and noncanonical account alias
bindings remain explicit qualification holds rather than inferred ownership.
