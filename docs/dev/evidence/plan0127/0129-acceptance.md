# Ticket0129 installed candidate acceptance

Candidate identity: `0129-source-identity.json` binds editable installed Wake0.8.0 candidate to exact source hashes, parent1bb976b and Codex0.162.1. Global Wake installation is unchanged. Test clients use dedicated socket `/tmp/tmux-1000/plan127-native`, not shared user tabs.

| Criterion | Result | Evidence |
| --- | --- | --- |
| Explicit new directory / exact resume; thread and tab identities | PASS | `0129-new-and-idle-close.json`, `0129-lifecycle-first.json`, `0129-resume-after-idle-close.json`, `0129-resumed-identity.json` |
| Default attachment reuse, explicit extra attachment, no implicit worktree | PASS | `0129-lifecycle-first.json`, `0129-explicit-extra-force-close.json`; open invokes native conversation creation and tmux, never Git/worktree creation |
| Active/pending guards; force preserves and reports durable work | PASS | `0129-busy-close.json`, `0129-busy-native-transcript.json`, first lifecycle receipts, `0129-unpublished-signal-close.json`, `0129-mailbox-close.json`, `0129-force-preserved-authorities.json` |
| Real new/resume/reuse/close and identity mismatch | PASS | Above plus `0129-idle-close.json`, `0129-identity-mismatch.json` |

Focused validation:63 tests passed across lifecycle, sessions, signal store, mailbox and native delivery. Seven lifecycle tests exercise the public CLI boundary; native process delivery and visible-client behavior are separately proven by the installed live receipts. Full Python suite passed975 tests in102.172 seconds; compilation and diff hygiene pass. A subsequent lifecycle command-error conversion passed23 affected session/lifecycle tests. Source review is adjudicated; both Standards and Spec pass within the disclosed boundaries.

## Primary review against parent1bb976b

Standards: pending work stays in existing JSON, signal and mailbox authorities; read inspection introduces no broker, database or schema migration. Source/installed/live identities are retained separately. Accepted review findings: skipped/damaged record attribution, unpublished signal publication, pending mailbox work, split-tab truthfulness and uncaught selection errors. Fixes and affected checks are recorded. No parallel worker is required for this bounded review.

Spec: native Codex creates and resumes conversations; Wake manages visible attachments. Closing never archives, deletes a conversation, cancels a wake or consumes mailbox work. Ready is distinguished from creation, and selection ambiguity refuses even under force. Busy-state refusal is corroborated by the exact native turn and completed sleep. Force preservation is followed by fresh signal and mailbox readback.

## Failures and limits

The first split-tab sample returned a traceback; retained in `0129-split-tab-refusal.json`. The fixed rerun returns the existing structured selector error and preserves both panes. A first mailbox fixture used unsupported delivery=`manual` and was rejected before admission; that private bus is retained. The corrected fixture uses supported inbox admission with notification suppressed. This is close-guard proof, not a messaging round-trip claim.

Split tabs refuse this tab-close operation, including force, to protect other panes. Close inspects the explicit wake root, selected conversation directory root, registered roots, default user buses and explicitly supplied `--bus-root` locations. Undisclosed custom stores cannot be discovered; custom buses must be supplied explicitly. Unreadable inventory holds ordinary close and is reported under explicit force. The routine is a bounded snapshot and process-identity revalidation, not an atomic transaction over tmux plus every durable store.

The candidate is not released. Tickets0130–0132 and complete lifecycle/migration acceptance remain open.
