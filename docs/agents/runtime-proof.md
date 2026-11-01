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

An opaque recipe evidence label does not establish or invalidate a native build.
Qualification can derive provenance from the owned completed build commands,
immutable package and exact native probes, independently approved source/tests,
review execution and prepared recipe. The original label and receipts remain
unchanged. Public `upgrades.reconcile` mode `qualification_only` archives the
prior qualification hold, revalidates these identities and pinned acceptance
artifacts, and readmits only qualification under the same job, policy, counters
and original deadline. It runs no coding worker or rebuild and grants no new
allowance; fresh qualification and promotion remain separate gates.

A current scoped administrator can observe an interrupted promotion with
`upgrades.reconcile` mode `promotion_observe`. It reads the retained intent and
actual selected registry/package through the existing promotion owner. It never
replays selection, rebuilds, resumes a worker or changes the original deadline,
policy, limits or spent attempts. A disabled or expired terminal job retains its
stop state while publishing the observed selection under `promotion_observation`;
an interrupted nonterminal promotion settles from actual registry evidence. An
uncommitted intent remains held. Current caller authorization and exact target
are required even when the original work allowance has ended.
