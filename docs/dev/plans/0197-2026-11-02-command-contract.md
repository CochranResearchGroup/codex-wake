# Command contract and discoverability

State: OPEN
Owner: primary / ecochran76
Ticket: LOCAL-0197 (this file; GitHub publication not requested)
Priority: next product usability slice
Branch: feat/command-contract-0197
Base: 6fb4fe7a9b6511a6bca4d090298cb85daf59ebf3
WIP limit: one primary implementation slice

## Current State

The operator confirmed all eight interview decisions in conversation, including
completion installation and shell activation. Design interview complete;
implementation packet is open. This file is the local work item and execution
contract; it does not claim integration, release or runtime activation.

Installed source6fb4fe7 has369 parser nodes whose help renders, with1575 of2020
argument definitions lacking explanatory help text. The portable controller has78
operations and78 matching OAuth MCP aliases, with no missing/mismatched entries.
These are structural observations, not complete behavioral parity proof. Legacy
profile helpers have handwritten Bash/Zsh completion; the Wake command tree does
not. Existing owners and account/daemon workflow docs are authoritative inputs.

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

## Next bounded action

Locate existing operation/tool metadata and installer ownership, choose the
smallest shared-definition seam for Slice A, and name its observable acceptance
before implementation. Test no-refresh auth observation at a valid seam; native
account/read can involve remote workspace routing, so refreshToken=false alone
is not proof of a purely local probe. Do not promise stronger evidence than the
selected observation mechanism establishes.
