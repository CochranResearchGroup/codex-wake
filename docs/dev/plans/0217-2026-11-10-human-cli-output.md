# LOCAL-P217 | Human-friendly CLI output

State: CLOSED
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

CLOSED. PR549 merged as1a651e073d7a0f5f7a8200d49074af2a22332c07; exact merged
0.22.0.dev3 wheel deployed at
`~/.local/share/codex-wake/releases/0.22.0.dev3-1a651e0`.
All305 Python members match source/wheel/install;29 changed members are CLI
adapters/presenter, no native owner changes. Nine launchers verified, real account
list is readable, explicit JSON complete and fresh Zsh completion registered.
Ten protected files,22 native processes and stock preserved; no native/provider
calls. Existing HTTP controller stale identity remains unchanged. Prior complete
package and tested rollback helper retained. See `deployment.json` under plan evidence.

Final release qualification:18 exact merged-package installed checks PASS11.610s;
37Python3.11 checks PASS15.733s. Full2338-test run retained one environment setup
error (missing installed launcher); its exact affected check passed in the
qualified installation. No product/assertion change or full-run retry to erase
that result. Independent Standards and Spec review has no remaining blocker.
See `release-validation.md` for commands, limits and earlier evidence.

Six inactive remotely backed checkouts archived with branches retained;50missing
registrations pruned. Active/dirty/unpublished/native/observer/Plan0216 trees
preserved. Main synchronized after removing only this task's exact verified dirty
paths; root config/GLOSSARY and Plan0216 work remain untouched. Final release
checkout will be removed after its clean published closeout is merged.
Memory disposition: forbidden by session developer instruction; no explicit
memory-update request. Non-write receipt and full deployment/custody/rollback
artifacts remain outside Git in the user-scoped qualification directory.

## Definition of done

Named CLI and affected checks pass locally; exact merged package is deployed with
readable accounts, complete JSON and fresh Zsh completion. Review, environment
limitations, retained initial failures, rollback and safe worktree custody are
recorded. Native sessions, protected state and unrelated work remain preserved.
