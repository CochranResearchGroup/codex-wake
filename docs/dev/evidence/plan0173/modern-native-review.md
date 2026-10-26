# Modern native port review

Review target: upstream `6aaac694803004a63c6f393d153c96d22521a6b9`
through `fda3733d6a` on `fix/wake-native-0.164`.
Spec: [modern port plan](../../plans/0173-agent-harness/0006-2026-10-25-modern-native-port.md).
Independent reviewer: `/root/modern_port_review`. One discovery pass; no compilation or edits.

## Standards

No candidate findings. The review checked existing processor, per-thread
serialization, configuration-refresh and history-recording seams. External
lockfile dependency identities remain unchanged. Primary accepts this result;
no structural cleanup is added to scope.

## Spec

No candidate findings. The reviewer checked loaded-thread lookup, non-mutating
scope probing, captured runtime status without global discovery, no-turn context
injection, durable notice history, idempotency and confirmed connection writes.
Generated notices and runtimeOnly exports are present; reload remains experimental
as declared. Primary accepts the source-review result.

This is source review, not runtime acceptance. Focused integration tests, modern
managed roundtrip, actual TUI rendering, matching final package and live requesting
session acceptance remain separate gates. No accepted findings require remediation.

## Additional smoke

The initial complete package ran `/bin/sh` inside its real read-only sandbox.
It printed `sandbox-ok`; a cwd write failed with `Read-only file system`, and
no file was created. The private root had an explicit profile extending
`:read-only`. Two earlier invocations used obsolete syntax or omitted the now
required profile and failed during command setup; neither is a runtime regression.
Private receipt: `native-modern-0164/sandbox-readonly-smoke.json` under user state.

The cumulative binary patch is preserved byte for byte and passes reverse
application checking against its exact source. Ordinary whitespace scanning of
the patch file reports its required single-space blank context lines; source
whitespace checks remain separate. Do not trim patch context to silence that scan.

## Runtime findings and bounded remediation

The first native integration selection passed both connection-reuse modes and
hook warmup, but found a real default-paginated notice failure. The original
reader used a legacy-only history API, and paginated persistence deliberately
drops legacy AgentMessage events. An initial reader-only repair did not fix
that persistence cause. These failures remain retained in private receipts.

Native `83d9e54059235ebadf1176f30fafb81091b2b323` now supplies the canonical
ItemCompleted form alongside the legacy display form. Upstream selects the
appropriate representation for each history mode. Persisted paginated item
pages supply the durable deduplication oracle, independently of compacted model
context. Primary verified the persistence policy and reviewed the bounded fix.

Four focused cases then passed with retries disabled: paginated and legacy
notices (including actual restart/readback, content conflicts and deduplication),
pending-response retention, and selected-thread MCP reload. The reload test
also required the existing error-response helper for its expected rejection;
production reload code did not change. Legacy usage expectations now include
the upstream cache-write token field. No accounting or lifecycle code changed.

Final formatting changed only the MCP snapshot call layout, committed as
`3ab07eac61e3247524e66afcb3f9271a87725482`. No tests were repeated solely for
formatting. The cumulative patch now points to that source; the final complete
package is rebuilding before runtime qualification.

## Cold TUI replay repair

A genuine paginated TUI run found a second production issue: live notices were
visible and persisted, but cold TUI hydration discarded their orphan items.
Read-only database and source tracing showed no matching turn metadata. Public
item readback alone was insufficient frontend acceptance.

The producer now uses upstream's existing ItemCompleted plus TurnComplete
representation for a completed display container in paginated history only.
It writes directly to persistence without TurnStarted, provider usage, a session
completion callback or a TurnCompleted notification. Legacy behavior is unchanged.
The regression first failed public turn paging (zero containers, expected one),
then all four focused cases passed with retries disabled. They verify cold
turn/item association, exact null-timing display completion, unchanged goals,
zero extra model starts/usage, and a busy real work turn remaining in progress.
Primary reviewed the 22-line production change and its upstream precedent.

Source `eceb9d578809fded64d91bbdb1f8f5a3fcb546f3` passed final formatting with
no further edits. The complete package is rebuilding; actual stock TUI replay
and current Wake 0.22.0.dev1 acceptance remain open. Caller metadata passed on
unchanged source; the previous scoped Clippy packet timed out without findings
and is not counted as green.
