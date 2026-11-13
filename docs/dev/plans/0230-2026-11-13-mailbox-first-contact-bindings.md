# LOCAL-P230 | Native mailbox first contact and notification bindings

State: BLOCKED
Ticket: LOCAL-P230
Owner: primary WebB
Priority: P1
Branch: fix/notification-binding-lifecycle
Dependencies: none
WIP limit: one implementation lane

## Scope and acceptance

Remove per-session manual preparation from host-delegated mailbox first contact.
A verified caller may contact a verified native recipient inside existing enrolled
roots without that recipient first polling. Existing revocation, disabled grants,
root boundaries and fixed-actor behavior remain effective. Opt-in notification
workers must resolve missing and replaced tmux client bindings for already admitted
notifications without weakening composer, exact-identity or uncertain-effect fences.
No implicit root enrollment, new grant, automatic replay, daemon replacement or
working-host deployment. Existing explicit binding mode remains supported.

## Current State

Isolated implementation worktree from e8c79a79; root checkout preserved. Reuses
existing native bootstrap and notification harnesses. First-contact regression red:
public CommandRunner inbox-only send reports exact original recipient authorization
error when recipient has not polled. A previous live diagnostic proved a manually
bound WebB receives notifications; this is symptom evidence, not systemic acceptance.

Source repair and serial review complete. Exact installed candidate passes 115
focused tests; broader installed smoke is blocked by measured host clock jumps. See [qualification](../evidence/plan0230/qualification.md). Source is being published for review; integration and working-host activation
remain outstanding until the installed-smoke clock gate passes.
No service configuration or installed package changed in this slice.

## Definition of done

Observe red then green for first contact and missing/replaced notification binding;
cover revoked/unenrolled/ambiguous peers and preserve explicit-mode behavior. Run
focused local checks, document installed-versus-source distinction and leave a
reviewable patch. Commit, merge and working-host activation remain separate.
Worktree retained for review until changes have durable custody; no other lane owned.
