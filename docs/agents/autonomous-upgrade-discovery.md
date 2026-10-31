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
