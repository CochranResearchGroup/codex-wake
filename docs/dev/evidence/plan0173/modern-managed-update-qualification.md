# Modern managed package qualification

The optional `--modern-managed-update` qualifier **passed** against final native source `3ab07eac61e3247524e66afcb3f9271a87725482`: real stock→GNU candidate→stock package replacement, scoped MCP isolation, canonical paginated notice/context and authentic stock rollback reads all passed. No model turns were used; nonzero accounting remains outside this fixture. Earlier failed runs and their causal oracle corrections are preserved below.

The modern path copies complete caller packages into the private fixture, invokes reference `app-server daemon start`, then actual reference `app-server daemon update --from-cli --yes`. It creates a paused reference-owned thread, snapshots its actual goal and rollout, updates through the candidate's real `--from-cli` command, reads the same baseline, exercises the existing selected-thread MCP refresh and no-turn notice checks, and rolls back through the frozen reference caller package's real `--from-cli`. It checks exact package files/modes, process executable SHA, peer UID/private CODEX_HOME, builtin updater-stop/pin effects, goal identity, conversations and raw rollout hashes. No manual current selection, history rewrite, resume workaround, custom success-path pinning, host installation, or model turn is introduced. Nonzero token accounting is explicitly **not proven** by this fixture.

## First bounded stock smoke

One stock-to-stock setup smoke ran using immutable stock MUSL 0.164.0 for both caller arguments. It stopped at its first terminal fixture error after 21.51 seconds:

`RuntimeError: modern managed endpoint escaped the private home`

Both reference start and actual reference `update --from-cli --yes` returned success. The latter reported status `updated` and the builtin pinned-package message. The baseline, candidate features and rollback were **not reached**. This is a failed run, not package lifecycle acceptance.

The error was an incorrect qualifier guard: modern transport intentionally exposes the private rendezvous as a symlink to a protected hashed shared socket (`codex-rs/app-server-transport/src/transport/unix_socket.rs`, `protected_socket_path`, lines 354–367 at native commit ea92904281f99180c24773c2fb597e60891213af). The corrected guard checks the exact private advertised rendezvous, owned socket, SO_PEERCRED UID, peer private CODEX_HOME, and exact executable SHA. That correction has **not been rerun**. No blind retry was made.

Artifacts (user-scoped; not copied into Git):

- Root: `/home/ecochran76/.local/state/cw-modern-smoke1`
- Receipt: `receipt.json`, SHA256 `418d97cf1e34fffbaf7c7eb0486a8f508e41fe268e8c1e6ce9ea4fe5d8cd711c`
- Log: `/home/ecochran76/.local/state/codex-wake/native-modern-0164/modern-stock-smoke1.log`
- Stock CLI SHA256: `b93f6811d3f653f0fb83be4050d857fb9abbb111dfa2ce160563327daff7f306`
- Frozen caller manifest SHA256: `328cc6b7d776fed066a3b475766ec01bd8b8f31d91e4955a5588f37ff9ddb51b`

Exact invocation (working directory is this worktree):

```sh
env CODEX_WAKE_QUALIFICATION_PARENT_NETNS="$(readlink /proc/self/ns/net)" \
 timeout 180 unshare -Urn sh -c 'ip link set lo up; exec "$@"' sh \
 /home/ecochran76/.local/share/codex-wake/releases/0.22.0.dev0-ce1ad93/bin/python \
 scripts/scoped_refresh_native_qualification.py --execute \
 --root /home/ecochran76/.local/state/cw-modern-smoke1 \
 --prefix /home/ecochran76/.local/share/codex-wake/releases/0.22.0.dev0-ce1ad93 \
 --managed-cli /home/ecochran76/.codex/packages/standalone/releases/0.164.0-x86_64-unknown-linux-musl/bin/codex \
 --rollback-cli /home/ecochran76/.codex/packages/standalone/releases/0.164.0-x86_64-unknown-linux-musl/bin/codex \
 --modern-managed-update
```

