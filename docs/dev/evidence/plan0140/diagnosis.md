# Notification visibility diagnosis

Scope: investigate preserved Plan0139 attempt without replay, receipt edits,
new Codex turns, service changes or production repair. Installed0.11.1 source
2e87f664dea6ef3bdc7b37d004f60f8748638af0; audit baseline main9aed3e8.

## Observed

Worker records notification_visibility_unproven for the sole original attempt
attempt_891fb92c107d4bd189fcb05c242632f7, message
msg_887eda3fcdd64d35a6113df4677212a0. The preserved native user-message contains
that exact notification marker in completed turn01a126b8-b89a-7f32-ba95-f8f603b2f77d.
Public recipient receipts show received, accepted, completed. Thus the notification
reached the recipient while the transport observer could not prove pane visibility.
The original post-paste screen capture was not retained. This does not establish
which UI mechanism removed or obscured the marker, nor supply a native queue
receipt for that original attempt. Original notification remains uncertain.

## Reproduction and hypotheses

Installed command:
`~/.local/share/codex-wake/releases/0.11.1-2e87f66/bin/python ~/.local/state/codex-wake/visibility-diagnosis/repro.py`.
Runs actual TmuxBinding.deliver with disposable bus and external runtime fixtures.
One paste; absent post-submit marker -> uncertain/notification_visibility_unproven
in0.159s; assertion for submitted fails. This is a deterministic classification
reproduction, not proof the original UI followed the synthetic sequence. Successful
paste alone cannot prove submission; this failing assertion is diagnostic only,
not the acceptance criterion for a proposed fix.

Ranked hypotheses before probes: (1) redraw/scroll removes marker, (2) wrapped
marker defeats exact substring, (3) capture precedes UI paint. Private tmux shell
probes establish mechanisms1and2 without sending Codex notifications:
160-column marker visible; after100output lines marker absent from viewport but
present in scrollback. Fresh20-column pane wraps the marker over3lines: exact
substring false, joined-lines match true. The first resize-based wrapping probe
was inconclusive and remains preserved. Hypothesis3 was not tested; original
missing capture prevents retrospective attribution. Both private tmux servers
were killed after probes. No original effects replayed.

## Cause boundary and recommendation

TmuxBinding.deliver lines113-122 qualifies delivery by searching one visible
screen capture after bracketed paste/Enter. SubprocessTmuxRunner.capture_pane
uses capture-pane -p without scrollback or joined lines. The screen is a lossy
observer of submission, so successful receipt and uncertain visibility can coexist.
The worker's uncertainty hold is correct under that evidence contract; do not
simply return submitted after successful paste or auto-clear the journal.

Recommended bounded repair: send live-tab notifications through the existing native
queue mechanism, accepting only its exact recipient/queue-ID receipt. Preserve
current process generation, identity, idle/empty-composer, pane lock, expiration,
capability and reply-arm checks. SavedRecipientBinding already qualifies native
queue acceptance, but its closed-client and explicit reopening rules must remain
separate; do not reuse it by bypassing those checks. Native queue is not an atomic
idle guarantee: retain immediate pre-submit checks and document the remaining race.
No retries/fallback after entered submission; timeout or malformed receipt uncertain.
No native-receipt reconstruction for the old attempt, which lacks an attempt marker.

Future repair acceptance: public dispatcher regression for viewport loss/wrapping,
exact queue receipt; busy/draft/reused-PID/expired/permission holds; ambiguous queue
response uncertain with no resend; installed owned live control ending in completed
processing and ordinary no-force tab closure. One bounded review, installed proof,
artifact parity and release. That implementation is proposed, not performed here.

Private evidence ~/.local/state/codex-wake/visibility-diagnosis/: repro.py/red.log,
screen-probes.json, wrap-probe.json, native-evidence.json. Source and preserved
native history are authoritative; Graphiti atlas found only an unrelated AuraCall
cloud, so no useful project recall. Memory disposition unavailable: no reviewed
Codex Wake group; non-write receipt memory-disposition.json retained privately.
