# Persistent wake deployment

Operator authorized review, merge and deployment on 2026-11-13.
PR #618 merged as `a16b4de4b054fe470f865e1fb64b2965140565c1`. The existing single two-axis review and single
TDD remediation remain authoritative; no second broad review was run.
Main advanced only by a runbook record; its one conflict preserved both intents.
Merge-source focused tests39 PASS17.019s, Ruff/policy/diff PASS. Hosted paid CI skipped.

Exact merged wheel SHA256 `f997f4535d04891a7274e33fde5f9bf421d7fc40e03e6b533296c73f7444547d`.
Immutable prefix `~/.local/share/codex-wake/releases/0.22.0.dev20-a16b4de`.
All332Python members match source/wheel/install; all31dependencies unchanged.
Separate Linux UID1017 installed-wheel tests39 PASS16.148s (Python3.12.3; shared
kernel). Working prefix Python3.12.13 installed CLI register/show/revise/cancel PASS,
armed=false. Provider responses in focused tests are injected, not live acceptance.

All9stable launchers switched; tab monitor PID922854, matching
snapshot generation `a2e5f3aa17d14bb7b476a7dfd0cd83c0`. Settings byte-identical.
Supervisor PID923877 uses the new prefix; fresh root heartbeat
advertises recurring_schedules_v1 and wake_session_modes_v1. Existing17root
registrations retained; no new reconciliation holds. The pre-existing im-receipts
hold and inactive roots remain unchanged.35native processes preserved at final
cutover; no native daemon restart, terminal input or production schedule creation.
Existing controller/MCP connections retain imported code until normal reconnect.

First cutover guard saw transient native helper PID911982 exit and attempted
rollback. Reused operation IDs in the deployment script caused cached monitor
operations; corrected to unique per-action IDs, reconciled actual process identity,
and completed a fresh cutover. Original attempt artifacts retained, no native
process termination was issued. Final state was verified from /proc and heartbeats.

Olddev19prefix, exact launcher preimages and supervisor drop-in preimage remain
private rollback custody. Restore recorded links/drop-in, reload systemd and restart
only tab monitor/supervisor. No state migration or deletion performed.
Raw receipts: `~/.local/state/codex-wake/persistent-610-deploy/` outside Git.

Live provider execution and real closed-Byobu restoration were not exercised;
this is deployed code and monitor capability proof. New schedules still require
explicit operator/agent modes and policies. No native daemon upgrade occurred.
Memory disposition forbidden by explicit-request-only developer boundary.
