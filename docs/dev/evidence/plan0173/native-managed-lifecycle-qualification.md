# Private managed native lifecycle qualification

State: PASS_PRIVATE_LEGACY_LIFECYCLE_AND_CANDIDATE_TO_STOCK_ROLLBACK.
Wake source base:ce1ad93eec437c1b4854dde2c9a174d5c5f94255.
Native source:98d5c6736ac66f06c62b9eaa275adb8a30baa431.
Qualifier script SHA256:1d9d661ccd69fd5add1dee4a95638b8ac15647e0d845553fa2212bfedb5b0ba5.
Only the qualification script and this report are owned by this lane.

## Exact scope and authority

The native daemon README documents an operator updating its fixed managed path
out of band and then using start/restart without bootstrap. The earlier inference
that missing modern update/from-cli alone blocked activation was too strong.
This packet qualifies that documented legacy path in a fresh private home.

No host managed package, shared native server, existing conversation, service,
resource allowance or authentication file was changed. No bootstrap, updater,
model turn or provider request was invoked. The run used a distinct user/network
namespace with only loopback and no external route, private HOME/CODEX_HOME/XDG
roots, scrubbed child credentials and an unused loopback provider endpoint.
Default standalone qualification mode remains unchanged.

## Matching artifacts and real helper execution

Immutable private artifact bundle:
`~/.local/share/codex-wake/native/managed-98d5c6736a-20261025T213621Z/`.
Its manifest records source, artifact hashes and the provider-free helper test.

- Full CLI SHA256:497a0ff8560e3870c24e40f4422db19bff969f26cb12c7fd35c768787e686c7b.
- Tested code-mode host SHA256:74379f24916b0ad993757300b607b86c5ed7381255a1018fcec0da2e55c7f1c9.
- Helper build:locked/offline,2jobs,300second cap; exit0 in171.90seconds.
  Build-only helperd16051... was superseded by the test-configuration artifact.
- Named stdio test:remote_session_persists_values_forwards_delegates_and_controls_cells;
 1selected passed,6skipped, execution0.072seconds, envelope96.78seconds.
 It exercised actual helper process RPC, retained values, delegated tool callback,
 notification, yield/wait/termination and shutdown, without a model/provider.
- Test source SHA256:432dee93feb1c8040370059140290e8825757138501f0ad9ebbc050f0da7dc4a.
- Test log SHA256:d42ab6cb4e953666f11884667aeb8cca77ee0870fcf309f2be6088e6c48cafc1.

CLI hashes matched before/after helper build and test. Hashing uses streaming
file_digest. Tracked native source stayed clean; the separately authorized
untracked CodeGraph index was preserved.

## Preserved red attempts and fixture corrections

1. managed-wrong-standalone-red stopped before launch because /proc/1 namespace
   inspection is restricted in a user namespace. An explicit outer namespace
   witness corrected the probe while retaining distinct-namespace/loopback checks.
2. managed-wrong-standalone-red-2 exercised actual lifecycle refusal: standalone299
   staged as legacy codex rejects the app-server argument;5.85seconds, empty cleanup.
3. managed-full-cli-attempt1 reached actual CLI lifecycle but its long private
   CODEX_HOME exceeded SUN_LEN. Managed stop succeeded and cleanup was empty.
   A shorter private user-state root and explicit private-workspace cwd corrected
   only the fixture. No native source change was made.
4. cw-managed-98d5-a2 reached managed refresh and notice proof but the probe
   incorrectly counted a synthetic display container as a model turn. The raw
   rollout had only metadata, goal update, exact internal notice context and exact
   agent display event. Its failure is retained. The correction accepts only one
   exact expected notice container with null timestamps/error, one exact notice
   agentMessage, and no other turn/items. Raw history rejects task/usage/model
   request/completion or unrelated records; goals/counters are checked unchanged.

All original roots remain retained. No history/body rewrite, resume workaround or
native implementation fix was used to obtain green.

## Terminal managed proof

Original proof root:`~/.local/state/cw-managed-98d5-a3/`.
Canonical sanitized receipts/logs:
`~/.local/state/codex-wake/native-activation/managed-private-qualified-98d5/`.
Receipt SHA256:c85e36ae2c3a57387a9cb68418a095041653ae49ffecd1f4dd694426c7426c79.
Elapsed25.44seconds; model turns0.

