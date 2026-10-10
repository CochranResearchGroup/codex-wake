# Plan0138 unit1 — Same saved conversation completed

Installed source: v0.10.1 / 4aabb57cf4be8b88885b2e8005b4ecce949479d1.
Normal private supervisor PID50807 processed the original wake exactly once.

Recipient `01a1266b-d696-7880-b39b-5e170181236d` was verified notLoaded before
registration; its owned Byobu window was already closed with history preserved.
The default control held with attempts0 and was cancelled. The explicit original
wake `wake_20261010_153021_abc7` retained same_thread policy and due15:31:51UTC.
At15:31:54UTC it resumed that exact thread and accepted one queue submission,
`cfd1e960-538c-417b-b685-810b27b4d0d4`. Originating turn ended before due.

Read-only native history proves completed follow-up turn
`01a12671-4326-79a3-9640-e0e36478a60f`, with the original wake/submission IDs,
alongside completed seed turn `01a1266c-3f98-7c92-aae5-2baed0a1b582` in that same
thread. The follow-up verified exact seed bytes and wrote exact
`P68_SAME_SAVED_THREAD`; the marker was independently read back. No manual reply,
replay, duplicate wake, replacement conversation or shared-daemon restart occurred.
The saved thread returned to notLoaded after completion. No test tab remains.

Private original record and native readback:
`~/.local/state/codex-wake/plan0138/wake/submitted/wake_20261010_153021_abc7.json`
and `native-completed-thread.json`. The record itself reports queue acceptance;
completed native history supplies the separate execution proof.

The archive timeout and rejected unarchive from setup remain in native-checkpoint.md
and private receipts; this result does not claim those lifecycle RPCs succeeded.

Unit1 PASS. Agent-message integration and unattended mailbox request/reply remain
open; this scheduled-wake result does not qualify either. HostedCI remains waived.
