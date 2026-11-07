# Stock shared home and independent Wake profiles

State: OPEN
Work item: https://github.com/CochranResearchGroup/codex-wake/issues/488
Owner: ecochran76 / primary
Authority: ten accepted interview decisions and explicit to-spec invocation.

## Current State

Specification published as GitHub #488 with ready-for-agent state;
implementation ticket execution is starting on feat/independent-profiles-0205. The
operator-approved testing boundary is the existing public controller operation
surface shared by CLI/API/MCP, followed by actual stock/two-profile and WSL/PowerShell
acceptance. No runtime configuration or authentication changed in this phase.

## Problem Statement

The operator wants to keep using ordinary stock Codex with one shared home: logging out and logging in switches accounts, while session history and configuration remain available. Wake profiles must run alongside stock, start from useful copies of that configuration, and subsequently remain independent of stock and each other.

The existing account-oriented design assumes private account stores and can share configuration among managed profiles. Its history importer requires an idle, fully persisted source and treats account homes as the source/destination boundary. Those assumptions do not fully support the agreed shared-stock-home mode. Runtime inspection also found a blocked modded launcher, invalid build registrations and an unavailable limit watcher; deployed source and previously passed disposable native tests do not establish working-profile readiness.

## Solution

Preserve stock's existing launcher, home and account-switching behavior. Add an independent Wake-profile mode with snapshot seeding, selective explicit configuration sync, source-preserving session transfers and inspectable readiness. Adopt existing profiles without discarding their history, sign-ins or local settings.

Make stock's shared home a first-class store whose identity persists across login changes. Support explicit transfers stock to profile, profile to stock and profile to profile. Reuse supported operator-level MCP connector sign-ins while keeping Codex account login and writable runtime state local to each profile. Expose equivalent behavior through CLI, API and MCP to WSL and PowerShell clients.

## User Stories