The candidate CLI and adjacent same-source helper were copied into the private
legacy releases/current layout. Actual candidate start/version/stop succeeded.
Staged source and /proc executable hashes matched the497a0ff... full CLI. Two
paused private goals retained identity, token ceiling1000, tokensUsed0 and
 timeUsedSeconds0. Dry-run inspection left both snapshots unchanged. Reload
updated only the selected toy behavior/catalog to v2/extra_v2; peer stayed v1.
There were exactly three toy startups:v1,v1,v2.

Actual notice append/read retained exact selected context/display and proved peer
absence. A synthetic history display container was distinguished from an actual
model turn using exact content/null timestamps plus strict raw-rollout evidence.
This is RPC/context/history proof, not new stock-TUI rendering or human-read proof.
Earlier standalone299 TUI evidence remains a separate artifact boundary.

The candidate was managed-stopped, then the complete reference0.164 package
(binary, companion and resources; no auth files) was copied into the same private
managed layout. Actual reference start/version/stop succeeded. /proc executable
hash matchedb93f6811d3f653f0fb83be4050d857fb9abbb111dfa2ce160563327daff7f306.
Both actual candidate-created threads were read with includeTurns and their goals
read back. Goal identity, status, counters, ceilings and all original fields
matched. The selected exact notice/container/context remained readable and the
peer remained absent. Raw rollout hashes before/after rollback reads were equal.
No resume or migration workaround was attempted.

Both daemon identities were absent after stop; toy/private-home survivors were
empty. A fresh host-side readback independently confirmed those exact daemon PIDs
absent and no private-home process remained (fresh-host-cleanup.json).

## Remaining boundaries

This qualifies fresh-private-home managed lifecycle and functional
candidate-to-stock rollback only. It does not prove live existing-stock-to-candidate
conversation migration, new rendered-TUI behavior for this full CLI, or a whole
native-suite pass. The helper's actual execution was proved by the named stdio
seam; execution through a managed model turn was not invoked. Activation and the
choice between modern managed updates versus a pinned legacy/manual-upgrade
runtime remain primary/operator decisions. No further builds or activation were
performed after terminal qualification.

Memory disposition: forbidden; this task did not authorize a memory write.

## Primary reconciliation

Carriede5251703 into957218c. Canonical receipt hash verified independently as
c85e36ae2c3a57387a9cb68418a095041653ae49ffecd1f4dd694426c7426c79.
Primary lint exposed inherited/new E701/E702 style in the qualification runner.
Ruff formatting was applied and ASTs compared identical; exact tested script
1d9d661ccd69fd5add1dee4a95638b8ac15647e0d845553fa2212bfedb5b0ba5
is retained in associated userstate, formatted script
53ed05e87886a0ba94cdabff48f5d0d6ffdd81969d320cc8e3ef1d509d63eb80
passes Ruff/compile/diff checks. This formatting is not a new runtime proof.
Live native0.164.0 and eight retained campaign files are unchanged. Deployment
policy Q1 remains an operator choice; private managed qualification is complete.

## Reproduction entrypoint

Run from this Wake worktree with a new short private root. The original runner
source/hash is retained with the receipt; formatting preserves its AST. This
invocation uses real namespace isolation and does not contact the host daemon:

```sh
wake_install_prefix="$HOME/.local/share/codex-wake/releases/0.22.0.dev0-ce1ad93"
wake_native_prefix="$HOME/.local/share/codex-wake/native/managed-98d5c6736a-20261025T213621Z"
env CODEX_WAKE_QUALIFICATION_PARENT_NETNS="$(readlink /proc/self/ns/net)" \
  unshare -Urn sh -c 'ip link set lo up; exec "$@"' sh \
  "$wake_install_prefix/bin/python" scripts/scoped_refresh_native_qualification.py \
  --execute --root "$HOME/.local/state/cw-managed-new-run" \
  --prefix "$wake_install_prefix" --managed-cli "$wake_native_prefix/bin/codex" \
  --code-mode-host "$wake_native_prefix/bin/codex-code-mode-host" \
  --rollback-cli "$HOME/.local/bin/codex"
```

This documents the qualified path; it is not authorization for another effect
run or live installation. A used root must be preserved, not cleared for retry.
