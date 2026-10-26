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

Installed source/MCP control cutover and fresh/resident connection verification remain pending. Selected SoyLei thread is idle, but actual native `thread/mcpServer/reload` dry-run is unsupported; no shared fallback or native restart was attempted. A fresh stdio catalog cannot prove an existing connection reloaded.

HF-20 still owns recurrence authority and missed-run/overlap behavior. The existing daily prompt re-arms its next occurrence; that is not a native cron timer. This repair proves arbitrary future one-shot scheduling within representable dates and preserved lifetime policy, not a new recurrence engine. No business review, block mutation, external provider inference, original allocation renewal, or governor activation occurred.
