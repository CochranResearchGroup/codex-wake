# LOCAL-P214 | Compact neutral tab formatting

State: OPEN
Ticket: LOCAL-P214
Owner: primary
Priority: P1
Dependencies: P213
Branch: fix/compact-tab-format

## Outcome

Operator rejects current colors, bulk and repeated STALE. Add explicit compact
and show_stale display preferences. Compact uses type+tiny activity cue+native
name, suppresses profile and idle/unknown metadata. Plain mode removes palette.
Hide repeated STALE text only; preserve native expiry and stale inspect state.
Existing explicit full layout remains compatible. Qualify private installed then
apply compact/plain/noSTALE to user's default session, preserving rollback baseline.
No changes to provider/process identity or activity evidence semantics.
