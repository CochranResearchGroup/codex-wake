# LOCAL-P217 | Human-friendly CLI output

State: OPEN
Ticket: https://github.com/CochranResearchGroup/codex-wake/issues/548
Owner: primary
Priority: P1
Dependencies: none
Branch: feat/human-cli-output-217
WIP limit: one

## Outcome and acceptance

Operator reports `accounts list` dumps internal JSON. Make human-facing CLI
results readable by default with explicit `--json` preserving machine envelopes.
Lists should be aligned tables with meaningful columns, empty lists explanatory,
details readable labels, errors clear with unchanged failure codes. No terminal
color dependency, no truncation of identifiers or loss of machine metadata.
Preserve API/MCP/SSH frames and explicit stream/transcript contracts. Document
script migration and validate through the public CLI, including redirected output.

## Scope and execution

Primary owns output presentation and CLI adapters, focused tests, docs and local
qualification. One read-only audit worker checks compatibility for accounts and
controller callers; it owns no files. Serial critical path: public CLI red test,
shared presentation plus accounts, then affected adapters, compatibility checks,
installed-wheel smoke. No provider actions, account mutations on working host,
daemon/native binary upgrades, paid CI, or production restart. A private package
install qualifies console entrypoints; working installation is separate.

## Current State

Operator now authorizes PR, merge, deployment and worktree cleanup. Release slice
is isolated at `/tmp/codex-wake-p217-release`, based on fetched origin/main
fa2363c. Native binaries/owners will remain unchanged; deploy only the Python CLI
package and regenerate Zsh completion. Existing native sessions and monitor state
must be preserved. PR549 is published. Six inactive remotely backed checkouts archived and50stale
registrations pruned with refs retained; active/unpublished lanes preserved.
Final source and rollback qualification pass; working rollout awaits merge.
See `docs/dev/evidence/plan0217/release-validation.md`.

Prior implementation qualification:

CLOSED for source implementation and private installed-wheel validation;
unreleased and not deployed to the working host. Shared presentation covers the
adapters listed in `docs/agents/cli-output.md`; machine consumers explicitly
select JSON. All three independent review findings corrected. 327 focused checks,
69 compatibility checks, five private-installed presentation checks pass. Full
2338-test discovery recorded deterministic consumer/header failures; all affected
modules reran after corrections: 64 checks PASS. Full discovery was not repeated.
Active planning audit, undefined-name lint, compilation and generated-reference
checks pass. See `docs/dev/evidence/plan0217/validation.md` for complete evidence.

No working-host deployment, commit or push. Receipt:
`~/.local/state/codex-wake/qualification/plan0217-20261110/receipt.json`.
Graphiti discovery skipped: current source and supplied example sufficient.
Memory disposition: forbidden by session developer instruction (no explicit
memory-update request); non-write receipt retained outside Git. Preexisting
completion patch and unrelated Plan0216/GLOSSARY/config changes preserved.

## Definition of done

Named CLI tests and affected existing checks pass locally; private installed wheel
shows human accounts output and unchanged explicit JSON; docs describe compatibility
and commands/results/environment/source are recorded. Broader command coverage is
reported accurately rather than inferred from shared helper tests.