Cleanup receipt reported empty private-home process and toy survivor arrays. A fresh `/proc` census for the exact fixture root/private CODEX_HOME also returned empty after the run. The private daemon was stopped; no private updater survived. Host CLI, updater and resources were untouched.

## Static validation and remaining gates

Ruff 0.14.2 format/check, Python compilation, and `git diff --check` pass after the guard correction. CI was skipped as requested. New-candidate native execution, complete reference→GNU candidate→reference roundtrip, paused baseline cold-read compatibility and selected MCP/notice proof remain pending. If native cold reading requires a documented resume operation, stop and report the exact response before introducing that operation.

Memory disposition: `forbidden`; this bounded task authorizes the owned source/report and qualification artifacts, not a durable memory write.

## First actual candidate attempt: baseline guard failure

The first actual run used root `/home/ecochran76/.local/state/cw-modern-run1` and the same bounded command above, replacing the managed caller with `/home/ecochran76/.local/share/codex-wake/native/modern-0164-ea92904281-candidate1/bin/codex` and reference caller with `/home/ecochran76/.local/share/codex-wake/native/stock-0164-b93f6811/bin/codex`. It failed after 28.62 seconds **before candidate update** on `event_msg/thread_settings_applied`, a newly encountered stock baseline record rejected by the inherited history allowlist. Receipt SHA256: `0c0713a81ae27530103264b6d2eec24ddb4954691ef009ca16284c1ffe787271`. Real reference pin/package/socket/process proof passed; its updater list and latest marker were absent. No candidate execution, resume or history modification occurred. Cleanup and fresh owned `/proc` census were empty.

Full input package maps before/after are `modern-roundtrip1-inputs-{before,after}.json` in `/home/ecochran76/.local/state/codex-wake/native-modern-0164/`; maps are identical. Candidate CLI SHA256: `37d750ff09e3b47d1ceb0745c9f0b88adc2e4b21d67e27230a4055e28adcdcf5`; reference CLI retains the stock SHA above.

Upstream `protocol.rs:2329–2336` defines this as the thread-owned settings snapshot; `core/src/session/thread_settings.rs:129–151` emits/checkpoints it without a model turn. The modern-only allowlist now admits that exact event shape only for the native thread ID, private workspace and `owned_no_provider`. Legacy behavior and rejection of unknown events are retained. A focused temporary-rollout regression accepted this settings event and rejected task_started, token_count, unknown and foreign-owner events. Ruff passes. A fresh-root rerun was explicitly authorized after this known compatibility correction; its result is recorded separately below.

## Authorized corrected run: actual replacement completed, byte-preservation failed

Run2 used fresh root `/home/ecochran76/.local/state/cw-modern-run2`, the same command and frozen caller packages as run1, and stopped at the first different failure after 69.92 seconds. Log: `/home/ecochran76/.local/state/codex-wake/native-modern-0164/modern-roundtrip2.log`. Receipt SHA256: `08c077bad526c552694b29c0029c3028b8c03451d8a4729faae7fb1146006a59`.

The real reference start/pin, NEW GNU candidate `update --from-cli --yes`, and frozen reference rollback `update --from-cli --yes` all completed with matching complete package files, process executable, owned peer/private CODEX_HOME and builtin pin/updater-stop readbacks. Baseline thread `01a17631-4287-7bf0-827b-436eb553a2bc` and its full paused goal (including timestamps, tokenBudget 1000, tokensUsed 0 and timeUsedSeconds 0) remained identical and readable under candidate and reference rollback. No resume was needed.

The strict raw history comparison failed: baseline had three rows, candidate read had four and reference rollback read had five. Each added row is `event_msg/thread_settings_applied`; all three settings payloads are identical. Original session metadata and goal event remain present. Raw SHA values are:

- Reference baseline: `6be8b8a5e2395709fbcc56a4d9723a16276061a4a3d94ef4b0162fbc730175c1`
- Candidate read: `c48fdc3dfdf5b9996b22ea08f7a248cb6c66e32caaa32f375b689c64d52c5fa3`
- Reference rollback read: `d8d3aee2564d426d53176301c91a07b12156eb5c73876c02ed811e4efd8a555b`

