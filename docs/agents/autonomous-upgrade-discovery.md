# Persistent upgrade discovery

The upgrade watcher is opt-in and starts disabled. Source installation and the
example user units do not enable it. Existing upgrade enable/disable controls
remain authoritative for dispatch and promotion. Only explicitly registered
operator notices report effects; discovery never submits a model turn.

The installed `codex-wake-upgrade-watch --root ROOT --once` entrypoint performs one
bounded metadata poll and advances at most one accepted job stage. Without
`--once`, it repeats with bounded five-second idle waits. The service/timer
examples invoke this installed entrypoint under an explicit user. Adjust its
installation prefix and root to the actual qualified deployment. Do not enable
these units as a side effect of source qualification.

Discovery uses official stable-release metadata. It records last poll, next due,
latest release, current job, skipped releases, provenance and observed lag. If
selection data is absent, lag remains explicitly unverified. One current job
finishes its bounded attempt before a newer release can dispatch. Multiple newly
seen releases coalesce to the newest, with the skipped versions retained.
Rediscovery of an already attempted release returns its original job even after
its recipe changes; it does not create a fresh budget.

Host configuration may provide existing version-pinned recipes. To support future
releases without manually writing each recipe, configure `discovery.recipe_template`
as the absolute path of a trusted recipe JSON and `discovery.recipe_template_sha256`
as its exact SHA256. Only release id/version/revision and source identity are
filled automatically; build, patch, qualification and compatibility instructions
remain those of the pinned template. A changed template requires deliberate pin
reconfiguration and never renews an exhausted release automatically.

The built-in resolver dereferences the official stable tag to an exact commit,
downloads its canonical immutable GitHub archive, computes its digest and records
the archive as a pinned source input. Network metadata is not executable code.
Default source-resolution limits are 120 seconds and 512 MiB aggregate retained
source archives. Configure `discovery.source_timeout_seconds` (1–300) and
`discovery.source_maximum_bytes` (1 byte–2 GiB) explicitly if needed. Partial or
changed cache records require reconciliation; the resolver does not delete old
packages, source evidence or unrelated cache data to make room. The separate
upgrade job owns its repair/build budget and private worker process group.

Generated recipes are registered through the host-owned pinned-template catalog;
public job start checks the exact recipe SHA256 and upstream version under the
job lock. A metadata failure, unknown source, changed pin, disabled bot, exhausted
cache or unavailable authority produces inspectable held/disabled state while the
working build remains selected. Interrupted or uncertain jobs are never silently
resubmitted.

## Immediate local deactivation

The local owner of the private host configuration can stop the bot with one command:

```sh
codex-wake --wake-root /path/to/configured/root upgrades disable
```

This persists OFF, fences promotion and stops only owned workers. It requires no
service-grant reset or new resource allowance. It grants no ability to enable or
run work. Remote API/MCP controls retain their current scoped authentication.
Delivery failure remains visible if the notice recipient grant is unavailable.


## Interrupted verification

Normal restart/handoff retains the existing job and its cumulative limits. An
explicit `upgrades.reconcile` with `mode=verify_only` requires completed worker
provenance and never submits another coding worker. For a known-started, observed
dead worker without a final report, `mode=verify_review_only` additionally requires
a private host-owned full process census and pinned native-event artifacts. The
configured independent reviewer must then establish every original patch intent,
disposition and retirement equivalence after host verification. Public provenance
records `worker_completed=false`; absent output is never fabricated.

A repeat after deterministic host failure requires fresh census, retained original
evidence and only completed configured host commands since admission. Later
workers, reviewers or ambiguous in-flight effects refuse readmission. Both modes
retain original counters and deadlines. UTC adjustment metadata remains visible;
boot/counter uncertainty still holds. Host launcher PATH must retain any recipe's
sealed toolchain wrapper before the raw toolchain, including its approved cache
and profile settings. Local owner `upgrades disable` remains available without a
current service grant.


## Host tool preflight

The host-owned repair configuration may declare `host_tools`, mapping each
command basename to an absolute `path` and lowercase SHA256 `sha256`. For
example, pin `cargo` to the approved wrapper, rather than its underlying binary.
The executor checks PATH resolution and bytes before replay and before every
subprocess. Missing/fallback paths report `host_tool_path_mismatch: <name>`;
changed bytes report `host_tool_hash_mismatch: <name>`, without starting that
command. No PATH rewrite, dependency fetch or additional coding allowance occurs.
Undeclared tools retain existing behavior. These pins belong to the sealed job
configuration; adding them does not authorize changing an existing held job.


## Fresh deterministic verification jobs

Host `limits.repair_attempts: 0` admits a new job that may replay, regenerate,
verify and obtain independent review, but cannot submit a coding worker. Failed
verification/rejected review holds with `coding_disabled_verification_failed` or
`coding_disabled_review_rejected`; identity, deadline and zero counter remain
inspectable. Other numeric limits stay strictly positive. This does not renew
an existing expired job or make an interrupted worker complete.

Host `repair.reviewer.require_patch_dispositions: true` requires independent
intent/evidence/equivalence dispositions for every declared patch, even on a clean
normal replay. Prepared/public provenance identifies the independent dispositions
and retains original replay provenance. Missing/invalid dispositions fail closed.
Any mechanically derived source delta retains its prior-worker lineage separately;
review must bind the resulting exact source/tests and required capabilities.
