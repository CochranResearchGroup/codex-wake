# Plan 0101 fresh-agent handoff

## Objective and authority

Continue the full local agent-to-agent communication system in Plan 0101,
lane P63, issue #181. The campaign remains OPEN. Do not substitute mailbox-only
acceptance for the system goal. Latest operator goal ceiling is 2,250,000 tokens;
earlier 750,000 and 1,500,000 limits in artifacts are historical. Carry cumulative
usage across meter resets. This handoff does not itself authorize new live actors,
roots, provider effects, or service installation.

Read AGENTS.md and relevant current docs/dev/policies before work. Canonical
authority order: current user instructions, repo policies, Plan 0101, bounded child
plans, verification receipts, then this locator. Read the plan's appended
execution checkpoints; its initial current-state paragraphs are historical.
The active meter presently reports paused, despite the later raised objective;
verify goal state and continuation authority rather than infer it from this note.

## Startup readbacks

Workspace: /home/ecochran76/workspace.local/codex-wake.
At handoff, tracked tree was clean before adding this note. Branch
feat/p63-receipt-restore; HEAD and PR #188 head:
8dd07138661ca8b9b8e5ce913ce73ec5074a7a7c.
Canonical origin/main: 24ddf11224a06c2b11764b66b8031be6242364c6.
Recheck local/remote SHA, status, PR/issue, active-lane catalog and installed
identity. The lane catalog may still project the older paused checkpoint branch;
do not interpret that stale projection as evidence of another active worker.
No subagent is active. Do not reset exhausted review allowances through a handoff.

## Landed foundations

- PR #182, 9b43ab7: read-only shared-daemon discovery and Byobu selectors;
  verification 0094.
- PR #183, 42893b1: explicit enrollment/capabilities and transactional inbox,
  read/ack/reply/cancel messaging; verification 0095.
- PR #184, 6d4c399: fenced scheduler, private notification jobs, uncertainty
  holds, and exact-message receipt replay library; verification 0096.
- PR #185, f3050bd: capability rotation, diagnostics and pinned retention;
  verification 0097.
- PR #186, 625bb9c: original restart-safe budget checkpoint, note 0002.
- PR #187, 24ddf11: foreground waits for attributable accepted/declined/
  completed/failed dispositions, exact historical receipt lookup, and shipped
  mailbox skill workflow; Plan 0106 and verification 0099.

Global package/service was not changed. All mailbox identities used so far were
synthetic and disposable. No production enrollment or actual named live-agent
round trip has been accepted.

## Open PR and exact blocker

PR #188: https://github.com/CochranResearchGroup/codex-wake/pull/188
Plan 0107 closes only the bounded explicit restore/source-guard seam;
verification 0100. Production authority configuration, automatic daemon discovery,
long-suspension CLI and installed process restart are unfinished.

Commits 532f2bc and 8dd0713 add a nonsecret exact-arm descriptor, restoration
against independently supplied mailbox/actor authority, receipt source registry
injection, participant/generation validation, and guarded daemon publication.
Generic injector delivery of a2a.receipt firing records is explicitly held as
unqualified; a receipt match must not invoke an old generic transport.

Latest hosted run 37148747612: Python 3.11 passed, Python 3.12 FAILED. Preserve
the failure; do not merge or blindly rerun. Failed job 111277982216. Local log
locator /tmp/codex-wake-p63-ci-failure.log (ephemeral; fetch again if absent).

1. test_webhook_http.WebhookHTTPTests.
   test_connection_and_ingest_capacity_reject_without_queue: with one admitted
   connection, exchange's socket.shutdown(SHUT_WR) raised ENOTCONN (errno 107)
   before response parsing. Admission may close the second socket first.
   Investigate fixture half-close handling while preserving exact 503 ADMISSION,
   complete response framing, one ingest call and no queued request assertions.
2. test_github_webhook_runtime.GitHubWebhookRuntimeTests.
   test_provider_timeout_runs_on_main_thread_and_fails_closed: first response
   correctly 503 VERIFICATION_UNAVAILABLE; second was 503 COMMIT_FAILED instead
   of 200 COMMITTED. The .25-second POSIX absolute deadline covers the entire
   ingress, including SQLite commit. Host contention is a hypothesis, not a
   demonstrated cause. Investigate before changing timeout budgets or tests.
   Retain main-thread deadline enforcement, recovery, and durable checkpoint proof.

No repair edits have been made to either webhook test. The interrupted preceding
turn only read policies and test source; no partially applied mutation exists.

## Verification already available

Current receipt tests: nine pass. Full local suite: 824 tests, latest 36.314s,
passed; focused receipt/injector 33 tests passed. Rebuilt isolated Python 3.12
receipt suite: nine tests in 1.105s passed. Environment:
/tmp/codex-wake-p63-receipt-venv; rebuild from intended commit before reuse.
An initial FD 4-to-5 observation was traced to /dev/urandom; initialized fresh
process baseline was 5-to-5, children 0-to-0. Preserve both observations.
Restoring the old daemon evaluation function made the revoked cached-receipt
regression fail (one unauthorized firing), while current code passes.
These results do not erase the current hosted failures or prove live delivery.

## One bounded next packet

Re-anchor current head and failed CI; inspect actual webhook runtime/deadline
and fixture ownership using CodeGraph for structural discovery. Resolve the two
observed failures with a justified bounded change, preserve original failure
evidence, run affected checks and required hosted gates on the final head.
Update verification 0100 and PR description to the actual final scope. Integrate
PR #188 only after review/CI policy gates pass. Do not count integration as full
Plan 0101 completion. Resume production authority configuration and receipt
suspension work only with their own bounded plan and acceptance evidence.

## Remaining full-system gates and hard stops

Installed Codex 0.160.0 schemas and official release source were inspected;
verification 0098. queue/start's idle guard does not establish composer/client
identity or installed implementation provenance. queue/add can execute after
active work finishes. Automatic delivery remains unavailable. No implicit
resume, retarget, separate stdio server or unqualified TUI paste.

Still required: qualified exact-thread delivery and busy/offline/composer guards;
actual named disposable two-agent request/reply plus recipient acknowledgement;
long receipt suspension; restart/reconnect/unload/restore; resource and multiroot
installed acceptance; supervisor packaging, migrations/rollback and release/
installed-runtime readbacks. Freeze exact IDs, roots, finite timeout, request/
reply maximum and cleanup owner before any live packet. Same-UID capabilities
provide API authority, not OS isolation.

Retention removes logical rows only; physical compaction, ninety-day compact
tombstones, backup/restore and secure erase remain unqualified. Actor rotation
fences prior claims; cross-generation claim recovery is unfinished.

## Budget and memory custody

Observed cumulative floor before this handoff: 957,432 tokens (original paused
644,919 + resumed paused 73,733 + unmetered observed 24,873 + reset paused 1,591
+ subsequent paused 212,316). A further reset meter read 1,593 before writing
this note; small late outputs are not fully counted. Use a conservative reserve,
and checkpoint well before 2,250,000 rather than treating a fresh meter as zero.

The prior turn's mandatory memory disposition was unavailable, receipt:
/home/ecochran76/.graphiti-openclaw/state/closeout-memory/
20261003T193829Z-remember.json. No authorized repository group or healthy MCP
was established; zero Graphiti writes. This handoff makes no new memory-write
claim. Do not seed raw messages, secrets, full logs or speculative findings.
