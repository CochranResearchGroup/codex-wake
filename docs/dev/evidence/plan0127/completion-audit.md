# Plan0127 completion audit

Objective: execute the full Plan0127, including all five tickets, actual installed
workflow, migration, integration, release and truthful closeout. One primary
owner; no substitute prototype or fixture-only completion. Audit began with
completion unproven. All behavior, migration, source integration, release and
terminal-runtime requirements now pass. Documentation closeout is prepared on
docs/plan127-completion and must integrate before the goal is marked complete.

Authority: Plan0127 and tickets0128–0132; canonical source via PR227; audited
repairs dc235a9; installed release-qualified-source-wheel.json binds all78 modules.
Raw evidence referenced below is under this directory. Historical failed samples
remain present. Prior receipts are reused only within the explicit invalidation
map in release-evidence-invalidation.json.

## Parent user stories

| ID | Requirement | Verdict and inspected evidence |
| --- | --- | --- |
| S1 | Humans identify the intended agent by visible tab | PASS: sessions resolve/open return exact thread and attachment; 0129-lifecycle-first/new-and-idle-close and release-open/reuse. Source selector guard and session tests cover ambiguity. |
| S2 | Ordinary agent communication uses native Codex | PASS: release-final-native-A includes actual send_message_to_thread MCP call; release-final-native-B contains its assigned worker turn. No Wake mailbox admission is used. |
| S3 | Durable condition follow-up survives sender turn end | PASS: release-final-arm-record plus native A/B; A ends initial turn, B creates condition, A resumes15s later and reads42. |
| S4 | Scheduler submits without initiating TUI | PASS: normal supervisor delivery in release-installed-acceptance; final corrected wake completes with owned TUI server absent, release-counter-record/native and release-final-deployment. |
| S5 | Explicit new conversation in chosen directory | PASS: release-open and 0129-new-and-idle-close return new native thread, chosen cwd and pane. |
| S6 | Resume one exact conversation visibly | PASS: 0129-resume-after-idle-close/resumed-identity; no replacement thread. |
| S7 | Reuse default, extra attachment explicit | PASS: release-reuse and 0129-explicit-extra-force-close; selected thread reused, deliberate extra attachment qualified. |
| S8 | Close preserves conversation | PASS: release-close-cancel closes B; release-closed-B reads its retained native history afterward. |
| S9 | Active work and pending wakes guard ordinary close | PASS: release-busy-B/busy-close-final proves active native turn with code2; release-close-cancel proves idle pending guard then distinct cancellation. |
| S10 | Force reports affected work without cancellation | PASS: 0129-explicit-extra-force-close reports exact affected_messages/affected_wakes; 0129-force-preserved-authorities verifies both retained. Later cleanup stdout gap is disclosed, not invented as reporting proof. |
| S11 | Missing target holds to expiry; resume explicit/same-thread | PASS: 0130 detached/busy expiry and headless resume receipts; 0128-unavailable-held/expired corroborate no submission. release-counter-native proves current exact-thread execution with explicit policy. |
| S12 | Interrupted effects reconcile before any retry | PASS: 0130-after-acceptance-reconciled/auto-reconcile-result attribute exact turn without second intent; 0130-after-intent-unresolved remains unresolved. Current public regression proves second poll does not submit or increment again. |
| S13 | Acceptance differs from execution and acknowledgment | PASS: native records retain queue identity and execution/ack not_observed; actual native transcripts independently prove completed turns. release-counter-record/native correlate exact nonce and prompt hash. |
| S14 | Legacy state remains readable during migration/rollback | PASS: 0132-installed-rollback old0.8 holds native4 byte-identically; restored reader submits once. 0132-installed-explicit-legacy and unchanged reader contracts retain schemas1/2/3. Frozen installed comprehensive and hosted compatibility gates cover retained contracts. |
| S15 | Retire only qualified redundant paths | PASS: 0132-path-inventory and ticket pre-code contract restrict retirement to implicit basic tmux capture. Advanced signals, tracked mailboxes and network-time compatibility remain; no native parity claim for them. |

## Every child acceptance criterion

