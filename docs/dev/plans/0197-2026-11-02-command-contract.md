# Command contract and discoverability

State: CLOSED
Owner: primary / ecochran76
Ticket: LOCAL-0197 (this file; GitHub publication not requested)
Priority: next product usability slice
Branch: feat/command-contract-0197
Base: 6fb4fe7a9b6511a6bca4d090298cb85daf59ebf3
WIP limit: one primary implementation slice

## Current State

Reconciled 2026-11-12: PR461 integrated Plan0197; PR462 integrated Plan0198 at
`76ac7d918f414becc97e23b7212c3ac2422d114c`. The exact merged package was deployed
with all 238 Python members matched, installed completion and real-account
read-only recents. Existing daemon targets and stock binary were preserved.
See [deployment receipt](../evidence/plan0198/deployment.json) and RUNBOOK's
2026-11-02 command-contract/shortcuts deployment entry. This is recorded delivery
evidence, not a fresh installed-runtime readback or broader live-account acceptance.

## Historical source qualification

Five local tickets are implemented, integrated and validated on
feat/command-contract-0197. Product source24e4cc1; all local tracker states DONE.
Shared help/reference/coverage, first22operation schemas, sanitized status,
typed/interactive workflows and auto-installed completion are delivered.
Both Python versions passed240presubmit tests/16checks atc0fafa2. One broad
Standards/Spec review accepted two completion blockers; one bounded TDD pass
resolved both, followed by25focused checks/version and exact final installed
wheel qualification (236Python members equal). No merge/release/deployment or
working shell/account changes. See [ledger](0197-execution-ledger.json) and
[acceptance](../evidence/plan0197/acceptance.json). Earlier environment failures
remain recorded; this is not a claim of clean first-pass comprehensive testing.

## Desired outcome and confirmed decisions

1. Establish a Wake-wide command contract; deliver accounts, daemons and history
   first, including configuration/build operations required for those workflows.
2. A shared declarative operation definition drives argument schemas, help,
   reference documentation, completion and API/MCP mappings. Keep execution in
   existing owners. Adapters may differ in presentation and caller admission,
   while sharing domain semantics. Declare local-only and deferred surfaces.
3. Supported remote operations preserve argument meanings, result/error meanings,
   exact target checks and idempotency across CLI/API/MCP. Equal alias counts
   alone do not establish parity. Preserve native stdio versus JSON presentation
   where declared, with equivalent outcome semantics.
4. Existing commands/scripts remain compatible. Add named flags for common
   workflows while retaining advanced JSON inputs and explicit pins/intent keys.
5. Common interactive commands resolve and pin the selected target, show impact,
   and confirm interruption. A replaced target is refused, never silently
   re-resolved. Scripts retain explicit target pins and idempotency keys;
   unattended execution must not gain implicit interruption approval. Uncertain
   outcomes are reconciled under the original intent, never blindly replayed.
6. Bash/Zsh completion suggests commands, flags and locally registered account
   names. No provider requests, service starts, credential reads or mutations.
7. Supported installation paths automatically install and activate completion,
   with opt-out. Use standard user completion locations; add a small Wake-managed
   startup block only where needed. Preserve unrelated shell configuration;
   updates refresh owned content and uninstall removes only unchanged owned
   files/blocks, retaining user edits with an explanation. Explain reload needs
   for already-running shells. Package build/import must have no shell effects;
   explicitly document package-manager routes that cannot run user installation.
8. Authorized API/MCP callers can observe sanitized authentication state, identity
   and plan where available. Never disclose credentials or initiate login/token
   refresh. Keep interactive sign-in and credential entry local. Report unknown,
   stale and unavailable evidence explicitly rather than treating cached identity
   as current authentication or provider access proof.

## Scope and non-goals

First delivery covers the named account/daemon/history workflows, generated
reference/help/completion, supported installer integration and behavioral
transport checks. Publish coverage and exceptions for the wider tree; do not
claim the remaining commands are migrated. Preserve existing target/resource
and account/conversation terminology in GLOSSARY.md; no generic programming
terms or implementation decisions are added to the glossary.

No automatic global launcher cutover, existing-account migration, credential
copying, provider model experiment, old-job/goal resume, memory write, hosted CI,
merge or deployment is authorized by this plan. No second execution owner or
replacement account registry. Existing real-account trial evidence is private
and must not be copied into repository fixtures.

## Delivery order and dependencies

Primary owns serialized shared definitions, compatibility, admission semantics
and integration. Independent documentation/completion renderers can be developed
after their input contract is fixed; no delegation is required for this plan.

- Slice A: account list/resolve/status as the first visible vertical slice;
  shared definition produces useful help/reference, CLI/API/MCP results and
  sanitized authorized status. Prove secret-free/no-refresh behavior.
- Slice B: full first-delivery command coverage, typed common arguments and
  safe interactive target resolution. Preserve advanced script interfaces.
- Slice C: parser/definition-derived Bash/Zsh completion with installation,
  activation, upgrade and uninstall in disposable user homes. Do not install
  unfinished completion into the operator's live shell during qualification.
- Slice D: installed compatibility/parity verification and explicit coverage
  report for migrated, local-only and deferred commands; one bounded review.

Each implementation slice requires its own compact acceptance evidence before
advancing. Resolve overlap with current issues/PRs before implementation and
register the implementation lane under existing repository policy. LOCAL-0197
owns the outcome until deliberate tracker publication avoids duplication.

## Acceptance criteria and definition of done

- First-delivery arguments have meaningful descriptions, types, defaults,
  examples and effect/confirmation guidance visible in installed help.
- Generated reference and completion reflect current definitions; a local check
  detects stale generated files and missing transport mappings/exceptions.
- Behavior checks cover result/error equivalence, authorization denial, target
  replacement, idempotency conflict/repeat and uncertain-result non-replay.
- Sanitized auth observation excludes secrets and refuses provider login/refresh;
  completion remains local/read-only and uses the selected registry/root.
- Fresh/repeated install, update, opt-out and uninstall preserve user shell edits;
  actual Bash/Zsh completion works in disposable shell sessions. Noninteractive
  installs are deterministic and explain any activation that cannot be completed.
- Existing public CLI invocations and machine interfaces remain compatible;
  declared changes are documented without weakening controls.
- Run focused checks for each changed seam, applicable local presubmit, then
  installed workflow qualification. Record commands, source, duration, failures,
  exclusions and environment differences. No paid hosted CI or broad test reruns
  without a changed risk. No new provider prompts for documentation work.
- Final artifacts distinguish source completion, integration and installation.
  No ordinary operator sessions or unrelated services are interrupted.

## Historical source-only terminal state

All five local tickets DONE; no unresolved accepted findings. Review1 and
remediation1 are consumed. Keep worker worktrees clean and recoverable. A later
integration/release decision is separate from local ticket closure; do not reopen
broad review or start additional hardening merely because the branch is local.
