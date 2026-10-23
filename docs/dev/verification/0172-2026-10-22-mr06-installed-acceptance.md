# MR-06 installed acceptance: retained setup failure

Work item CW-MR-172/MR-06. Primary owns the only ready ticket; no independent
nonblocked ticket exists to delegate. Candidate base651d493, package sourceef8b5b4,
unreleased0.19.1 wheel SHA256
`c5078cd1d94286bbd84c71f112a62514501d6de63481ec9f20c864ec8d6aab34`.
State: IN_PROGRESS — live acceptance not qualified; corrected launcher prepared.

## Current evidence and limits

Before live effects, all121 package modules matched the accepted wheel and the
non-editable installed prefix byte for byte. Prior frozen1451 PASS/one opt-in skip
and final installed15 PASS remain valid for those unchanged package bytes. They
are not a full-suite qualification of the new opt-in launcher. The new provider-free
launcher regression passes1 test in0.084s; compile, F821/F822/F823 and whitespace pass.

The user said “ok go” after MR-06 was declared ready for actual visible TUI and
bidirectional acceptance. The recorded live envelope was one disposable recipient
per runtime, six original synthetic prompts,300 seconds including cleanup, no
extra launch/replay. One launch of each runtime consumed that recipient envelope.
The sample stopped in6.338s before any conversation prompt, bus, actor grant,
binding or wake registration. No live first-release criterion is promoted to pass.

Codex0.163.0 / Grok1.0.40 eb1a2256660d stable / Wake0.19.1. Owned Codex thread
`01a166c3-ae11-7f93-a57e-26d571b6a73f`; Grok session
`3fd09f1e-2e5a-45f5-9fea-872b2e902223`. Both launch paths were entered. Grok
reached a matching local session-info response, but the Codex pane disappeared
before capture. Exact stop: `command_refused:tmux:can't find pane: %0`.
The Codex exit cause is unconfirmed because the original pane was not retained.
A bounded file-searcher lookup found no matching owned-session startup error in
the returned log candidates; cached/partial lookup is not proof no other log exists.

Initial cleanup readback retained one introduced process1373703 and no changed
pre-existing generations, so the original sample remains FAIL/cleanup_incomplete.
A later fresh OS readback found that process already gone; no remedial signal was
sent. Another later census has zero introduced residuals and one pre-existing
process1367443 later absent, with cause unattributed. No pre-existing
PID was targeted. These observations stay separate; later cleanup does not rewrite
the failed sample or prove global process stability indefinitely.

Raw evidence is private at
`~/.local/state/codex-wake/design/grok-multi-runtime-20261021/mr06/`.
The original launcher's exact source was not snapshotted at run time; its command,
result and installed identity are retained. The corrected launcher now snapshots
its own source/hash and installed module inventory before any runtime launch.

## Provider-free repair and concrete next run

The original tmux pattern is red-capable without models: start a shell that emits
CW_STARTUP_FAILURE then exits7; tmux removes its pane, and capture fails. The new
prepare_tmux seam first creates an owned inert pane, enables remain-on-exit, then
respawns the requested command. A real tmux regression proves the dead pane,
original exit7 and original error remain accessible in scrollback. An intermediate
viewport-only check failed and is retained; the actual launcher already reads
scrollback. This is startup-evidence repair, not a passing Codex startup proof.

Connection/security flags are now placed explicitly on `codex resume`; CLI help
confirms that option location. This removes an ambiguity but is not a confirmed
root-cause fix. The corrected launcher waits on bounded fresh process readbacks
instead of assuming shutdown completes after0.4s, retains unattributed new processes,
never kills a pre-existing PID, and refuses acceptance on unresolved residuals.

The concrete opt-in launcher is
`scripts/multiruntime_live_qualification.py`. Before runtime launch it requires
an installed prefix, qualified wheel and exact wheel digest; every installed
module must match. It snapshots its source. Grok permits only the exact Bash probe
and work helper commands, not arbitrary command rules. Inherited runtime session
context is observed, never inserted by the harness. Failure/refusal/uncertainty
stops the path. No production grants, buses, services or installation are changed.

A further live run needs an explicit recipient-envelope extension: at most one
additional disposable Codex TUI and one Grok TUI, six synthetic prompts total,
five minutes including cleanup, no replay. The prepared first three durable
intents plus at most one A2A notification fit within that ceiling. The previous
sample submitted zero prompts; no pending request or work claim exists to replay.
Until that extension is received, do not launch the corrected harness.

## Independent criterion verdicts

| Criterion | Source/isolated package evidence | Current live evidence |
| --- | --- | --- |
| AC1 exact durable Codex/Grok wake | Prior installed controls pass | NOT QUALIFIED: setup stopped before registration |
| AC2 both directions, authentication, claim/reply | Frozen bus/actor/notification controls pass | NOT RUN: no bus or actor created |
| AC3 wait / unsupported queue and interrupt | Installed refusal controls pass; no new guarantee | NOT RUN in this sample |
| AC4 approved fallback and protected composer | Installed profile/fault controls pass | NOT RUN: no binding created |
| AC5 original expiry, cancellation, restart, uncertainty | Frozen fault controls pass | NOT RUN: no intent created |
| AC6 Codex identity/reader compatibility | Prior frozen1451 and installed15 pass, unchanged package | Real Codex TUI startup FAIL/unknown cause |
| AC7 truthful capabilities/agent interface | Installed CLI/MCP controls pass; unqualified modes explicit | Native Grok caller attestation remains NOT QUALIFIED |

MR-06 stays IN_PROGRESS. MR-01–MR-05 source/isolated evidence remains retained;
none of it substitutes for the missing actual TUI and bidirectional first-release
acceptance. Main integration, release and production rollout remain separate.
