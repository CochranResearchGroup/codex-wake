# Runtime proof

Source, installed identity, availability, acceptance and publication are separate
boundaries. Verify the installed executable or direct MCP/service surface before
claiming its behavior. Use isolated fixture roots for reproductions; preserve
production state, other sessions, workers and pending intent. Label injected
provider evidence explicitly. Inspect current runtime without exposing credentials.
No source change or triage state authorizes live dispatch or recovery. Record
unknown outcomes; reconcile before retries. Do not substitute guest wall time
for an unqualified trusted clock.

Upgrade compiler cache: the private upgrade root owns `upgrade-compiler-cache/`,
shared by repair verification and package Cargo invocations through
`CARGO_TARGET_DIR`. Cargo fingerprints invalidate changed source, compiler,
target, profile and flags; cache presence never replaces stage or qualification
checks. `upgrades.status` reports identity, bytes, retention and the existing
`temporary_bytes` ceiling. Occupancy counts toward that job ceiling (together
with job scratch); reaching it holds work without deleting compilation.
Terminal holds and local disable retain the cache and original job limits.
`upgrades.cache_cleanup` with the exact expected target explicitly removes only
this cache, refuses active or uncertain workers, and records reclaimed bytes.
Packages, rollback selections and evidence are outside this cleanup boundary.
Legacy job-local `cargo-target` scratch remains disposable. Cache reuse is
compiler work reuse, not proof of a fresh compilation or package acceptance.
