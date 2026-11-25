# Plan0267 tmux and Byobu recovery qualification

Issue [#772](https://github.com/CochranResearchGroup/codex-wake/issues/772)
qualifies durable delivery to an exact stock Codex conversation after loss of
its terminal tab or server. Five layout cases exercised the shared PostgreSQL
path. A separate CLI run exposed a missing terminal binding when the operator
registered and bound the schedule from outside tmux.

## Initial layout matrix build

- Wake source `46b0476f8a28d3b35ab075400c0005b81dd6d468`. The integration base
  `8243e6146f1f62411e850f750d3dd4b8ce9f34a2` adds only a plan ledger update.
- Private installation of wheel `codex_wake-0.22.0.dev44-py3-none-any.whl`,
  SHA-256 `ac42eb2c194611e4860df1eee529176a9617f194dc6e255d51b08ee35b7c3607`.
  All 369 packaged Python sources matched both the source commit and the
  installed package byte for byte.
- Stock `codex-cli 0.171.0`, SHA-256
  `b76a027d6b210f9a8da7aaf321dd235c700f0ef7a794d4a5314b9af6c134f0f0`.
  The private tmux server ran on tmux 3.4 through Wake's configured Byobu
  workspace adapter. Model responses came from a loopback fixture.

## Installed runtime observations

Every case used a new private Wake root and stock Codex home. The runner
observed an exact saved conversation, configured one durable occurrence with the
same executable, profile home and target tab, and replaced the owning supervisor
process. The next supervisor recovered and delivered. The runners checked the
exact native thread, one local attempt, one shared PostgreSQL submission with the
same native queue receipt, and exactly one additional completed delivery turn.
The restored marker remained until the restored tab received focus.

| Case | Observed outcome | Result SHA-256 |
|---|---|---|
| Vacant original slot | Original index 1, name and working directory restored. The sentinel and unrelated tab at index 7 survived. | `1da54e9300808c22932e5bffe3ef696cd5fabf6d9f9c2d265456061d968531cb` |
| Busy recipient | With the tab closed, an active native turn held delivery at zero attempts. Releasing the active turn allowed one restoration and delivery. | `7069d398b88460cf4da7843ec16a1c33a70e7af45b8bb23336a69b95a8709bb8` |
| Matching idle shell | Wake retained the shell process and pane, then restored at index 1 with a distinct name. The shell moved to index 2 and kept its name. | `ab2d5d292256fddd53507f6bf639b64fe9c91ccc9429f1351b10bac94149fc61` |
| Unrelated tab in original slot | The occupant kept index 1 and its pane. Wake restored the original conversation in index 2. | `654080c665751bddde807e7dd4c0bfdb828b1d80a18b361f31908997b6d0ea2f` |
| Terminal server loss | The test removed the private tmux server and restarted the owned native daemon. Wake created the terminal server and resumed the same conversation from the pinned home at index 1. | `849b530577b822008b5e8b829dc8c1171ed486a4938d7b3c1b021a62979e63a9` |

The aggregate matrix and each case's result matched the console report. Local
raw artifacts live under `/tmp/wake766.b5mChY/evidence`. The artifact directories
are `postgres-tab-loss`, `pg-busy`, `pg-reclaim-shell`, `pg-occupied-slot`
and `pg-stale-socket`. Each holds `result.json`, `monitor.log` and
`native.log`. The standalone runner scripts are alongside the evidence directory.

## Schedule registration outside tmux

Running the initial wheel with the public `schedules register`,
`schedules bind-restoration` and `schedules show` commands outside tmux produced
a durable schedule and confirmed its explicit recovery profile. After loss
of the tab the supervisor held delivery with `recipient_ownership_changed`.
The admission target lacked a tmux socket, so the final ownership observation
looked outside the recovery profile's private server.

Source `a72f97ea5b4658dec236a52e85e308f4310c3a30` uses the fingerprinted
profile's socket when admission lacks terminal context. Binding records the
verified original frontend birth with placement. A missing server can then be
qualified using the observed frontend's process and boot identity. After
restoration, delivery rechecks the exact conversation on that same socket.
Existing bindings with only a saved placement still load. A prior schedule
that lacks both the original process evidence and a reachable server can
require rebinding while the exact tab is available to qualify future loss.

The red-run receipt is
`/tmp/issue772-cli.llWbW4NV/evidence/result.json` (SHA-256
`516e7ffaebf63153634f727dad6c1e29caa5252db6595dc33b2ad78882db4396`).
The runner scripts `run.py` and `full-server.py` in that scratch directory
remove ambient `TMUX` from the CLI and supervisor environment, verify the
schedule has no admitted socket, and require a pinned explicit placement.

Both runners passed against the separately installed corrected wheel
`codex_wake-0.22.0.dev44-py3-none-any.whl`, SHA-256
`5093ae14389204f077d996abfd1a79be4894e50b4c62f5a68fc7b40d5972526b`.
All 369 packaged Python sources matched the corrected commit and installed
package. The tab-loss case restored index 1 and preserved the other tab at
index 7. The server-loss case recreated the terminal server at the same
private socket and resumed at index 1. Both delivered one additional
completed turn to the original conversation with one matched PostgreSQL
attempt and native queue receipt. There were no remaining runner or
supervisor processes after cleanup.

| Corrected-wheel receipt | SHA-256 |
|---|---|
| `/tmp/issue772-cli.llWbW4NV/installed-tab/result.json` | `ad52cfabb0e0c70620feb2d2346ade87316e839b04fef16803f2e2a1cd17d772` |
| `/tmp/issue772-cli.llWbW4NV/installed-server/result.json` | `ecf7ab12f1af4212989fd35516be1fa7eeaac1e3fe7207588c94342d1ab9407c` |

## Reproduce the qualification

1. Install the exact wheel with its `postgres` extra in an isolated environment.
   Initialize an empty private PostgreSQL database with
   `codex-wake messages database-init`. Set `CODEX_WAKE_MESSAGE_DB_DSN` in the
   runner and supervisor environments.
2. Use a disposable stock app-server, local model catalog and loopback model.
   Open its saved UUID with `sessions open --resume` on a private tmux socket,
   enroll the agent, and pin the recovery profile to the same UUID, home,
   executable, working directory and intended tab. Configure a one-occurrence
   `reopen_live` schedule with `schedules register` and pin its restoration
   profile with `schedules bind-restoration`.
3. For each layout scenario, remove the tab or its server, and start a new
   supervisor generation with the supported `supervisor run` command. For the
   busy case keep a native turn active with the tab closed until the scheduler
   records a busy hold and zero attempts, then release it.
4. Read the schedule occurrence, Wake native delivery receipt, PostgreSQL
   attempt row, native turns and `sessions list` attachment. Compare the
   recipients, queue receipt, attempts, restored slot, cwd and result.

For local regression, set `CODEX_WAKE_TEST_MESSAGE_DB_DSN` to a disposable
database and run the following with the same Python 3.12 interpreter. All 63
tests passed against the fix.

```sh
PYTHONPATH=src:tests python -m unittest \
  test_postgres_message_delivery test_tab_recovery_restored_slots \
  test_wake_live_restore test_wake_mode_runtime test_wake_session_modes \
  test_recurring_schedules test_tab_reattach \
  test_tab_reattach_public test_tab_reattach_traits
```

This covers a private tmux server through the Byobu workspace adapter. Live
Cooper or Bastion startup, the Byobu interactive shell and psmux were outside
this qualification. The model provider fixture uses a private account home
and loopback endpoint because this test exercises recovery without production
provider credentials.
