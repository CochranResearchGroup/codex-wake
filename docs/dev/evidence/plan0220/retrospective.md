# Plan0220 retrospective and actions

State: TRACKED_NOT_IMPLEMENTED. Owner: primary / ecochran76. Date: 2026-11-11.

Source scope: visible governor qualification exchange, current repository artifacts and retained u7 evidence. Earlier prompts do not establish a complete execution log. These findings do not count as the scheduled final code review.

GitHub tickets own outcome and acceptance. [Action index](retro-actions.json) records verified creation/readback. No fixes or deployment are claimed.

Important correction to the initial retrospective: receipt summarization already exists (closed #442, scripts/summarize_receipt.py); finding6 is an adoption/typed-adapter gap. Existing dependency preflight and closed #353 must be reused where applicable. The repo already has lint/unit/package checks; hosted checks are replaced by applicable local validation under operator policy.

| Finding | Priority | Tracked action |
|---|---|---|
| 1 | P1 | [#576: Observe terminal governor results before acceptance cleanup](https://github.com/CochranResearchGroup/codex-wake/issues/576) |
| 2 | P1 | [#577: Preflight native governor qualification before starting a journey](https://github.com/CochranResearchGroup/codex-wake/issues/577) |
| 3 | P1 | [#578: Require live process containment evidence for native cancellation changes](https://github.com/CochranResearchGroup/codex-wake/issues/578) |
| 4 | P1 | [#579: Detect stale source and package identities in qualification summaries](https://github.com/CochranResearchGroup/codex-wake/issues/579) |
| 5 | P2 | [#580: Count resumed work turns independently of owner notices](https://github.com/CochranResearchGroup/codex-wake/issues/580) |
| 6 | P2 | [#581: Use bounded receipt summaries for native qualification evidence](https://github.com/CochranResearchGroup/codex-wake/issues/581) |

## Evidence and implementation guidance

### F1 — #576

UIu6 waited12s while native CLI allowed15s; u7 waited20s and exposed an actual terminal timeout. Source: scripts/goal_limit_native_ux_acceptance.py:887, /tmp/p220u7/receipt.json.

Proposed change: Use one explicit deadline contract in the existing acceptance runner; preserve terminal CLI result and operation phase before cleanup. Keep diagnosis of the actual resume timeout under #572.

Cheapest meaningful verification: A deterministic check rejects observation deadlines shorter than command timeout plus a declared margin.

Dependencies: None; coordinate edits with #572.

Maintenance: Low; small deadline contract and one existing-runner regression.

### F2 — #577

Plan0220 UI setup required canonical account config, private umask, short sockets, paginated/V2 capabilities and authenticated clock corrections. Source: docs/dev/evidence/plan0220/qualification.json retained_setup_failures and UI01/u2/u3 receipts.

Proposed change: Extend existing qualification entry points and reuse scripts/validation_preflight.py where applicable. Verify effective prerequisites under the exact test UID and private cwd; do not build another framework or duplicate closed #353 host enforcement preflight.

Cheapest meaningful verification: Missing V2, stale clock configuration and overlong socket path each produce a precise prerequisite failure with zero model requests.

Dependencies: None; serialize shared script edits with #572/#574.

Maintenance: Medium; native capability/config contracts evolve.

### F3 — #578

backend-watcher-loss-05 interrupted root/child turns but left two exact sleep processes live despite stopVerified=true. Fixed in native v2; raw red retained. Source: Plan0220 qualification.json delegated_containment_v1.

Proposed change: Wire the existing delegated native limit/watcher-loss acceptance into the applicable local changed-surface validation guidance/profile. Reuse current process identity assertions; do not create a parallel fixture framework.

Cheapest meaningful verification: Cancellation/process-admission changes select or explicitly require existing live-tool qualification; unrelated docs changes do not launch native work.

Dependencies: Final #574 exact-package evidence must be reconciled before declaring adoption complete.

Maintenance: Medium; real native gate is costly, so select it by affected surface.

### F4 — #579

Plan0220 qualification.json still names e18b/80c8 and pending v2 fields while final u7 receipt names1171 and a resume failure. Source: docs/dev/evidence/plan0220/qualification.json and /tmp/p220u7/receipt.json.

Proposed change: Derive or validate one compact current qualification index from immutable receipts. Keep old runs as history; ticket outcomes and run verdicts retain separate authority.

Cheapest meaningful verification: Current index identifies exact Python/native source and hashes, latest verdict, ticket gate and cleanup state.

Dependencies: None; coordinate artifact ownership with #574.

Maintenance: Low to medium; explicit receipt schemas and cross-reference validation.

### F5 — #580

FinalV3 watcher-loss raw len(new_ids)==1 check included one genuine work turn and one exact owner-recorded engagement notice. Offline owner-record reconciliation qualified one continuation while preserving raw FAILED_PACKET. Source: backend-watcher-loss-v3-01/retained-notice-disambiguation.json.

Proposed change: Correct the existing public continuation acceptance assertion using operation started_turn_id and provider metadata; subtract notices only through exact authoritative owner records, never prefix heuristics.

Cheapest meaningful verification: Replay retained notice plus one real work turn: pass with exact operation/provider identity.

Dependencies: None; serialize backend acceptance script edits with existing lane.

Maintenance: Low; typed distinction at existing assertion seam.

### F6 — #581

This retrospective printed the complete u7 receipt, including hundreds of source hashes, and truncated useful output. Existing scripts/summarize_receipt.py from closed #442 already handles validation/cleanup schemas, but not the native journey receipt.

Proposed change: Adopt the existing summary command and add the smallest explicitly typed native-qualification adapter needed. Update existing developer navigation; no second summary CLI and no global AGENTS expansion.

Cheapest meaningful verification: Native summary shows verdict, exact source/package identities, elapsed time, failed stage and cleanup census with raw locator.

Dependencies: None; related #439/#442 remain unchanged.

Maintenance: Low; reuse existing bounded summary and focused public tests.

## Execution boundaries

WIP stays with current #572/#574 until the governor continuation blocker is resolved. Follow-up tickets are READY for planning but dependencies and shared-file custody govern implementation. Do not open parallel replacements for existing runners. Prefer deterministic local checks for mechanical errors; no global AGENTS changes. Keep previous failures immutable.

The actual u7 extend/resume timeout remains under #572, with installed acceptance under #574. No duplicate product-defect ticket was created. The final broad review and bounded TDD pass remain pending.

Memory disposition: forbidden for agent-memory writes; this user-authorized repository record is the durable project artifact.