| Ticket / criterion | Verdict | Inspected source or raw behavior proof |
| --- | --- | --- |
| 0128.1 Exact idle thread, unattended installed submission | PASS | release-counter-record/native and normal supervisor deployment; earlier 0128-native-records/journal. |
| 0128.2 Acceptance identity distinct from execution/ack | PASS | release-counter-record has accepted queue and not_observed; exact native completed turn separately. |
| 0128.3 Busy/unavailable holds; no implicit mailbox on direct failure | PASS | 0128-unavailable-held/expired,0130-busy-held/expired; native-direct-failure confirms real native error and unchanged Wake/default mailbox bytes. |
| 0128.4 Explicit transport, no uncertain fallback | PASS | native CLI target and dispatcher; current uncertain acceptance public regression,0130 unresolved record; legacy compatibility is explicitly selected. |
| 0129.1 Explicit new/resume, directory and exact returned identities | PASS | release-open/reuse,0129-new-and-idle-close/resumed-identity. |
| 0129.2 Reuse/explicit extra, no implicit worktree | PASS | 0129-lifecycle-first/explicit-extra-force-close; unchanged lifecycle source invokes native/tmux, not Git. |
| 0129.3 Active/pending guards, force preservation/report | PASS | release-busy-close-final/close-cancel,0129-explicit-extra-force-close/force-preserved-authorities. |
| 0129.4 Real lifecycle and identity mismatch | PASS | normal installed receipts plus0129-identity-mismatch refusal code6 with original pane preserved. |
| 0130.1 Interrupted before intent and after acceptance before record | PASS | 0130-before-submission-restarted and after-acceptance-reconciled; exact native evidence retained. |
| 0130.2 No blind replay; unresolved remains visible | PASS | 0130-after-intent-unresolved; private same-root control remains retained/unregistered; current regression counts one intent after repeated poll. |
| 0130.3 Busy/detached/restarted-client qualified separately | PASS | Separate0130-busy/expiry,detached/headless-resume and client-restart receipts; retained failed availability assumption is not erased. |
| 0130.4 Actual disposable scheduler-process restart | PASS | 0130-before-submission-restarted and auto-reconcile-result include actual systemd scheduler outcomes. No shared-daemon/host restart claimed. |
| 0131.1 Entire installed agent lifecycle unassisted | PASS | release-final-native-A/B,arm-record,pane,open/reuse,close-cancel. Actual result42, initial A ended before wake turn; controller did not relay result or poll scheduler. |
| 0131.2 Tab/transcript/record agree on exact identity | PASS | Exact A/B UUIDs, nonce, queue/turn IDs and visible response in retained receipts; corrected prefix modules match qualified interfaces. |
| 0131.3 Guard/cancel/close, expiry and resume | PASS | normal close-cancel and busy-close-final; separate0130 expiry/headless controls remain valid under unchanged transport policy. |
| 0131.4 Installed/source identity, limits and two review axes | PASS | release-qualified-source-wheel/validation,release-repair-review and child review artifacts; honest opt-in/manual exclusions. |
| 0132.1 Inventory before retirement | PASS | 0132-path-inventory and pre-implementation contract retained in ticket. |
| 0132.2 Existing state/recovery/rollback | PASS | 0132-installed-rollback,uncertain-migration,same-root-recovery; raw original backups, nonce and payload hash preserved. |
| 0132.3 Only qualified retirement, no silent fallback | PASS | Public implicit legacy refusal and explicit selection; exact candidate migration rejects legacy transport; native uncertainty returns before external effect. |
| 0132.4 Publish migration/capability/boundary docs; no destructive cleanup | PASS | README, bundled/installed skills, native-workflow-migration and state contract published with source; protected state hash readback remains unchanged. |

## Implementation decisions, testing and execution contract