1. As an operator, I want plain codex to remain stock, so that my ordinary workflow stays familiar.
2. As an operator, I want to keep stock's existing shared home, so that my sessions and configuration survive logout/login account switches.
3. As an operator, I want stock's source-store identity to survive an account switch, so that configuration sync and session discovery remain coherent.
4. As an operator, I want known session-account provenance preserved without guessing from the current login, so that mixed-account history stays accurately described.
5. As an operator, I want to create a Wake profile from stock configuration, so that setup is quick.
6. As an operator, I want the seed to include MCP definitions, hooks and their assets, skills, rules and ordinary settings, so that the profile is useful immediately.
7. As an operator, I want session history imported separately from configuration seeding, so that I choose which conversations to bring over.
8. As an operator, I want each profile's home and writable state independent, so that stock and sibling profiles cannot change it implicitly.
9. As an operator, I want each profile to retain its own Codex login, so that switching stock accounts does not sign the profile into another account.
10. As an operator, I want supported operator-level MCP sign-ins reused, so that independent configuration does not force needless connector logins.
11. As an operator, I want unsupported connector sign-in reuse explained precisely, so that I can complete only the necessary native sign-in step.
12. As an operator, I want a configuration inventory that includes recognized categories and unknown items, so that useful settings are not silently omitted.
13. As an operator, I want copied hook and skill references to resolve to the intended assets, so that a profile does not accidentally depend on mutable stock-home files.
14. As an operator, I want to inspect effective configuration and provenance, so that I can tell copied settings from overrides and deliberate external dependencies.
15. As an operator, I want explicit source, destination and category selection for sync, so that I can update only MCP definitions, hooks or another chosen subset.
16. As an operator, I want one request to update selected profiles, so that routine maintenance is convenient while results remain attributable per destination.
17. As an operator, I want source changes applied automatically when the destination has not diverged, so that routine updates require little interaction.
18. As an operator, I want destination-only changes preserved, so that my profile customizations remain intact.
19. As an operator, I want conflicts reported only where both sides changed the same setting, so that unrelated safe updates can proceed.
20. As an operator, I want a preview and prior-sync baseline, so that proposed changes and conflicts are understandable.
21. As an operator, I want repeated sync requests to be repeat-safe, so that retries do not duplicate changes or erase unresolved conflicts.
22. As an operator, I want source deletions to preserve destination copies by default, so that a removal does not silently propagate.
23. As an operator, I want matching deletions available by explicit request, so that I can intentionally bring selected categories into agreement.
24. As an operator, I want synced settings to take effect at the next launch by default, so that ongoing work is uninterrupted.
25. As an operator, I want an optional supported reload of only the selected profile, so that I can apply changes sooner without restarting stock or peers.
26. As an operator, I want recent-N session viewing from stock and selected profiles, so that I can choose work to continue.
27. As an operator, I want to import one conversation or a recent-N selection in either direction, so that work can move between stock and independent profiles.
28. As an operator, I want a consistent saved snapshot of an ongoing source where supported, so that I can copy useful progress while the source continues.
29. As an operator, I want the snapshot boundary and unsupported entries reported, so that I understand exactly what was copied.
30. As an operator, I want imports to preserve source conversations, so that transfers do not disrupt existing work.
31. As an operator, I want an unchanged source revision to reuse its existing destination copy, so that repeated imports do not create duplicates.
32. As an operator, I want an advanced source revision to create a new linked snapshot, so that earlier destination copies and their later work remain intact.
33. As an operator, I want unknown transfer outcomes reconciled before another submission, so that a lost reply cannot cause a duplicate conversation.
34. As an operator, I want existing profiles adopted with history, sign-ins and local settings preserved, so that the new mode does not force me to start over.
35. As an operator, I want shared writable links replaced by private state during adoption with rollback protection, so that independence is real and recoverable.
36. As an operator, I want stock and two Wake profiles to operate concurrently, so that I can use stock normally while exercising modded capabilities.
37. As an operator, I want actual client, backend, profile and account observations, so that labels alone do not claim the correct harness is connected.
38. As an operator, I want CLI, API and MCP to expose the same outcomes, so that WSL and PowerShell clients can use the same workflow.
39. As an operator, I want normal chat/resume, transfers and MCP/hooks sync qualified together, so that the workflow is demonstrated end to end.
40. As an operator, I want self-limits and scoped refresh tested on the selected real profile, so that available tools are distinguished from actual enforcement and refresh.
41. As an operator, I want the personal profile qualified alongside stock before adding a second profile, so that rollout proceeds in a bounded observable sequence.
42. As an operator, I want capability failures to identify a concrete remedy, so that configuration and grants do not become blanket obstacles to demonstrated functionality.

## Implementation Decisions

- Keep stock's normal launcher and shared-home behavior unchanged. Register its store identity in Wake-owned metadata without imposing a per-account migration or reconfiguring stock merely to register it.
- Distinguish a store, a Wake profile, the currently authenticated Codex account and a runtime instance. Switching stock login does not replace its store identity or sync baseline. Preserve known provenance; report unknown account provenance explicitly.
- Extend the existing profile/account owner, configuration provenance owner, history discovery/import owner and shared controller contract. Avoid a competing account selector, registry or parallel configuration manager.
- Introduce an explicit independent-profile mode. New profiles in this mode get private copies rather than live writable links to stock or peers. Preserve existing modes until an explicit qualified adoption selects the new mode.
- Seeding copies selected configuration categories and their home-local assets. It does not automatically import history, clone stock's Codex login, or transfer runtime control authority. Preserve existing valid profile authentication through supported native storage behavior.
- Inventory supported configuration rather than assuming only the original settings/skills/rules categories. Copy or remap home-local references and report intentional external dependencies or unsupported items. Preserve unrelated configuration.
- Use an explicit directional sync plan and per-destination, per-category baselines. Apply nonconflicting source changes; preserve destination-only edits. Conflicted entries remain unresolved until selected resolution, without blocking unrelated safe updates or advancing their baseline falsely. Source deletions propagate only when explicitly selected.
- Keep snapshots, operation identities and receipts outside live stock configuration. Detect changed inputs before applying their effects. Retries reuse valid outcomes; uncertain effects require reconciliation. Preview/apply, partial results and conflict reporting share one semantic contract across transports.
- Reuse MCP connector authentication only through its supported operator-level scope. Definitions and sign-ins are separate categories; do not manufacture credential sharing by linking mutable token files. Apply permitted sensitive connector settings privately, redact previews/results, and preserve destination Codex authentication and runtime control state.
- Adapt history discovery and transfer to a shared-stock source or destination as well as independent profiles. Use supported native exports/imports or consistent snapshots. Do not share writable databases, overwrite running destination history, or require unrelated stock sessions to stop merely to copy selected conversations.
- A copied ongoing conversation includes a clearly identified saved boundary. Exclude unfinished or unsupported material with an explicit per-entry outcome. Preserve original source identity/revision and known lineage. Do not infer new goals, grants or resource allowance from importing conversation content.
- Reuse the existing destination copy for unchanged source revision. When the source has advanced, create a new linked destination snapshot and retain all prior copies and destination work. Do not merge or overwrite diverged conversations automatically.
- Configuration changes apply to the next launch unless the operator selects a supported profile-scoped reload. Do not restart stock, refresh sibling profiles or interrupt running work as an implicit consequence of sync.
- Adopt existing profiles using a preview, consistent backup/rollback custody and explicit activation. Preserve history, local settings and supported sign-ins while materializing private writable state. An incompatible existing layout needs a specific repair path; it must not trigger a global stock migration.
- Repair launcher/build-registration and watcher readiness for the selected qualification targets as part of making this mode operational. Observe actual executable/backend identities and verified limit/refresh outcomes rather than treating source installation, a version label or a listed tool as acceptance.
- Extend the existing generated command contract, help, completion and transport adapters. Exact command spelling follows the implemented tree; this spec does not advertise unimplemented commands.