The first error is `RuntimeError: pre-update stock conversation, goal or history changed`; the rollback verification reports the same error. This is **not a passing byte-preservation proof**. No normalization, rollout rewrite, manual resume, relaxed hash comparison or retry was performed. Selected two-thread MCP refresh/notice qualification was not reached. No model turns or nonzero token accounting were proven.

Full source input maps remain identical to run1's frozen before map; run2 after-map is `/home/ecochran76/.local/state/codex-wake/native-modern-0164/modern-roundtrip2-inputs-after.json`. Cleanup receipt and fresh exact-root/private CODEX_HOME `/proc` census are empty. The owned reference daemon was stopped and no private updater survived. Host CLI/updater/resources were untouched. Remaining decision: assess the upstream cold-read checkpoint behavior against the required raw-byte contract before authorizing any further execution or contract change.

## Append-only checkpoint oracle correction

The parent explicitly approved accommodating native append-only settings checkpoints while retaining original bytes. `core/src/session/thread_settings.rs:20–28` appends and flushes the settings snapshot; app-server thread/goal processors invoke checkpoint persistence. The modern oracle now requires the entire original raw byte sequence as an exact prefix and permits only appended, strictly validated `thread_settings_applied` events for the matching thread/private workspace/provider. It separately compares complete goals/counters and reads native history; raw hashes remain recorded as changed. It rejects file-set changes, truncation, rewrites, model/usage, unknown and foreign events. No rollout data is mutated. A focused temporary regression passed the accepted settings append and all six negative rewrite/truncation/model/usage/unknown/foreign cases. One further fresh-root run was explicitly authorized for this correction.

## Run3: package roundtrip passed; startup-count fixture failed

The explicitly authorized run3 used fresh root `/home/ecochran76/.local/state/cw-modern-run3`, unchanged command/packages, and stopped after 71.30 seconds at `RuntimeError: continuity or v2 proof failed`. Receipt SHA256: `361c284f4ca443a61c383f243629847775283a5aa85202b7aecc912398c441f5`; log is `modern-roundtrip3.log` in the existing user-scoped artifact directory.

`stock_to_candidate_preserved` and `modern_package_roundtrip_preserved` are both **true**. The authentic stock→GNU candidate→stock complete-package lifecycle, builtin pin/updater stopping, process/peer identity, same conversations/full paused goals/counters, exact original raw rollout prefixes and strictly validated settings-only appends passed. Raw hashes remain recorded as changed, with `rollback_rollouts_unchanged=false` accurately retained alongside successful `rollback_rollout_prefixes`. No resume/history mutation was used.

The only false continuity predicate is `exact_toy_startups`: the log contains v1 PIDs 3781256, 3781566, 3781621 and v2 PID 3781903. The inherited oracle expects exactly `[v1,v1,v2]`. All other continuity predicates pass:

- same thread IDs and complete goals are unchanged; native model turns are zero.
- Selected scoped reload dryRun returned `queued:false`; actual admission returned `queued:true` for selected thread `01a17634-51e7-7791-8632-be2fd963b864`.
- Selected toy response is exactly v2 and catalog includes `extra_v2`; peer `01a17634-524f-7dd2-8184-b6d7ba63ceab` remains exactly v1 without `extra_v2`.
- Before/after dryRun snapshots match, so inspection did not refresh either thread.

The modern fixture additionally loads reference baseline `01a17633-ed3f-79b3-a379-90dd66fdd27f` under candidate configuration v1 before creating the two selected/peer threads. Thus a third initial v1 process is consistent with the fixture's third resident thread. This attribution is an **inference**: the toy startup record only logs PID/version and does not yet record per-thread startup association. It is a fixture startup-count mismatch; observed selected refresh/catalog behavior passes. No unexpected metadata shape or functional refresh failure is demonstrated. Notice append/context proof was not reached because the strict count guard stopped the run.

Runtime inputs/initialization are retained in receipt `managed_lifecycle.rpc`, full before/after/inspection responses, root `home/config.toml`, `toy.py` and `toy-pids.jsonl`. The toy initialize response declares protocol version from the request, `capabilities.tools={}` and serverInfo version v1/v2. Candidate config invokes the owned toy script with version and PID-log arguments plus the installed Wake lifecycle MCP. Provider URL is loopback port1, retries zero, no credentials, network namespace loopback-only.

