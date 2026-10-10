# Ticket0145 unloaded-recipient evidence reconciliation — PASS

No new native effect was needed. Original Plan0138 private
recipient-before-dispatch.json and recipient-before-v2.json both report
notLoaded for01a12681-3c92-7b30-b5d7-e3a2dbbee7c8 at the enrolled root.
This proves a server-unloaded conversation, beyond a closed pane alone.

Original explicit request msg_afb5abf5776c430a82a81581d2174fcf submitted under
attempt_3b714b08b9fa49dab71f17698fa15bf3, native receipt
01a12695-8514-7062-8332-e936b9eaedb1. Saved native transport resumes the exact
thread; recipient-completed-v2-thread.json retains its original seed
01a12681-cce1-7832-afa3-bdc405ece189 and completed notification turn
01a12695-8516-7342-8f8f-1e5195eb0461 with both exact message/attempt markers.
Public request accepted/submitted/completed, claim receipt
e92d71944c5d45e4a627215680b67ad6, terminal receipt
ffd2e61291c248d6b958a175e685a7fe. The failed first exchange remains preserved.

Default original msg_a42adc299b5446079eb2e0f903cc56d4 was
accepted/deferred/unread with offline receipt and zero lifecycle/queue effects,
then deliberately cancelled. Plan0138's sender reply was received, not completed;
this reconciliation does not upgrade that historical outcome.

Source/scope mapping: saved binding and shared notification prompt are byte
unchanged from released0.11.1/2e87f66 to0.11.2/0076ae4. Relative to0.11.0,
only shared claim-aware pointer instructions changed in saved delivery;
exact-thread observation/resume/authority/queue behavior stayed intact.
Scheduler adds derived current-recipient authority for live delivery without
altering saved policy or immutable envelope. Current installed117-control selection
includes saved dispatch, default zero effects, malformed/unavailable runtime,
busy/identity change, reopened composer, capability rotation, cancellation/expiry,
lost confirmation with no resend, independent reply arm and bookkeeping recovery.
Current actual native queue/thread operation is separately fresh in0142/0143.
All81package files in activated0.11.2 match that tested candidate.

Thus the existing notLoaded→resume→completed proof qualifies this ticket; its
conditional new live sample is unnecessary. No server-wide unload/restart,
archive/delete or unrelated thread change occurred. Earlier owned cleanup is in
Plan0138/cleanup.md; latest owned tabs also closed in0143. Raw source-artifact
hashes and reconciliation stay private in ~/.local/state/codex-wake/plan0145/.

Memory disposition: unavailable; no reviewed Codex Wake Graphiti group available.
Non-write receipt retained privately. Recovery tickets0146 onward remain OPEN.
