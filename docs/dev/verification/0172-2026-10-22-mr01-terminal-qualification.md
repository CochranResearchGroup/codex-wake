# MR-01 authenticated terminal-route qualification

Date: 2026-10-22
Work item: CW-MR-172/MR-01
Source base: 412789d
Verdict: QUALIFIED_TERMINAL_OBSERVATION
Owner: primary agent / ecochran76

## Result and Scope

After the user restored Grok sign-in and said done, one bounded rerun proved a
usable terminal route into an already-open Grok TUI. MR-01 is complete with this
limited route; MR-02 is ready. No later ticket was started and no other ticket
was ready for a subagent during this rerun.

The selected route is literal bracketed paste and Enter into a managed-launch
pane, with process-generation and displayed-session checks. Qualification is for
Grok1.0.40/eb1a2256660d, its observed minimal/no-alt-screen UI and this binding
method. It does not qualify arbitrary existing Grok tabs, every UI version or a
native shared-backend protocol.

The [first authentication-gated receipt](../evidence/plan0172/mr01-auth-gated.json)
is retained unchanged. Its failure is not erased by this successful rerun.

## Live Sequence

Use the earlier probe's empty private workspace/private sockets and restrictive
launch settings, with a fresh directory and requested session UUID. No manual
auth or user-configuration edits were performed. One TUI opens without sign-in.
Installed version remains1.0.40; this session's actual displayed model is Grok4.7.

Before input, record the private pane, PID/start ticks/boot identity, executable
arguments including the requested UUID, and workspace. Send the built-in
/session-info control command. The TUI itself reports
fce842bc-e502-40ba-a892-6d7778283ef1, Turn0. This establishes the live
conversation independently of a tab title or CWD.

Native initialize and exact-workspace session/list work on a separate stdio
connection, but the list is empty. No private leader socket existed immediately
after the TUI launch. Consequently there is no evidence that this separate
native backend owns the open TUI session; no native load or prompt was attempted.
This is an unqualified route, not proof that Grok can never expose shared control.

The small qualification helper rechecks exact UUID, process generation and
the observed session-info UUID, then requires an empty recognized composer:

- A deliberately mismatched expected UUID refuses before input; the pane's
  captured content is unchanged.
- An owned unsent draft makes the helper refuse submission. Only that injected
  draft is cleared, then the empty composer is re-observed.
- Exactly one synthetic prompt is pasted literally using a private tmux buffer,
  bracketed paste and Enter. No shell interpolation, tools or subagents.

The prompt asks for CW_MR01_ACK_2ff83efe58. A subsequent capture shows both
the submitted instruction and that token as a separate response line.
A second /session-info reports the same UUID, Turn1; PID and start ticks also
remain unchanged. The TUI was already open before the prompt was submitted.

## Evidence Meaning

This proves terminal-observed prompt acceptance and a standalone model response
in the same live conversation. It does not create a receiver acknowledgment,
authenticated work claim, correlated A2A reply or exactly-once transport receipt.

Negative identity and protected-composer behavior are observations of the
qualification helper, not tests of a production Wake adapter. Active-turn busy
queue/interrupt behavior, generic unknown UI recognition, caller attestation,
unmanaged-session adoption and native live submission remain unqualified.
MR-02/MR-03 must implement and test real guards; MR-05 owns broader policies.

## Bounds and Resources

One TUI launch and one conversation prompt; no delivery replay. Live probe through
owned-process teardown249.221s, within the300s/two-recipient/six-submission bound.
The two session-info commands are local control commands, not conversation
prompts. Native observation sends only initialize and session/list.

After teardown, grok usage for this exact UUID reports one model call and one
turn: inputTokens27805, outputTokens100, cachedReadTokens1280,
reasoningTokens88, totalTokens27905 and costUsdTicks184586000.
These are retained native counters, not a new interpretation of fresh-token
accounting, cost units or strict resource enforcement. No token/cost ceiling was
specified for this probe.

## Cleanup and Reconciliation

Only the exact private test tmux session and private leader peer were retired.
Fresh OS census preserves every pre-existing Grok/tmux process generation,
finds zero introduced application processes and confirms the test TUI PID absent.
No production conversations, mailboxes, grants or controllers were touched.

[Sanitized machine receipt](../evidence/plan0172/mr01-terminal-qualified.json).
[Selected exact synthetic frame lines](../evidence/plan0172/mr01-terminal-frames.json)
retain capture hashes for recognizer work without claiming a production parser.
Complete synthetic captures and process snapshots remain at
~/.local/state/codex-wake/design/grok-multi-runtime-20261021/mr01-authenticated/.
MR-01 DONE; MR-02 READY with terminal-observed capability and explicit limitations.
All other tickets remain dependency-blocked. The primary has no delegated result
to reconcile in this wave.

## Validation

Validate JSON, bounded counters, same-session/generation evidence, exactly one
persisted model call, cleanup and explicit absent native/A2A receipts; check
relative links and Git whitespace. No production code or runtime test suite is
changed by this evidence packet.

Executed: machine/private-receipt invariants PASS; persisted usage field
comparison PASS; 129 relative targets in touched documents PASS; three synthetic
frame projections parse; whitespace PASS. Active planning audit retains four
inherited Plan0166–Plan0169 findings and adds zero Plan0172 findings.
