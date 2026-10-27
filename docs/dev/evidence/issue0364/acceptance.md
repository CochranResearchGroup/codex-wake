# Native orphaned custom-output recovery / #364

The installed custom development daemon panics on a retained custom tool call without its output. The assertion unwinds before existing aborted-output recovery, leaving a turn without a terminal event. Stock release behavior logs and recovers. This is separate from resource enrollment, quotas and governor activation; why the original output was lost remains unresolved.

## Source and artifact identity

The installed daemon package and immutable modern0.164 baseline fbfe287f4d738946ed3b158da9d9081db01ed039 have matching CLI, code-mode-host, bwrap and rg hashes. The original CLI hash is31b27c12fb4639b4568002cde21a6ab75d76f29cab8c32d0e1f137bb2c7c640b. Thus the repair is based on the actual installed source family, retaining existing native feature patches.

Native commits f9bbbb034cac95ceb0020c12ba196761aaf456b9 and b706004728800f4cba08e5554b854f1bd5461f25 change recoverable missing custom output to informational logging, retain aborted-output synthesis, exercise ordinary/inherited calls in debug, and add a persisted-history resumed-turn regression. The complete bounded diff is native-orphan-recovery.patch, generated with zero context to avoid blank patch-context lines being treated as whitespace in the outer evidence diff. Apply to the exact baseline with git apply --unidiff-zero; reverse-apply verification against the final native tree passed. No API shape, allocation authority, existing output or synthetic ID derivation changes.

Canonical packaging uses the supported build_codex_package.py with explicit prebuilt candidate CLI and unchanged qualified baseline helpers, targetx86_64-unknown-linux-gnu, version0.164.0. Private package native/ar2-orphan-b706004728 is self-contained and NOT selected for shared use. Candidate CLI SHA2560696309a7cf4f140287901079a15117553701b5813a2f820282e21fde509776c. candidate.json records all executable hashes and exact boundaries; package version alone is not build identity.

## Red and green

Commands run in the native worktree through repository just test, with CARGO_TARGET_DIR pointing to a dedicated temporary repair cache, CARGO_BUILD_JOBS=2 and CARGO_INCREMENTAL=0:

- `just test --cargo-profile dev-small -p codex-core --lib -E 'test(normalize_adds_missing_output_for_custom_tool_call)'`: RED3selected,2pass/1fail; automatic retry also failed. After source fix, GREEN2pass in0.044s. The obsolete debug should_panic test was removed; the ordinary-case recovery test now runs in debug too.
- `just test --cargo-profile dev-small -p codex-core --lib -E 'test(context_manager::)'`:95PASS2.170s,2693unselected. This is an affected component selection, not the full workspace.
- `just test --cargo-profile dev-small -p codex-core --test all -E 'test(resumed_custom_call_without_output_recovers_and_completes_turn)'`:1PASS0.945s,2565unselected. It persists a synthetic orphan after a saved seed turn, resumes the durable history, asserts explicit aborted output in the public provider request and observes TurnComplete. Historical tool input must not be replayed.
- `just fmt`, whitespace check and canonical package build succeeded. Full workspace suite was not run; native policy requires separate approval for that broader lane. An unrelated existing unused import warning remains outside the patch.

Retained setup failures are not product reds or passes: initial test path preparation used the wrong working directory; an integration target was named suite instead of all; the first integration fixture had no materialized rollout; a later in-memory-only orphan was correctly ignored by the durable store. The final fixture writes through the supported persisted-rollout append seam. Private logs retain those failures and their corrections. No shallow fixture result is represented as runtime recovery.

The installed-binary offline replay initialized a separate app-server with isolated home and loopback-only provider, copying operator-local original history without mutating it. Baseline custom original/minimal histories panic with no provider request; baseline stock and paired custom controls proceed. The packaged candidate passes BOTH minimized and original full-history scenarios: no panic, one loopback request carrying recovered aborted output, and explicit failed terminal turn from the fixture's intentional HTTP400. That failure is deterministic fixture termination, not external inference or successful business work. Owned replay processes were terminated and reaped.

## Review, cleanup and remaining gate

Primary Standards and Spec axes were reviewed independently against fbfe287f4d and issue364. The source change is narrowly scoped and uses existing logging/serialization; no blocking source finding remains after the persisted-fixture correction. The original loss of an output and other invariant-panic paths are not claimed repaired. Private source transcripts and provider request bodies remain outside Git.

The temporary8.18GiB native build cache was removed through supported Cargo clean after all builds/replays finished, with no live references. Net available bytes increased8781950976 during that cleanup; all retained candidate hashes were reverified afterward. The previously cleaned53GiB cache remains untouched. Build cost is paid again if rebuilding later.

The shared native daemon was NOT restarted or replaced; the live AR2 session was NOT edited, interrupted or resumed. Goal governor remains masked/inactive; no goal or resource renewal occurred. The current source-thread resident Wake MCP catalog remains0.22.0.dev1, separate from installed Wake commands/skills0.22.0.dev2. User approval is required before applying the qualified package to the shared daemon: the prior continuation explicitly excluded a shared native restart, and update may interrupt active tabs. Supported future cutover command is the candidate's `app-server daemon update --from-cli --yes`; it has NOT been executed. Preserve current conversation/goal state and verify native identity/continuity if that action is approved.

Issue364 and plan0177 remain OPEN for this shared cutover. Handoff continuity issue365 is separately merged/installed and closed. No old exhausted campaign, expired follow-up, provider experiment or business review was revived by this repair.
