# Account open/resume and recent conversation copying

State: CLOSED
Owner: primary / ecochran76
Ticket: LOCAL-0198 (this file)
Branch: feat/account-shortcuts-0198
Base: 6a290eef7dbf7b18fa3cdcd03f48f3d6286d98d1
Dependency: Plan0197 integrated through PR461; historical stacked base retained above
Priority: next operator usability slice
WIP limit: one primary slice

## Current State

Reconciled 2026-11-12: PR461 integrated Plan0197; PR462 integrated Plan0198 at
`76ac7d918f414becc97e23b7212c3ac2422d114c`. The exact merged package was deployed
with all 238 Python members matched, installed completion and real-account
read-only recents. Existing daemon targets and stock binary were preserved.
See [deployment receipt](../evidence/plan0198/deployment.json) and RUNBOOK's
2026-11-02 command-contract/shortcuts deployment entry. This is recorded delivery
evidence, not a fresh installed-runtime readback or broader live-account acceptance.

## Historical source qualification

LOCAL-0198 DONE on feat/account-shortcuts-0198. Sourcebdb2114 implements
open/resume, explicit shortcut default root, read-only recents and frozen recent
copy batches through existing owners. Both Python versions passed245presubmit
tests/16checks ate3a61e7; the final private-directory guard fix then passed53
focused tests/version. Exact final wheel and238Python members match source and
installed UID1017 prefix. Actual native reopen/last/open, multi-copy, same/new
batch dedup, changed-source partial outcome and no-repeat behavior passed with
external networking blocked. Both owned daemons stopped; fresh process census
empty. Plan0197 remains closed with its consumed review/remediation counts.
See [acceptance](../evidence/plan0198/acceptance.json). No working deployment.

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

## Historical source-only terminal state

Implementation and source/disposable-installed acceptance complete. Local ticket
DONE. Keep the stacked dependency on validated Plan0197 visible until integration;
merge, release, operator default-root selection and working installation remain
separate. Older source histories/formats remain constrained by existing owners.
