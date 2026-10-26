# Modern managed package qualification

The optional `--modern-managed-update` path is implemented. The authorized new GNU candidate roundtrip reached real stock→candidate→stock replacement but the overall qualifier is **FAILED** on raw rollout-byte preservation: native cold reads append settings checkpoints. The legacy default qualifier is retained. Historical intermediate gates below are retained with their actual execution status.

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