| Requirement | Verdict and proof |
| --- | --- |
| D1 Separate existing predicates, durable state and transport; no new broker/DB | PASS: unchanged daemon/injector/lifecycle interfaces and native transport integration; source/wheel manifest. |
| D2 Native direct messaging; qualify unattended interface separately | PASS: actual native MCP assignment and installed CLI queue submission; interactive prototype is not used as unattended proof. |
| D3 Accepted/submitted/uncertain/ack/terminal truthful; schema before coding | PASS: records and raw receipts distinguish these; ticket0132 records pre-code schema4 contract. Counter means durable intent, not execution. |
| D4 Resolve exact destination; revalidate attachment before close | PASS: unchanged session_lifecycle source and live mismatch refusal. |
| D5 Explicit new/resume/extra/force/legacy/resume-missing | PASS: public CLI commands and dedicated installed receipts; none inferred from recent conversation/tab. |
| D6 Busy/unavailable holds, unknown is not permission | PASS: distinct pending/expiry outcomes; malformed counters held byte-identically in due public scheduler checks; ordinary close refuses active/unknown. |
| D7 No exactly-once claim or blind replay | PASS: explicit unresolved records, bounded native evidence reconciliation and retained failures; documentation says the same. |
| Testing: public CLI/installed scheduler primary seam | PASS: installed comprehensive983 tests and smoke support real normal supervisor/transcript/pane proof. |
| Testing: native delivery, durable outcome, visible synchronization together | PASS: full normal lifecycle; final repair proof separately binds new counter and reader advertisement. |
| Testing: reuse prior tests; disposable real clients | PASS: existing tests amended, owned identities/socket retained; final OS process cleanup checked. |
| Testing: externally visible failure outcomes | PASS: public malformed record holds, actual busy/expiry/close refusal and retained uncertainty; no helper-only acceptance. |
| Execution1: current source/worktree/version/policy/custody | PASS: release branch, exact commits/manifests, policy readbacks, original local policy and five dirty notes retained. |
| Execution2: smallest complete behavior on existing seams | PASS: real full installed lifecycle, no replacement product/broker. |
| Execution3: reproduce failures then repair, installed/live evidence | PASS: counter/advertisement red-green,983 installed tests and actual native repair execution; earlier failed live samples retained. |
| Execution4: durable exact identities/outcomes | PASS: normal installed receipts and exact nonce/hash/native turn correlation. |
| Execution5: every criterion recorded, failures preserved | PASS: all20 child criteria mapped above; first numeric result FAIL remains retained and fresh job succeeds without controller repair. |
| Execution6: uncertainty holds and inspects, no silent swap/fallback | PASS: same-root unresolved record remains preserved and unregistered; current source returns to reconciliation before intent. |
| Execution7: standards/spec review, coherent commit, truthful planning | PASS for source/review; final planning closeout remains contingent on release/integration below. |
| Execution8: qualified retirement, no state deletion/unrelated disruption | PASS: raw migration/compatibility inventory; final deployment protects153 older module files and11 other units; archive preserves records/history. |

## Integration, publication and terminal custody

- Source integration PASS: PR227 canonical0a05c66; PR228 exact head
  1e6d5bcb87fdc1b74dcd5e4e0e60e7c824b90399 passes hosted Python3.11/3.12 and
  merges as a686c7b73034b149967b4ef19d0d7a58b2b61cc4. Merged-main run38025485695
  passes both jobs. release-publication.json records actual readbacks.
- Release PASS: public v0.9.0 tag resolves to a686c7b. Exactly two downloaded
  assets match the tested wheel and canonical sdist SHA256. Canonical rebuilt
  wheel archive timestamps differ, but all84 entries are content-identical;
  the exact installed-tested wheel bytes are published. See release-public-build
  and release-publication.json; no intended publication is used as proof.
- Active four user links, immutable prefix, normal supervisorPID56947 and
  reader schemas1–4: PASS, release-final-deployment.json.
- Rollback targets/old packages/registered roots/unrelated units preserved: PASS.
- Owned visible clients/server terminal PASS: final-runtime-readback.json checks
  exact process generations and actual tmux server absence. All four registered
  roots have pending/firing0; uncertainty/signal/mailbox controls and conversations
  remain retained. No fixture looping worker remains.
- Capability scope: selected Codex Wake root reports supervisor56947/schemas1–4
  and has actual delivery proof. Other retained project workers can also write
  their own legacy health advertisement (SoyLei49232/schemas1–2); the activation
  snapshot is not a claim of exclusive ownership or all-project native rollout.
- Parent/P65 closure is warranted by the completed requirements above; publish
  its final documentation projection and verify that integration. P63's separate
  retained recovery obligations remain unchanged.