The complete source package map still exactly matches frozen run1 inputs; run3 after-map is `modern-roundtrip3-inputs-after.json`. Cleanup and a fresh exact-root/private CODEX_HOME process census are empty. Host processes/resources remain untouched. No fourth run or further fixture change was made. Next action is targeted startup attribution/oracle diagnosis, not another whole roundtrip. Static Ruff check/format, Python compile and diff-check pass; CI skipped.

## Final startup-accounting correction (not run)

The parent confirmed the additional resident baseline thread is expected and authorized a mode-specific exact count. The qualifier now records `expected_toy_startup_versions`: legacy/default requires exactly `[v1,v1,v2]`, modern requires exactly `[v1,v1,v1,v2]`. It does not use a minimum count or admit extra refreshes. A focused regression verifies both mode branches and rejects missing/excess v1 and excess v2 startups. Ruff and Python compilation pass. This correction is **NOT RUN**: the parent will choose the final rebuilt package before authorizing final qualification. All prior failed receipts remain unchanged.

## Final rebuilt package attempt: paginated notice-reader mismatch

One explicitly authorized final run used candidate `/home/ecochran76/.local/share/codex-wake/native/modern-0164-3ab07eac61-final1`, native source `3ab07eac61e3247524e66afcb3f9271a87725482`, CLI SHA256 `e0ea45eaf753ba89914cd8bcf8646baa92c4da0568a5d853f0a9652bb8ccf164`. The immutable stock reference is unchanged. The runner at b8ad589 was verified byte-identical to the parent activation-worktree script before execution. The same command used fresh root `/home/ecochran76/.local/state/cw-modern-final1`, final candidate path, and log `/home/ecochran76/.local/state/codex-wake/native-modern-0164/modern-final1.log`. It failed after 75.71 seconds on `RuntimeError: expected exactly one synthetic notice container`; rollback verification reported the same mismatch. Receipt SHA256: `00810e3b66e2234a57903207de99b498d0ceb9d7ea5eda41e22cda8b235e45e2`.

Stock baseline preservation, exact modern three-v1/one-v2 startup accounting, dryRun non-effect, selected v2 behavior/new catalog, peer v1 isolation, same thread/goal/counters and zero model turns passed. Actual candidate replacement and stock rollback package commands/process proofs completed. Full roundtrip acceptance remains withheld because the notice-history check failed.

The native notice append succeeded: `recorded=true`, `alreadyRecorded=false`, `modelContextAvailable=true`, `notificationPublished=false`. Selected get returned the exact event/text; peer get returned null notice and modelContextAvailable=false. However all three runner thread/start requests omit historyMode, so native responses use `historyMode=paginated` with `turns=[]`. The inherited oracle expects a synthetic container in `thread/read.turns`, which applies to the legacy shape. Raw selected history contains the exact external-supervision user context plus an `event_msg/item_completed` with matching thread_id, turn_id/event ID, AgentMessage ID and Text content; it does not use the older `agent_message` display event.

This demonstrates a fixture reader/oracle incompatibility with modern default paginated history and modern display-event storage. It does not demonstrate a failed notice append or context isolation. No final notice proof is claimed, and no raw history was rewritten. Proposed bounded follow-up: use native paginated items to validate the no-turn item (or explicitly select legacy history if that is the intended separate boundary), and validate the exact owned modern item_completed payload while rejecting unrelated/model events. No such correction or retry was performed in this task.

Complete final input package maps `modern-final1-inputs-{before,after}.json` in the existing user-scoped artifact directory match exactly. Cleanup receipt and fresh exact-root/private CODEX_HOME process census are empty; the owned stock rollback daemon was stopped and no updater/toy survivor remained. No compiler, provider, host CLI/updater/resource effect occurred. Source/report worktree is otherwise unchanged; CI skipped.

## Modern paginated oracle correction (runtime pending)