## Testing Decisions

The agreed primary seam is the existing public controller operation boundary used by CLI, API and MCP. Tests assert observable profile, configuration, transfer and readiness outcomes rather than private methods, internal call counts or storage layout. Runtime acceptance then verifies actual stock/profile behavior through installed launchers and native interfaces.

Prior art includes account/configuration public regressions, history-import and recent-batch tests, profile concurrency and migration/rollback acceptance, real-client WSL/PowerShell parity, scoped refresh and self-limit checks. Extend those seams instead of building a separate mock application or a collection of layer-only tests.

Required behavior matrix:

- Stock account A to B to A retains the same history/configuration store and launcher behavior. Authentication changes alone do not reset sync baselines or reattribute saved history.
- Seed two profiles and independently edit stock and each destination. Assert isolation, selected-category sync, preserved overrides, explicit conflicts, repeat-safe retries, partial results and opt-in deletion propagation.
- Copy hooks/assets and verify that actual execution resolves the intended profile-local resources; exercise changed source paths and deliberate external dependencies.
- Verify supported shared MCP sign-in behavior and independent Codex account login without exposing credentials in fixtures or receipts. Unsupported connector scopes are visible, specific outcomes.
- Transfer individual and recent-N conversations stock to profile, profile to stock and profile to profile. Cover completed and supported ongoing sources, snapshot boundaries, unchanged-source deduplication, advanced-source new snapshots, destination divergence, partial unsupported entries and ambiguous-response reconciliation.
- Adopt an existing linked/shared profile, preserve supported sign-ins/history/settings, and verify rollback and source preservation. Exercise changed identities and concurrent writers at the relevant selected targets rather than excluding all stock activity.
- Run ordinary stock alongside the personal Wake profile, then add a second independent profile. Observe actual executable/backend/account identity and test normal chat/resume, imports, MCP/hooks sync, voluntary limits and selected-profile refresh.
- Check the same operation semantics via CLI/API/MCP and actual WSL/PowerShell. Include generated help/completion and inspectable failure/remedy messages.

Start with synthetic disposable state and zero external model calls. Real-profile acceptance follows the approved sequence on explicitly identified test conversations under the operator's standing scope; record any real model calls separately. Preserve unrelated sessions, existing budgets and control state. Passing this matrix qualifies these capabilities, not every Wake feature or an unexecuted comprehensive suite. Run applicable checks locally under the no-paid-hosted-CI policy, retaining exact commands, source/package identity, failures and environment differences.

## Out of Scope

