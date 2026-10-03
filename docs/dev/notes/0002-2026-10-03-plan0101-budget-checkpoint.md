# Plan 0101 restart-safe budget checkpoint

Parent plan: 0101, OPEN; campaign issue #181 remains OPEN.
Repository: CochranResearchGroup/codex-wake on github.com.
Custody: docs/p63-budget-checkpoint, primary owner, origin/main target.
Stop authority: user requested execution with stop/checkpoint before 750,000 goal
tokens; working threshold at or before 700,000. Boundary meter 625,906. Complete
this checkpoint and pause before opening the larger live-delivery proof. The
final goal readback, not this boundary sample, owns final token usage.

## Authority and startup

Read AGENTS.md and applicable docs/dev/policies before changes. Plan 0101 owns
the unchanged full goal; Plans 0100 and 0102-0105 own bounded accepted foundations.
Verify git status, exact local/remote branch SHA, canonical main, lane catalog,
issue/PR readbacks and installed command identity. A handoff is a locator, not
proof. Do not infer full acceptance from closed child plans or passing fixtures.
On resumption preserve the user's token ceiling unless explicitly changed; a
new session does not silently reset the goal's cumulative allowance.

## Integrated evidence

- Discovery PR #182: 9b43ab7a0d653dfcb05c8978e78971220cf4e9bf; existing-daemon
  read-only discovery and qualified Byobu tab selectors. Verification 0094.
- Identity/mailbox PR #183: 42893b190eb19c30dc702b2377893b1ba5736b88; explicit
  roots/capabilities, transactional messages/receipts and CLI. Verification 0095.
- Scheduler/receipt library PR #184: 6d4c399e11f3c08b5a048c61579675657cabcb08;
  generation leases, derived private jobs, uncertain holds and exact-message
  immutable receipt replay to SQLite Wake. Verification 0096.
- Operations PR #185: f3050bde52301518f5ac061835b5ac502198ed1c; rotation,
  metadata diagnostics and pinned retention preview/apply. Verification 0097.
- Hosted Python 3.11/3.12 passed each integration. Latest run 37145185923.
  Latest full local suite: 818 tests in 42.501 seconds, no retries.
- Latest isolated installed fixture: inbox request/reply, repeated identical job
  projection, cancellation, doctor, empty retention apply and old/new capability
  validation; 22 read connections closed, children zero before/after, zero runtime
  effect calls. All identities and roots are synthetic and disposable.
- Installed test environment is /tmp/codex-wake-p63-venv. Global package/service
  install was not changed. Rebuild from the desired durable commit before reuse.

## Important boundaries and unfinished gates

Automatic delivery is unqualified. turn/start can steer an active turn; a prior
idle read is not an atomic safety guarantee. Installed queue/start schemas alone
do not prove busy/composer/queued-work safety. Metadata/TUI matches are not a
runtime attestation. No implicit resume, retarget, new stdio server, production
enrollment, unrelated daemon restart or unqualified TUI paste is authorized by
a mailbox intent. Exact capability plus daemon namespace/thread/cwd provides
actor API authority; same-UID filesystem access is not security isolation.

ReceiptSignalAdapter is a library seam. Long-running receipt CLI, daemon source
restore and dispatch authority wiring remain unfinished. Production retention
pins remain conservative because qualified signal acknowledgements are not
cleared by that library. Pruning removes logical body rows; physical compaction,
compact ninety-day tombstones, backup/restore and secure erase are not qualified.
Capability rotation fences prior claims; explicit claim recovery across actor
generations remains unfinished. Do not reinterpret an existing claim as new work.

Remaining full Plan 0101 criteria: qualified exact-thread delivery with busy/
offline/composer safeguards; actual named disposable two-agent request/reply
and recipient acknowledgement; receipt workflow/skill and long suspension;
restart/reconnect/unload/restore; resource and multiroot installed qualification;
supervisor installation, migrations/rollback, release and runtime readback.
No production actor, root, service or live recipient was enrolled during fixtures.

## One bounded next packet

Qualify delivery capability from the installed runtime's authoritative protocol
and implementation semantics before effects. Freeze exact disposable thread/root/
bus IDs, one request and one reply maximum, finite timeout, cleanup owner and
OS resource observations. If the runtime cannot atomically prevent steering or
prove recipient/client identity, keep automatic delivery unavailable and report
that exact unmet criterion. Do not replace the full system goal with inbox-only
acceptance. Use the remaining cumulative allowance to decide whether a complete
proof can fit before starting; checkpoint instead of overrunning the user bound.

## Review and memory custody

/root/identity_review performed the one broad identity review; accepted F1 was
reproduced and corrected. The same worker later supplied disjoint mailbox and
scheduler fault tests (7 and 8), terminal success, accepted after source inspection
and included in comprehensive tests. No new broad review allowance is created by
this handoff. Implementation attempts and review bounds carry across plans.
Memory disposition unavailable: recorded_no_write receipt, zero Graphiti writes,
no authorized repository group established. Repository artifacts are authority.
