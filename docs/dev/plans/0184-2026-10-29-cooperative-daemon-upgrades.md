# Cooperative daemon upgrades

State: OPEN
Outcome boundary (preserved): OPEN. Native checkpoint gate is implemented and isolated-runtime qualified; broader real-model and downstream activation automation remain open. Operator requests every open tab receive a prompt instructing active work to pause and produce a durable handoff before a built daemon is installed. Prior Plan0183 runtime acceptance is evidence, not installation authority. Only dummy UID1017 qualification; preserve working services, eight supervision records and lifecycle registry.

## Current State

The native checkpoint gate has isolated-runtime source qualification, with private
native custody and exact compiled identity recorded below. Broader real-model
acceptance and downstream activation automation remain OPEN. Canonical Wake
integration through PR430 (`343ed9f`) publishes that evidence; it does not install
or activate the candidate or close those broader gates. Historical runtime
observations below remain dated qualification, not current live-state readbacks.


Design: native updater preparation precedes package selection, stopping workers or replacing the daemon. One connection-owned native admission barrier rejects new work while allowing the coordinator to steer existing active turns. Closing the coordinator releases its upgrade hold without reopening a real shutdown drain. Capture all loaded conversations (including workers), publish durable visible/context notices to all, steer every active turn to checkpoint and pause. Idle conversations get a durable host snapshot and no unnecessary model turn. Active agents return an operation/thread-bound structured handoff; the updater atomically writes and fsyncs it into private CODEX_HOME/daemon-upgrades state, avoiding sandbox write permissions or mandatory MCP enrollment. Installation waits for valid handoffs, inactive goals, and idle native turns. Missing, invalid, timed-out or unacknowledged handoffs block installation; old daemon remains selected/running. No forced kill or invented summary. Preserve counters and deadlines; no automatic resource renewal or work resume.

Stable seams: actual native prepare RPC rejects new turns, accepts checkpoint steering and releases on coordinator disconnect; supported native update --from-cli publishes requests to two real open UIs, receives agent-authored handoffs and makes durable files before replacement; negative refusal holds old binary and files. Scheduled updater must use the same preparation before installer effects. Older daemons without the barrier must produce an actionable held result rather than unsafe fallback. First adoption remains a distinct compatibility gate.

TDD: one public seam red before minimal implementation, then next slice. Existing native protocol/client and updater tests/harnesses first. Source reviews, exact complete-package hashes, actual dummy-account update and rollback, final OS census and unchanged working state required. No independent real-model proof inferred from scripted provider.

## Qualification ledger

Native source: `/home/ecochran76/workspace.local/codex-wake-native-0165`, branch `fix/native-0165-cooperative-upgrades`, base `e641e1daeda0d119f28e320c7cb328b30d118754`. Wake evidence checkout remains `codex-wake-build-0165` / `fix/native-0165-oauth-acceptance`; unrelated prior dirty work retained. No OpenAI-origin push and no working-account installation.

- RED: actual supported updater with unsafe baseline package completed replacement without a checkpoint receipt (`upgrade-journey-red1`). Public prepare RPC also rejected on prior daemon (`upgrade-barrier-red2`).
- GREEN: corrected candidate `076ff7187be40308903f8396c8adc9e4b042259dff787cad6f7659326a245233` delivered visible/context notices to four actual modified-client tabs (two active conversations, one mirror attachment, one idle conversation). Two active turns paused their native goals and returned operation/thread-bound handoffs; host writer atomically persisted/fsynced these even with read-only model sandbox and no MCP enrollment. Cached idle bootstrap conversation also received an idle snapshot.
- Actual supported update rejected new work during preparation, waited for checkpoints, replaced daemon, and retained original conversation identity in all four tabs. Supported rollback restored baseline package and preserved handoff hashes, goals, ceilings and counters (`green5`). No automatic model work resumed.
- Negative ready=false (`refuse1`), full 120-second hang (`hang1`), and older unsupported daemon (`legacy1`) all held the old daemon/package and released only the coordinator's admission hold. Older daemon explains one-time save/stop adoption requirement.
- Retained failures: first checkpoint candidate incorrectly treated wrapped native history entries as bare ThreadItem; it safely held installation (`green1`). Fixed reader consumes entry.turnId and entry.item. Two expanded UI probes failed because fixture sent Enter inside paste-burst timing; captured composer showed unsubmitted `/status`. Separating typing and Enter by400ms passed all original UI/rollback assertions (`green5`); no product UI change.
- Native admission selection: two tests passed. Initial daemon suite:78passed/4failed because fake control server lacked the new RPC. Corrected external protocol fixture:81passed/1failed; all updater cases pass, separate legacy PID-time check flaked (`shutdown_grace_handles_process_exit`: legacy start time changed). Its exact diagnostic rerun passed1/1 in2.07s; original failure retained and suite not described as clean. Owner: native daemon qualification lane; disposition: unresolved host-time-sensitive regression risk before working installation. No policy relaxation or unrelated PID fix.

