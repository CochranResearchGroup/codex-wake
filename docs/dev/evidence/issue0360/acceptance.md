# Issue360: future scheduling repair

## Contract and diagnosis

Authority is the existing approved HF-13 specification, HF-01 decisions, HF-20 occurrence boundaries, issue360 and the operator's instruction to repair. No repeated interview or new recurrence authority. Wake durability, trigger due time, delivery TTL, owner completion and execution budgets remain separate.

Qualified live red: `python3 /tmp/t360-repro.py` reports original retainedID pending, due_at=null and monitor_ready=false; assertion fails. The first command used check_output on monitor's expected nonzero diagnostic status; corrected probe parses diagnostic JSON without suppressing its failure. Logs /tmp/t360-repro-{red,red-qualified}.log. No clock or state was fabricated.

Root wiring was missing. Initial qualified clock anchors were already present; long relative delays were accepted. Source TTL follows the due time, so there was no24h cap. Registration reporting hardcoded scheduling_time_unavailable and never projected original due time. Native reconcile only inspected submission uncertainty and skipped pending timer recovery. Agent controls lacked deliberate root/action scope.

## Source acceptance

Public API red/green logs use `PYTHONPATH=src:tests` and installed base runtime `/home/ecochran76/.local/share/codex-wake/releases/0.22.0.dev0-1a31564/bin/python`:

- `-m unittest test_harness_callers.HarnessCallerTests.test_future_wakes_expose_original_due_and_delivery_window_without_claiming_monitoring`: missing due at24h and3650d RED, original due/expiry and explicit unmonitored state GREEN. Logs /tmp/t360-future-{red,green}.log.
- `-m unittest test_harness_callers.HarnessCallerTests.test_future_wake_requires_loop_worker_and_keeps_identity_when_monitor_arrives`: one-shot worker incorrectly armed RED, loop-only readiness and original-ID dedup GREEN. Logs /tmp/t360-monitor-{red,green}.log.
- `-m unittest test_native_intent_recovery.NativeIntentRecoveryTests.test_reconcile_recovers_original_future_timer_without_submitting_or_rebasing`: pending did not advance RED, original timer firing without submission/attempt growth GREEN. Logs /tmp/t360-reconcile-{red,green}.log.
- `-m unittest test_wake_control_mcp.WakeControlMCPTests.test_agent_can_inspect_due_time_and_cancel_its_future_wake_with_host_scope`: inventory omitted due RED, real subprocess inventory/cancel GREEN. Logs /tmp/t360-controls-{red,green}.log.
- `-m unittest test_wake_policy.WakePolicyTests.test_owner_completion_actions_are_distinct_and_closed_tab_is_not_completion`: extended existing owner matrix caught held wake reported armed RED, distinct retire/hold/retain readback GREEN. Logs /tmp/t360-owner-{red,green}.log.
- `-m unittest test_wake_control_mcp.WakeControlMCPTests.test_verified_self_controls_do_not_need_per_thread_grants_or_reach_peer_wakes`: native self control absent RED; intermediate fixture omitted production's adopted permission provenance and returned no own wake; public PermissionStore fixture configured, GREEN. Logs /tmp/t360-self-controls-{red,green,green-final}.log. Missing native context, spoofed caller, peer cancellation, all-root selection and root-wide pause refuse; own all-cancel leaves peers pending.

Affected selection: `-m unittest test_native_intent_recovery test_harness_callers test_wake_policy test_wake_control_mcp test_wake_control`,60PASS15.337s. Earlier59-case run accidentally removed an existing datetime import; retained failure /tmp/t360-focused-full.log, restored and reran to59PASS, then final60PASS. Pinned Ruff F821/F822/F823, policy wiring and diff whitespace PASS. No missing test is represented as passing. Full CI is the separate integration gate.

## Live recovery

Original SoyLei intent wake_intent_27d748b766ab457ab8d3512276679d6d recovered in place through source public `native reconcile`, dispatch_attempted=false. Due2026-10-27T01:21:37.949431Z; delivery expiry2026-10-28T01:21:37.949431Z. Original scheduling_intent/key/origin, target, prompt, policy, ID and attempt count unchanged against operator-local private backup. No prompt/private review data is included here.