The parent authorized a modern-only correction after confirming native paginated notice restart tests. `ModernManagedFixture.notice_history` now calls the actual public `thread/items/list` API on the currently authenticated managed endpoint, on both candidate and reference rollback. Exact upstream protocol: `ThreadItemsListParams` accepts threadId, limit and sortDirection; `ThreadItemsListResponse.data` contains `ThreadItemEntry` with turnId, item, startedAtMs and completedAtMs. The modern reader requires paginated mode with empty `thread/read.turns`, one canonical agentMessage with stable event/item/turn ID and exact text, null start time and a recorded completion timestamp. Peer/baseline require no visible items. Pagination must be exhausted.

The raw proof separately requires exactly one stable external-context response_item and one owned item_completed/AgentMessage display record with exact content and matching public completion timestamp. It permits only the already validated settings checkpoints and goal records; all other records/model signals are rejected. Rollback uses the same public API and exact-prefix preservation checks. The legacy superclass is unchanged by this correction. No synthetic legacy container or forced history mode is introduced.

A focused temporary fixture regression passed canonical item/context/display and empty peer histories, and rejected task_started, token_count, unknown, foreign-owner display, mismatched raw item ID and mismatched public item ID. Ruff 0.14.2 format/check, Python compilation and diff-check pass. No package runtime was launched after this correction. Proposed final2 invocation is the final1 command with `--root /home/ecochran76/.local/state/cw-modern-final2` and log `modern-final2.log`, using the same final1 candidate/reference complete packages and original bounds; it requires explicit parent authorization.

## Final2 acceptance: PASS

The parent explicitly authorized one final2 run after the modern paginated oracle correction. It passed in **64.30 seconds**, process exit0, with fresh root `/home/ecochran76/.local/state/cw-modern-final2`, the same frozen final GNU/reference packages and original 180-second loopback-namespace bound. No retry occurred. Log: `/home/ecochran76/.local/state/codex-wake/native-modern-0164/modern-final2.log`. Receipt: `/home/ecochran76/.local/state/cw-modern-final2/receipt.json`, SHA256 `d8757161e272321c42cf3f42ad84a5e2703a5a1e867376baa59b4386dd7b013b`.

Verified acceptance predicates:

- Actual complete stock MUSL→final GNU CLI `e0ea45eaf753ba89914cd8bcf8646baa92c4da0568a5d853f0a9652bb8ccf164`→immutable stock `b93f6811d3f653f0fb83be4050d857fb9abbb111dfa2ce160563327daff7f306` package updates through builtin `--from-cli --yes`, package-file/process/peer/private-home identity and builtin pin/updater-stop readbacks.
- Reference-created baseline thread and full paused goal/counters/timestamps preserved under candidate and real stock rollback. Same selected/peer conversations and full goals remain readable.
- Exactly three v1 toy startups and one v2; dryRun leaves snapshots unchanged; selected reload produces v2 behavior and new `extra_v2` catalog while peer remains v1 without the new tool.
- Canonical public paginated notice item count1 for selected and0 for peer; all `nextCursor` values are null before exact item-count comparison. Exact stable event/item/turn identity and text, matching raw external context and item_completed display, and zero model-turn/request/usage evidence pass.
- Authentic stock rollback `thread/items/list` again returns the same canonical selected item and no peer item, with exhausted pagination. No resume was needed.
- All three pre-rollback raw rollout files retain their exact original byte prefixes; each receives only one strictly validated owned settings checkpoint on rollback. Raw hashes are retained as changed, not falsely called equal.

Complete final caller package maps `modern-final2-inputs-before.json` and `modern-final2-inputs-after.json` in the existing user-scoped artifact directory are identical. Cleanup receipt has empty private-home process and toy survivor lists; a fresh exact-root/private CODEX_HOME `/proc` census is also empty. The owned rollback daemon was stopped, no private updater survived, and host CLI/updater/resources remain untouched. No compiler/provider effects or nonzero accounting proof occurred. Prior failed final1 receipt/log remain unchanged. Memory disposition remains `forbidden` under this task's bounded write scope.
