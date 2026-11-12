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

## Current State

PR538 delivered compact/plain/no-STALE presentation; the original failed
loaded-host deadline and manual reconciliation remain in the delivery record.
Subsequent P216 installed100-tab/46-tab qualification is recorded separately in
[accepted receipt](../evidence/plan0216/qualification547/accepted-eighth.md).
That later delivery is not pending implementation. This plan's OPEN label is
retained for explicit remaining-scope disposition rather than closing it by
association. Later [P223](0223-2026-11-11-tmux-subscription-crash.md) owns the
recorded disabled automation state. No new runtime qualification or activation
is claimed here.

## Delivery

PR538mergedc59b5c8 and exact private qualified wheel649fb27f deployed.25sourcechecks
and3installedchecksPASS; all305private package members verified. Initial installed
probe raced installation and failedimports, retained; rerunaftercompletionPASS.
Normal live resume still exceeded10sunderload. Reconciled through existing owner
apply with90sdeadline and cached provenance, original baseline preserved;44tabs
readback confirms compact/plain/noSTALE. Monitorstopped to avoid churn; automatic
loaded-host deadline remains open. No healthfreshness claims or providercalls.
See deployment.json. Memoryforbidden:noexplicitmemory-writerequest.