A second old retained intent initially made broad root activation ambiguous. Qualified read-only eligibility established its expiry2026-10-25T18:19:10.335137Z, long before current bounds. Full active inventory contained only these two known records. Scope question was resolved by evidence, not assumed consent. Registered native-lifecycle with the existing supervisor: fresh monitor_ready=true, source supervisor, mode loop. SoyLei pending/not_due/attempts0; unrelated intent failed/expiry_reached/attempts0. No unrelated work was revived.

## Remaining boundaries

Source installation is qualified; resident connection cutover is not. See the terminal reconciliation below. The selected-thread native reload primitive is unsupported. The existing explicitly approved shared-idle profile was used for one bounded refresh; no native restart occurred. A fresh stdio catalog cannot prove an existing connection reloaded.

HF-20 still owns recurrence authority and missed-run/overlap behavior. The existing daily prompt re-arms its next occurrence; that is not a native cron timer. This repair proves arbitrary future one-shot scheduling within representable dates and preserved lifetime policy, not a new recurrence engine. No business review, block mutation, external provider inference, original allocation renewal, or governor activation occurred.


## Terminal deployment reconciliation — 2026-10-26

PR361 merged source repair at02b68e8; PR362 merged install identity at e58d3a9701a34e39f7d1ded2668a4f15a1cc18d4. Both full CI matrices passed1728tests/1skip on Python3.11/3.12 (runs40265950701 and40267418377). Installed prefix0.22.0.dev1-e58d3a9 reports0.22.0.dev1. Installed product smoke and fresh stdio qualification passed; the stdio test used a host-supplied native-context fixture and is explicitly not resident connection proof.

The exact existing refresh `issue360-shared-mcp-upgrade-dev1`, fingerprint466f111a2176c2dd10f0769838abb8831c5342ece500641c30e292671ebd4c55, terminated **expired / expiry_reached**, with reload_attempted=false and reload_acknowledged=false. Its fixed expiry was2026-10-26T04:45:08.100111Z. Last retained idle observation had139loaded conversations and1busy conversation, plus a TimeoutError observation. These are last observations, not proof of which condition persisted for the entire wait. The terminal observer reported no resource or goal-continuity proof. No duplicate reload, replacement refresh, approval extension or resource renewal was issued.

Fresh read-only native `mcpServerStatus/list` on the actual source thread still reports codex-wake **0.21.2**, connected. Actual model-facing `wake_list` with the native caller UUID returns **policy_denied**. Therefore refreshed resident0.22.0.dev1 and caller-scoped controls are **not qualified**, and #360 / plan0176 remain OPEN. The source/installed version must not be substituted for the resident catalog version. No cancellation canary was created through the stale connection.

Fresh lifecycle monitor check reports monitor_ready=true, supervisor source, persistent loop, recent health. The original SoyLei intent remains pending/not_due with due2026-10-27T01:21:37.949431Z and expiry2026-10-28T01:21:37.949431Z. Compared against the private pre-repair backup, ID, full scheduling_intent (including key/origin), target, prompt, wake_policy and attempts remain identical; attempts0 and no native_delivery. It was neither cancelled nor resubmitted. Expired LitScout remains failed/expiry_reached, attempts0.

The terminal-file callback itself submitted once with native submission2abad520-ea6c-4554-bd30-077f9829ae83 and resumed this exact conversation. This establishes this callback's observed delivery, not business-review execution or a refreshed MCP catalog. The durable callback record still labels execution/acknowledgment not_observed; current-turn observation is a separate evidence boundary.

Native daemon PID2692768 and executable remain unchanged. The existing source-thread goal is still blocked (tokensUsed44278, timeUsedSeconds151); it was not resumed or renewed. Because refresh expired before continuity snapshots/resource verification, all-goal continuity across a successful reload remains unqualified. Goal-limits service remains masked/inactive. Manual resource readback showed18560MiB available and swap full; no unrelated process was stopped. The repair's terminal observer was disabled/stopped after reconciliation; durable receipts remain operator-local.

Qualified deployment outcome: source and installed commands upgraded, original timer recovered and independently monitored. Unresolved outcome: existing native connection still old, actual scoped controls denied, full resident/goal-continuity acceptance incomplete. Best next slice is to supply a supported native connection refresh under explicit current authority; do not retry this expired intent or renew its allowance automatically. HF-20 recurrence and its missed-run/overlap decisions remain separate and unresolved. No business review, external provider experiment, block mutation, shared native restart, governor activation or old-goal renewal was performed by this continuation.

Memory disposition: forbidden — no persistent memory update requested.
