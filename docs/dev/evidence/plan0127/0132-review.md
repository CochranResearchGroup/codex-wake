# Ticket0132 review

Comparison: baseline5175f5f to the frozen working-tree source patch. Parent
Plan0127 and ticket0132 are the specification. Standards: repo policies0003,
0005,0006,0013,0014,0016 and the code-review skill smell baseline. Primary
review performed serially; repository plans are the requested ticket tracker.

## Standards

No accepted blocking findings remain. Source reuses record storage, lifecycle
locks and the existing native scheduler. No parallel store/broker, historical
cleanup, implicit fallback or shared runtime change is introduced. Migration
originals are exclusive private files, synchronized before record replacement.
Focused public-CLI tests retain red/green evidence; installation and real native
turn receipts qualify effects. Derived caches and operational state stay out of
git. Optional naming/format cleanup does not widen this ticket.

## Spec

Accepted blocking findingM132-1: schema1 candidate native records can be
misinterpreted by older readers during rollback. Resolved by native schema4,
explicit metadata-only promotion, actual installed0.8 hold and capable-reader
execution/reconciliation proof.

Accepted blocking findingM132-2: new native record classification could crash
on malformed expiry/due/type/status. Resolved by fail-closed validation; the
public scheduler regression retains failing samples and unchanged damaged
state after repair.

Implicit basic tmux selection is retired only where native time/file parity is
qualified. Explicit compatibility, advanced signals, process/file-change
predicates, tracked receipt contracts and existing readers remain supported.
Network-time native parity is expressly unqualified. Migration preserves IDs,
prompts, target, status, nonce and uncertainty; backup conflicts refuse.

Migration and installed-release preparation pass their source gates. Hosted
integration, publication and normal installed rollout remain parent gates;
this review does not claim them complete.
