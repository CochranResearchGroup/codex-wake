# #380 source review — one round

Fixed base:289bb97ecf8a0382089819e4c4119bc5462e48d0.
Reviewed implementation:abdb91d3091fc8cba1cb7c83c7c22d4257563410.
Command:`git diff 289bb97ecf8a0382089819e4c4119bc5462e48d0...abdb91d3091fc8cba1cb7c83c7c22d4257563410`.

Standards axis: separate read-only reviewer; author of version-inspection slice,
so not independent for that slice, independent for migration implementation.
Spec axis: primary, against Plan0194/#380 and interruption/storage-preservation
requirements. Review does not count source fixtures as installed acceptance.

Accepted findings for the single bounded TDD findings pass:

- S1, P1, controller_migration.py124–129: configured account-home census uses
  absolute lexical paths. An idle client's CODEX_HOME alias can resolve to an
  affected home without matching it lexically and without open write FDs.
  Resolve runtime-home aliases before matching; unresolved ownership remains held.
  Independently found on both Standards and Spec axes; adjudicated once.
- S2, P1, controller_migration.py808–826: rollback validates replacement state
  only before its loop. A file written after that validation can be unlinked by
  a later rollback step. Revalidate exact replacement/backup state after each
  authorization guard immediately before removal. Preserve new private work.

Live preview still has real protected dependencies and incomplete writer census.
No review finding authorizes bypassing either hold, interrupting operator work,
claiming correct historical ownership or closing #380.

## Single bounded findings pass

S1 and S2 each reproduced as a failing public migration regression, then passed
after the fix. S1 uses a real idle subprocess with a symlinked CODEX_HOME; S2
writes private native state from the per-step authorization callback after the
initial rollback validation. Both processes/files belong to synthetic test homes.
Final focused suite:58 PASS in17.367s. Undefined-name and focused lint checks pass.
No second broad review or second findings pass was run.

Standards sources: code-review skill/Fowler baseline; policies0004/0005/0006/
0014/0016/0021; domain/code-discovery/runtime-proof guidance; Plan0194; frozen
base-to-abdb91d diff and migration tests.
