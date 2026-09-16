# Verification 0077: Installed Webhook Composite Qualification

Date: 2026-09-16
Plans: `0075`, `0076`, `0077`
Issue: CochranResearchGroup/codex-wake#107
Installed candidate: `2cdfaf75308f21f7b8464b94a5762668a46411f9`
Correction candidate: `97660040b0d85a9eef1eb29cfd6b76bb8dfe41f5`

## Result

PASS as a composite qualification with the failed-safe attempt preserved. The
installed candidate proved wheel provenance, owner-only `PrivateTmp`-visible
execution, service readiness, manual restart identity, signed webhook commit
and deduplication, provider exclusion, and dispatch absence. Its source-only
poll fixture then failed because it omitted the daemon's record publisher, and
its immediate cleanup bind check observed delivery sockets in `TIME-WAIT`; the
original receipt therefore correctly remains `overall: failed` and `safe:
false`.

Plans 0076 and 0077 corrected and independently proved only the missing polling
axes without another service effect. The generated provider-free fixture now
projects the match to firing and carries the exact GitHub health code/time.
Fresh host evidence separately proves the removed service left no unit,
process, listener, or occupied port.

## Installed Candidate And Service Evidence

- Commit `2cdfaf75308f21f7b8464b94a5762668a46411f9`; tree
  `92145fee8f8d465c410eaa60f137143da35bc5c4`.
- Wheel SHA-256
  `3ebf1053b309634c05684632d763f4beec59b3432283bd720890eeb4c630acdf`;
  version `0.5.2` and isolated Python 3.12 module provenance were captured
  before installation.
- The supported unit became ready on `127.0.0.1:8820` with PID `8112`, process
  start ticks `1861616`, zero automatic restarts, and socket inode `8338599`.
- Manual restart produced PID `8308`, start ticks `1861841`, zero automatic
  restarts, and socket inode `8343874`.
- Frozen signed delivery results were HTTP 200 `COMMITTED`, HTTP 200
  `DUPLICATE`, and post-restart HTTP 200 `DUPLICATE`.
- The managed source reader stopped before the service effect; its bootstrap
  blocked signal-source construction and disabled dispatch. The sanitized
  receipt records provider access and dispatch as absent.

## Preserved Failure Evidence

- Sanitized receipt:
  `/tmp/codex-wake-p53-c4-v2-service-effect-1.json`.
- Receipt SHA-256:
  `8cbb2508dfb8ee9f96a5051b4cb4953d42e769de493fed3cd19c0ab098b6e605`.
- The receipt remains failed at `provider_free_poll` with `RuntimeError`; it is
  not rewritten by the later correction.
- Immediate cleanup proved unit absence, inactive/not-found state, PID zero,
  uninstall success, no matching process, and identical six-unit before/after
  failed-manager sets. Its port bind check was false while three completed
  loopback connections remained in `TIME-WAIT`, so cleanup remained
  conservatively unsafe and retained the recovery root.
- Recovery root
  `/home/ecochran76/.local/state/codex-wake/qualification/p53-c4-_6ig13jq`
  remains owner-only mode `0700` and unmodified by corrective verification.
- Later ambient failed-unit membership changed independently. Only the exact
  contemporaneous receipt baseline is attributed to the attempt.

## Provider-Free Polling Correction

- Checkpoint `84d59fd` opens the explicit fixture module with
  `WakeRecordPublisher(root, current_reader_capability(root))`, matching the
  daemon default path.
- Checkpoint `9766004` projects the persisted GitHub health code and aware poll
  time into each per-instance reconciliation result.
- The executable generated-fixture test uses a fresh armed journal and proves:
  receipts `1 -> 1`, matches `0 -> 1`, pending `1 -> 0`, firing `0 -> 1`,
  `fired=1`, `dispatched=0`, and `submitted=0`.
- Explicit production-client and dispatch tripwires both remain at zero.
- Independent closed-world review reproduced the same counts, accepted the
  bounded ten-code GitHub/store health vocabulary, and verified unknown codes
  and naive timestamps remain rejected.

## Fresh Cleanup Readback

After the delivery sockets aged out, fresh host checks proved:

- `codex-wake-github-webhook-p53-c4-installed-canary.service` is
  `not-found/inactive/dead` with PID `0`, restart count `0`, and no fragment;
- the exact source-specific unit path is absent;
- no fixture-bootstrap or managed-reader process remains;
- no socket listens on port 8820 and a fresh bind probe succeeds; and
- the retained failed receipt and private recovery root remain unchanged.

## Validation

- 2 targeted P76-R01 tests passed.
- 58 daemon plus installed-runner tests passed.
- 26 installed-runner focused tests passed under independent review; 3 targeted
  GitHub daemon tests also passed.
- 519 comprehensive Python tests passed.
- 12 OpenClaw plugin tests passed.
- Python compilation, diff hygiene, and active/goal planning audits passed.
- Independent reviewer model/effort and cost telemetry were unavailable.

## Acceptance Boundary

This artifact qualifies installed loopback behavior and provider-free polling
for #107. It does not prove external HTTPS ingress, provider webhook mutation,
live GitHub delivery, wake dispatch, release, deployment, or global runtime
installation. Those remain separate #108 and #109 gates.

## Integration

- PR #119 targeted `main`, linked `Closes #107`, and resolved the exact
  published head `6962a76f608be6b0282356d91301cf4520f1852d`.
- Release gates passed on Python 3.11 and 3.12; no unresolved review threads,
  reviews, or conversation comments remained.
- The PR squash-merged as
  `920e5b84314a8063c8a7f3ed1c9d3523d32ab92c`, and GitHub closed #107.
- Post-merge canonical-main validation passed 519 Python tests, 12 plugin tests,
  compilation, diff hygiene, and active/goal planning audits.