- Replacing plain codex with the modded harness, migrating stock into private per-account stores, or changing its ordinary logout/login behavior.
- Continuous background mirroring, default bidirectional sync, implicit deletion propagation, or automatic merging/overwriting of diverged conversations.
- Blind credential-file cloning, sharing writable history databases, transferring active goals/grants/allowances, or resetting cumulative usage through imports.
- Rebuilding or redesigning every Wake capability, native Windows compilation, broad operating-system migration, externally exposing MCP through a new OAuth connector, or resuming parked OpenClaw work.
- Runtime activation, authentication changes, credential/session copying, watcher starts, or deployment performed merely by publishing this specification.

## Further Notes

The ten interview recommendations were accepted, and the operator explicitly selected specification publication. This spec supersedes conflicting operating-mode assumptions in the earlier concurrent-account design for the shared-stock-home mode. Related issues #369, #371 and #380 retain their existing state; this publication does not close them or claim their broader acceptance.

Historical readiness observations are evidence of gaps to recheck during implementation, not permanent claims about the current runtime. Source implementation, disposable qualification, working-profile activation, merge and deployment remain distinct evidence boundaries. The retained native0.167 package and Plan0204 release-driver evidence may be reused after fresh identity verification; historical compiler provenance remains unknown where it was not recorded.

Owner: ecochran76 / primary coordinator. Classification: enhancement. State: ready-for-agent. Plan0205 is the execution/design locator. The next phase is a dependency-linked implementation ticket breakdown; this specification itself is not an implementation-completion claim.

Memory disposition: forbidden; no explicit memory-write request.

## Execution ledger

Integration branch: feat/independent-profiles-0205. Base: 0f469f3724f88f4e607f18beb2e78dd6b8615b0b.
Worktree: codex-wake-stock-home-0205. Scope: #488, all 42 stories.
WIP limit: three implementation lanes including primary; shallow workers only.
Review bound: one broad Standards/Spec review against recorded base; one bounded TDD remediation, then focused verification only.
Tracker closure follows validated integration outcomes, separately from release/activation. No merge/deployment in this packet.

| Unit | Blockers | Owner | State | Write scope |
|---|---|---|---|---|
| #489 stores/seeding | none | primary | validated domain seam | controller_accounts, codex_profiles config and independent store owner; tests |
| #490 adoption | none | /root/adopt205 | integrated; 25 focused PASS | controller_migration and adoption helper; migration tests |
| #491 readiness | none | /root/ready205 | integrated (runtime join pending) | selected readiness owner; readiness tests |
| #492 config sync | #489 | /root/sync205 | validated domain seam | configuration sync owner and tests |
| #493 history | #489 | /root/history205 | validated domain seam | history discovery/import and tests |
| #494 parity | #489–#493 | /root/parity205 | running | command contracts/adapters/generated docs |
| #495 qualification | #494 | primary | pending | installed/runtime acceptance and receipts |

Shared contract owner: primary. Extend ControllerAccounts; store records carry stable store_id, kind (stock/profile), home, independent boolean and observed account separately. Stock identity is stored in Wake metadata, never auth-derived. Configuration engine consumes resolved store records. Preserve legacy default mode. Public operations are wired by parity owner after domain owners stabilize; domain public execute methods are the initial test seam.
Worker branches start from the recorded integration checkpoint; no nested workers or working-account live effects. Worker red/green command receipts and commits are integrated serially. Source changes must not clone auth or control state. Native package effects first qualify UID1017; no paid CI.

### Checkpoint 2026-11-07

#489 integrated 9ee1d157045c8bfd6bdebca76f4043e89b3bb72d. Public account seam red: unsupported stores.register; green: test_independent_stores.py 1 passed, test_controller_accounts.py 8 passed. Commands: PYTHONPATH=src /home/ecochran76/workspace.local/codex-wake/.venv/bin/python -m unittest discover -s tests -p <file>. Raw red/green logs /tmp/cw205-stores-{red,green}.log and /tmp/cw205-accounts.log. No installed/native claim. Sync baseline and detailed categories belong #492.
#491 worker e092695 +36a2d96 integrated as ddc1ba6 +10cee78; primary reran test_account_*py: 7 passed1.589s. Actual backend and watcher read-only owners used; native limits/refresh and transport guards remain join gates. Explicit caller paths must not become remote file inspection authority.
#490 worker /root/adopt205, branch feat/profile-adoption-490, base258b823; first turn runtime failure network permission revoked, resumed same owned state. #492 /root/sync205 branch feat/profile-sync-492 base9ee1d15 owns configuration engine and profile_stores helpers. Workers use shared existing Python venv, not nonexistent worktree .venv. No ticket closed yet; all seven creation receipts in user-scoped spec0205/tickets.json.

