# Account open/resume and recent conversation copying

State: OPEN
Owner: primary / ecochran76
Ticket: LOCAL-0198 (this file)
Branch: feat/account-shortcuts-0198
Base: 6a290eef7dbf7b18fa3cdcd03f48f3d6286d98d1
Dependency: validated Plan0197 source (stacked local branch; origin/main remains6fb4fe7)
Priority: next operator usability slice
WIP limit: one primary slice

## Current State

Operator clarified skim means source-preserving copy/transfer, with convenient
recent-history viewing as well. Requested open and resume shortcuts preserve
plain codex as stock with separate private account daemons. Implementation
starting; Plan0197 remains closed, its review/remediation counts unchanged.

## Scope and acceptance

- Local human `open ACCOUNT`, `resume ACCOUNT [UUID|--last]`; choose registered
  account/build, pin internally and reuse existing launch owner. No new prompt,
  goal enrollment, credential copying, daemon hot-update or account reassignment.
- `configuration default-root ROOT` explicitly persists a user-local default for
  these shortcuts. Global --wake-root wins. No root discovery or legacy-root
  behavior changes for unrelated existing commands; no codex alias/function.
- `history recent --owner ACCOUNT --limit N` views latest activity metadata.
  Extend existing history.search with optional sort=recent and bounded limit,
  keeping existing admission and API/MCP owner behavior. Sort before transcript
  admission so older large histories cannot crowd out recent results. Timestamp
  provenance and partial/unsupported discovery remain visible.
- `history import-recent --owner SOURCE --destination DEST --limit N` freezes
  latest N selected sessions before confirmation. Copy through existing single
  import owner; no bespoke native DB writes, moves, goals or credential transfers.
  Read-only preview is the default for noninteractive calls without explicit
  confirmation. Retain private batch ID, exact source/destination pins and child
  intent keys; `--batch ID` reuses that frozen intent and never selects newer
  history. Unknown entries stay held under the existing journal, never reforked.
  Report copied, unsupported/failed/uncertain entries individually. Preview does
  not start daemons; existing import requirement of two running daemons remains.
- Human open/resume and batch confirmation are local orchestration over existing
  owners, explicitly declared CLI-only shortcuts. API/MCP may call history.search
  (limit/sort), builds.launch and history.import under their existing scoped
  grants. Generate help/reference/coverage; completion learns new commands and
  account names. Preserve script interfaces and native process exit statuses.

## Validation and definition of done

Use TDD at public CLI/native-process and history owner seams. Prove selected
account/build, exact UUID/last arguments, default-root isolation, timestamp
ordering/limit before reads, source immutability, frozen batch retry identity,
partial outcomes and refusal of unsafe batch paths. Run focused affected suites
on3.11/3.12, installed provider-free command qualification and applicable local
presubmit. No paid hosted CI, working installation, real histories/credentials,
provider model turns, old-job resume, merge, deployment or memory write.

## Next action

Implement source-compatible recent ordering, then root/launch shortcuts and
frozen batch orchestration. Preserve unsupported import behavior rather than
silently expanding native format support.
