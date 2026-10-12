# Lifecycle probe findings — Codex0.162.1 / Wake0.13.1

## Question and verdict

Does quitting/resuming refresh skills and MCP, and can a fresh conversation
continue from an outgoing agent's handoff? Three real, short model turns ran in
one disposable Byobu/tmux session and a private app-server/CODEX_HOME/workspace.
No production peer, goal, budget, bus, service or installed configuration changed.

Same-thread TUI restart does **not** prove MCP refresh. The skill file read changed
from v1 to v2; the original thread retained its v1 MCP process/tool through quit
and resume. `/new` created a different loaded thread, started the v2 MCP process,
and the successor successfully called probe_v2 and read the agent-written handoff.
The same client process remained attached across `/new`.

## Actual observations

1. Installed `sessions open --new` created an exact thread and ready tab.
2. Original agent read the v1 skill, attempted the v1 tool once, and wrote its own
   handoff with task/authority limits and no goal-budget reset. The tool call was
   denied because the toy tool initially omitted read-only annotations. No tool
   result is claimed for this turn; rejection and the truthful handoff survive.
3. After v2 staging, `/quit` had not yet taken effect when `open --resume` ran;
   it returned `action=reused` and the same PID. Controller must observe actual
   exit. A later Enter submitted the still-visible `/quit`; exit was observed
   before the next exact resume. No new conversation was created by that resume.
4. New TUI PID resumed the original exact thread. Current skill file contained
   v2, but tool discovery/call still targeted probe_v1 and was denied. The same
   old MCP PID remained; restarting the TUI did not restart its thread runtime.
5. `/new` similarly required actual command acceptance, not assuming `send-keys`
   completed the transition. The newly loaded thread was initially absent from
   persisted `thread/list`; `thread/loaded/list` exposed it before its first turn.
6. Successor completed a native-queued turn: read the original handoff, read v2
   skill, successfully called the newly read-only-annotated v2 MCP tool, reported
   its own native-shell thread ID and explicitly did not resume/create a goal.
7. Ordinary installed close on the exact owned pane succeeded, `forced=false`,
   original conversations preserved, affected wakes/messages empty. Owned tmux
   session and app-server then exited. OS census found no process with the
   private CODEX_HOME and both MCP/TUI PIDs were gone.

## Limits and corrections

This is an experiment, not lifecycle product acceptance. The skill proof is a
fresh **file read**, not automatic catalog/hook/plugin reload. MCP v2 annotations
corrected the fixture's read-only declaration; the fresh success cannot be used
as evidence that previously blocked production tools become authorized. No
shared app-server restart, goal migration, budget renewal, real A2A claim transfer
or actual ask-Matt skill invocation was performed. Successor did a bounded
preflight report, not an implemented/qualified ask-Matt controller.

An explicit listener initially exposed a symlink; the installed Wake endpoint
guard rejected it before creating any thread. Resolved owned socket was used
without weakening the guard. Initial prototype logging reused an open receipt
filename; subsequent receipts are append-only with unique names. The initial
open was observed in the actual CLI output, not reconstructed as a raw receipt.

Goal get/set/clear schemas were generated from installed Codex. Set declares
mutation provenance; missing provenance supplies no user authorization. It
supports tokenBudget, not an explicit wall-time budget field. A future external
controller must enforce the approved elapsed-time bound independently and must
not renew resource allowance merely because a successor has fresh context.

GitHub preflight initially rejected the canonical registry's redundant
intent/enhancement alias mapping to the same enhancement label as intent/feature.
Removed only that redundant alias; exact target, actions and provider labels
remain unchanged. Qualified preflight then passed.

## Design consequences

- Separate attach/resume from tool refresh; expose exactly what was verified.
- Prefer native new-thread creation/queued initial prompt to blind slash-key
  automation. `/new` can work, but must reconcile actual loaded identity and
  preserve the old conversation before trusting it.
- Refresh defaults to a bounded named same-thread attempt. If MCP remains stale,
  stop with evidence; do not silently switch to new identity or restart a shared
  daemon. Fresh handoff is an explicitly selected separate operation.
- Outgoing agent writes the handoff; external controller verifies it and handles
  exit/startup/prompt delivery. A handoff is a source locator, not live authority.
- Preserve cumulative goal accounting and original pending work. Enroll a fresh
  A2A actor only through operator authority; never copy the outgoing capability.

Source hashes and curated identities: runtime-summary.json. Raw synthetic
runtime/turn receipts and handoff remain in private user-state evidence.