### Adoption integration checkpoint

Worker69531b9 and afec766 integrated as6b9e426 and a42458c. Primary focused public migration/adoption regression: 25 PASS5.614s, command PYTHONPATH=src:tests /home/ecochran76/workspace.local/codex-wake/.venv/bin/python -m unittest test_controller_adoption test_controller_migration -q. Actual copied hook execution, private MCP values/redacted receipts and rollback verified. Explicit native/credential state and unsupported nested links stay under existing owner. Pinned ruff0.14.2 undefined-name check on changed files PASS via /home/linuxbrew/.linuxbrew/bin/uv tool run. Initial venv ruff absent; no source failure hidden.
Review comparison point requested asynchronously per skill; no answer yet, no broad review started. All issue states remain open until integration/runtime joins. Three-worker implementation fan-out ended adoption; primary may resume implementation alongside sync/history.

Focused controller checkpoint: 195 PASS72.859s at6b9e426; evidence ../evidence/plan0205/checkpoint-validation.json. Warning: existing websockets deprecation only. This precedes adoption follow-up/sync/history and does not replace affected final checks. Live read-only readback reconfirmed real460 personal profile cached credentials unverified and stock/modded registrations held; private readback stays outside Git. PowerShell5.1 executable available.

### Domain join 2026-11-07

Integration77be4a5. #492 worker9d2007d+ecc9cd9 integratedc02eed0+843e2e8; sync/seed/stock focused8PASS; pinned ruff PASS. #493 worker8505175+db92fb4 integrated7685a85+176906a; public history/auth/import/shortcuts/runtime37PASS19.020s. Initial primary test selection misspelled test_controller_shortcuts and failed import; corrected test_command_shortcuts run25PASS11.368s, then follow-up37PASS. First failures retained, not source regressions.
#489 dependency-inventory red KeyError; first integration omission retained as edbe04d, corrected77be4a5 with8PASS1.109s. Config values remain redacted; dependency entries identify keys and external/missing-local scope.
#494 dispatched /root/parity205, branch feat/profile-parity-494, base77be4a5, owned command/transport/generated-doc surfaces only. Primary owns #495 runtime join after parity. Domain source outcomes validated; native launcher/backend/limits/refresh and real clients remain separate #495 gates. Active implementation count now one worker plus primary coordinator; no overlapping writers. All workers inherit runtime configuration; effective model/effort and allocation attribution unavailable, no optimization claim.

### Runtime qualification checkpoint

Tracker #489/#490/#492 CLOSED after comment+state readback; private mutation receipts source-closure-receipts.json retain actor/source/state. #491/#493/#494/#495 remain OPEN. Source closure does not close parent or imply deployment.
Domain regression at1583961:206PASS70.468s, pinned ruff undefined names across src/scripts/tests/hooks PASS, policy wiring PASS. Local Python3.12.13; prepared isolated qualification-prefix3.12.13 and qualification-prefix3113.11.15 with matching frozen dependencies. No working installation.
/root/history205 supplemental native verification at source1583961 uses UID1017 isolated network, exact candidate0.167 hash56a10d48... Native active-source completed-prefix run4 PASS; run5 all directions/restart/advanced/recent2 PASS, lost-reply native reconciliation held instead of recovered (no duplicate effect). Failed fixture setup attempts retained; final owned processes empty. Candidate was used for all stores in initial matrix, so genuine stock-build coexistence is NOT yet claimed. Worker now verifying genuine stock package and narrow reconciliation mismatch. Root exec remains available despite worker intermittent EMFILE; no unrelated process cleanup authorized/performed.
/root/parity205 has shared schemas/adapters and local/native/OAuth parity tests; actual PowerShell fixture revealed missing stable store_id grant field, now in targeted validation. No broad review or remediation pass started. Review fixed-point answer pending.
