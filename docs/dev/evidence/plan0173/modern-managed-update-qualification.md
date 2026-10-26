# Modern managed package qualification

The optional `--modern-managed-update` path is implemented; acceptance against the new GNU candidate is **NOT RUN**. Its source package must first pass the native build gates. The legacy default qualifier is retained.

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
