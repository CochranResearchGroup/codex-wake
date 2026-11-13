# LOCAL-P228 | Preserved policy and local edit reconciliation

State: CLOSED
Workflow: DONE; recovered and reviewed, integration pending
Work item: LOCAL-P228
Owner: primary / ecochran76
Priority: P1 repository continuity
Branch: chore/reconcile-preserved-policy
Base: 728b797f49e0c39730203cf6822a12ba8d6620a6
Dependencies: preserved four-commit policy lineage at13d11145
WIP limit: one serialized documentation/policy lane

## Current State

Current main lacks all ten surfaces changed by preserved commits11974e3a,
cb9dac25,26f44ac1,13d11145. Recover their exact final contents: selector v0.1.35,
its release/install metadata and three shared module changes, repo-local worktree
lifecycle and closeout text, exact governance hashes and original rollout note.
No broader profile adoption, code, runtime configuration value or installed
service changes. Remaining root edits are one config comment and two glossary
terms; carry them in a separate coherent commit after policy recovery.

## Scope and acceptance

- Compare against current main; preserve original branch and unique provenance.
- Recover only the original10changed files, byte-identical to13d11145.
- Keep one local policy identity per module, existing custom composition and
  scope; do not manufacture runtime or fleet adoption proof.
- Preserve source/selected-section hashes and selector content digest.
- Finalize comment-only cargo-signal wording and domain-only responsiveness/error
  definitions; no behavior changes or speculative ADR.
- Validate policy wiring, manifest hashes, selector enumeration, exact bundle
  digest, glossary uniqueness and whitespace; compare inherited planning errors.
- Review frozen diff against this contract and policies; checkpoint/publish branch
  for durable custody. No merge, deploy, issue mutation or hosted CI in this scope.

## Custody and validation

Original preserve/primary-policy-20261112 remains intact. Isolated checkout
protects the primary main anchor; close it after verified remote checkpoint.
Primary owns one lane, with no useful independent implementation to delegate.
Local Python3.12 checks; installed governance scope is current on original main,
while changed branch admission requires exact source verification. No service
restart to apply it. Graphiti discovery skipped: exact local/remote Git and
operator direction provide sufficient current evidence for this bounded recovery.
Memory forbidden: session developer requires explicit memory-update request.

Current checks: policy wiring PASS; source hashes PASS; selector enumeration
completed; planning audit retains exactly inherited0220/0224/0226 failures.
An initial ad-hoc hash checker expected a `sources` key; actual manifest uses
`governance_inventory`/profiles. Recursive declared-source verification passed.
No source or manifest change was made to accommodate the checker.

## Final evidence and remaining gate

[Validation](../evidence/plan0228/validation.md) records passing scope/hash/bundle/
wiring/TOML/glossary/lint/goal checks and3inherited planning findings,0new.
[Independent review](../evidence/plan0228/review.md): Standards0/Spec0; no remediation.
Two coherent commits retain policy recovery separately from comment/glossary work.
Branch publication establishes custody, not integration or runtime deployment.
Primary root edits may be removed only after exact branch equality and backup;
main remains canonical728b797f until a separately authorized merge. Original
preserve branch remains intact. Memory forbidden; zero Graphiti writes.
