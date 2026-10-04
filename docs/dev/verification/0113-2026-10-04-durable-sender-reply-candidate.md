# Plan 0119 sender-arm checkpoint | 2026-10-04 21:19 UTC

Worktree and branch remain the successor execution lane; starting source
checkpoint `10fce9d`, gate checkpoint `3f00aea`. M1–M4 remain unproven.
No message, notification, shared restart, client reconnect or global install.
Actual wakeA/wakeB round-trip attempts remain 0/3.

Candidate native operator command `a2a delegate-receipts` grants bounded,
independent observation of listed notification-enabled senders' own outgoing
requests. Configuration pins wake root, bus, operator capability locator, exact
actor and generation; at most100 senders, private atomic writes with serialization
and readback. Actor capabilities cannot perform operator delegation.
Native agent command `messages arm-reply` authenticates the actual sender and
registers its exact request in the existing signal journal. No after-send operator
intervention is required. The owning worker advertises process-bound health and
reconstructs the existing receipt source family.

In sender-arm mode, the existing reply notification waits for a current firing
arm. Lifecycle locking holds cancellation across the bounded transport attempt;
expiry and independent authority are rechecked. The existing mailbox journal
records actual submission and uncertainty. A crash after mailbox submission but
before arm bookkeeping is reconciled from that exact send receipt without resend.
Generic A2A receipt/tmux dispatch remains fenced. Mailbox schema is unchanged.

Candidate TUI now checks the actual remote server's canonical home/provider
namespace, as well as thread and root. A timed-out event responder is dropped
before later submission. Generic server validation errors remain uncertain;
only explicit not-sent and unsupported-method failures permit retry.

Evidence:

- Rust check passed after namespace changes; retained patch reproduced on a fresh
  pinned archive with all patched file hashes and normalized lock verified.
- Locked runtime build passed. Current executable SHA256:
  `8c1315463e35083aa33e47e4f05137ed6d607f5c55d2bc1b4a536c046aa6390b`.
  Patch SHA256: `bbcf349398054e371003ce04aa894e8a6ee1c9445359ba88bb5efcdfd8b37212`.
  Owned build receipt `/tmp/codex-wake-plan119-runtime/build-receipt.json`.
- Built candidate isolated server again rejected unloaded exact-thread input
  without provider effects. This remains a capability guard, not M1 acceptance.
- 145 focused A2A tests passed in47.612s; seven sender delegation/arm checks passed
  in3.698s after the final delegation serialization/readback change.
- First expanded test run had a clock-continuity failure; its log is preserved
  as `test-reply-wake-first-failure.log`. A retry passed but was classified flaky.
  Transport fixture clocks were then pinned; mailbox clock-continuity checks
  remain separate. A later delegation test incorrectly reissued an existing actor;
  it was corrected to use the already issued capability and now passes.
- Candidate Wake wheel built and installed into the owned isolated venv
  `/tmp/codex-wake-plan119-wake-venv`. Native command help works without PYTHONPATH.
  This is candidate packaging proof, not released or global installed acceptance.
- Full Python presubmit is in flight, owned session2616,
  log `/tmp/codex-wake-plan119-runtime/test-presubmit-candidate.log`.

The explicit runtime activation question remains pending. Note0007 identifies
the selected package, impact on all shared-daemon clients, exact demo IDs and
rollback. Policy0021 additionally requires source integration on origin/main
before deployment. Next: complete presubmit/hosted checks and source integration;
then, only with activation authority, execute the bounded actual M1 packet.

Budget checkpoint: inherited996214 + current347872 =1344086 before writing,
ceiling1800000. Goal active. Progress:blocker_reduction; no live behavior acceptance.
Memory disposition remainsnot_durable for in-progress, unaccepted implementation;
non-write receipt recorded inverification0112. No additional memory write.
