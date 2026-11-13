# LOCAL-P230 | Native mailbox first contact and notification bindings

State: CLOSED
Ticket: LOCAL-P230
Owner: primary WebB
Priority: P1
Branch: fix/notification-binding-lifecycle
Dependencies: none
WIP limit: one implementation lane

## Current State

CLOSED: systemic source repair merged (PR600,605,606), qualified dev18 participant
worker/entrypoints activated. Real native first-contact and replacement-client
notification/read/claim/completion verified without manual binding. StableTime is
used through the existing adapter; no host clock change or production-policy reset.
See [runtime acceptance](../evidence/plan0230/runtime-acceptance.md).
Existing loaded MCP connections retain older code until reconnect; shared refresh
requires separate effective permission and was not forced. Historical failures,
including the missed final composer call, remain in the evidence. Owned diagnostic
actors/tab/binding cleaned; conversations and receipts retained. Final checkout can
close after remote custody of this acceptance record is verified.

## Scope and acceptance

Remove per-session manual preparation from host-delegated mailbox first contact.
A verified caller may contact a verified native recipient inside existing enrolled
roots without that recipient first polling. Existing revocation, disabled grants,
root boundaries and fixed-actor behavior remain effective. Opt-in notification
workers must resolve missing and replaced tmux client bindings for already admitted
notifications without weakening composer, exact-identity or uncertain-effect fences.
No implicit root enrollment, new grant, automatic replay, daemon replacement or
working-host deployment. Existing explicit binding mode remains supported.

## Implementation history

Isolated implementation worktree from e8c79a79; root checkout preserved. Reuses
existing native bootstrap and notification harnesses. First-contact regression red:
public CommandRunner inbox-only send reports exact original recipient authorization
error when recipient has not polled. A previous live diagnostic proved a manually
bound WebB receives notifications; this is symptom evidence, not systemic acceptance.

Source repair and serial review complete. Exact installed candidate passes 115
focused tests; broader installed smoke is blocked by measured host clock jumps. See [qualification](../evidence/plan0230/qualification.md). Source is committed and published in draft PR600; integration and working-host
activation remain outstanding until the installed-smoke clock gate passes.
No active service configuration or installed entrypoint changed in this slice.

## Definition of done

Observe red then green for first contact and missing/replaced notification binding;
cover revoked/unenrolled/ambiguous peers and preserve explicit-mode behavior. Run
focused local checks, document installed-versus-source distinction and leave a
reviewable patch. Commit, merge and working-host activation remain separate.
Remote branch provides durable custody. Close the clean task checkout after publication;
recreate from the same branch when the host-clock gate clears. No other lane owned.

## StableTime correction (operator direction)

The operator selected existing StableTime for clock problems; do not change the
host clocksource. Current StableTime MCP and installed Wake adapter both provide
finite qualified NTS evidence. Extend the existing mailbox time-policy seam with
--require-stable-time, provider pinning without guest/plain-NTP fallback, and a
StableTime variant of the original installed mailbox workflow. Preserve legacy
checkpoint/history. Pending legacy work holds migration; do not reassign its
uncertain deadline semantics. Older readers must reject the new pinned policy.
No production bus migration is implied by source qualification. Re-qualify the
immutable candidate before proposing source integration and scoped activation.

StableTime correction qualified: final installed dev16 candidate163PASS and original
installed mailbox workflow with --stable-time PASS. Source review has no outstanding
accepted finding. The earlier host-clock gate is superseded by qualified StableTime
use; no clocksource change. Production bus already uses network time and is not
migrated. Next: integrate source, then activate the qualified worker/discovery code
with compatible existing time policy and verify actual new-session delivery.

## Native acceptance extension: wrapped footer

Initial merged source eac0d01e activated as qualified dev16. New sender contacted
an actor-free/unpolled native recipient; automatic binding and completion passed.
Replacing only that owned diagnostic client refreshed its PID/binding generation,
but the pending notice hit composer_protected. Idle capture reproduced a narrow
footer wrapping the known session title over two physical lines. Strict row count,
not a draft or unsafe modal, rejected it. This is a current runtime finding; the
older historical uncaptured occurrence is not retrospectively proven identical.

Bounded branch fix/p230-wrapped-footer from integrated main owns the correction.
Acceptance: recognize only a reconstructed footer ending in the exact fresh native
session name, pass that metadata through probe and pre-submit recheck, retain
unknown/draft/mismatch protection. Exact installed dev17 candidate25focusedPASS;
actual captured pane now eligible with metadata and held without it. Integrate
before worker activation, then reconcile original pending notice without resend.