Evidence: `docs/dev/evidence/plan0184/runtime-proof.json`; full synthetic receipts/logs under dummy `daemon-qualification-0165/upgrade-journey-*` and user state `~/.local/state/codex-wake/plan184`. Acceptance harness is `scripts/native_daemon_upgrade_acceptance.py`.

## Remaining gates and limits

Final stable/experimental schemas and Python types are generated. Native component checks:21updater tests passed (including scheduled deferral),4schema consistency tests passed/1generator ignored,2admission tests passed. Targeted Rust formatting and diff checks pass. Full workspace suite was not run; earlier legacy PID-time flake is retained separately.

Final immutable complete package: dummy `candidate-checkpoint4`, executable SHA256 `acb3e9284ebfd99a7aa6f2248c0d538aa7a3e6eda159ffa6d880f23e0f1064c5`. `final1`, `finalhang1`, `finalrefuse1`, `finallegacy1` all passed on this exact binary. `finalfresh1` additionally opened fresh actual modified-client tabs after update and rollback while retaining all original tabs. Its fixture explicitly registers the matching qualified build after native selection and restores registration on rollback; this is setup/configuration, not evidence of automatic downstream registry coordination. Five tabs verified after upgrade and six after rollback. Original four tabs all received upgrade prompts. A module-order formatter correction rebuilt to the identical SHA, so existing exact-binary runtime qualification was reused rather than rerun.

The downstream build-channel activation transaction is not implemented by this native coordinator: launcher registration and native selection must match. Automating their ordering and rollback belongs to the next bounded upgrade-UX slice; do not claim fully automatic build activation from these tests. Working installation was not attempted. Dummy UID1017 process census is empty; working governor remains masked/inactive and eight supervision hashes plus lifecycle registry SHA are unchanged. Source/specification and standards reviews are retained in evidence. No private patch was pushed to OpenAI origin.

Scheduled checks intentionally defer whenever conversations are loaded; explicit updates perform cooperative preparation. Older-daemon first adoption remains an explicit save/stop compatibility step. Independent real-model checkpoint acceptance and the original broader Plan0183 acceptance remain OPEN.

Provider is an owned scripted localhost Responses fixture, with zero external model calls. It proves native prompt delivery, tool execution, persistence, gating, refusal, timeout and UI continuity; independent real-model checkpoint quality remains unproven. The separate UID shares this WSL kernel/resources. Power-loss fault injection and Windows-native execution are not qualified by this run. First adoption from an older daemon needs a one-time deliberate save/stop; no unsafe fallback exists. Broader Plan0183 real-model acceptance remains OPEN. Automatic failed-start rollback UX from the earlier request is not redesigned in this checkpoint slice; prior Plan0182 qualification remains separate evidence.

## Source custody

Native implementation retained as local commit `dfde754e597f0b4766f5b22fbeb990d2e78fe151` on `fix/native-0165-cooperative-upgrades`. No OpenAI-origin push. Exact compiled binary remains `acb3e9284ebfd99a7aa6f2248c0d538aa7a3e6eda159ffa6d880f23e0f1064c5`; formatter rebuild verified byte identity. Native tracked worktree is clean; generated `.codegraph/` remains local/untracked.

Memory disposition: `unavailable`. Reviewed Codex Wake destination routing is unresolved; no unrelated cloud write. Zero writes attempted; machine-readable receipt: `/home/ecochran76/.local/state/codex-wake/plan184/memory-disposition.json`.
