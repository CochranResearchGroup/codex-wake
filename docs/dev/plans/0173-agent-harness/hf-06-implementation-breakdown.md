# HF-06 implementation breakdown proposal

State: PUBLISHED; native dependencies read back
Owner: ecochran76
Parent: CW-HARNESS-173/HF-06
Spec: [common session permissions](hf-06-spec.md)

The operator approved these six slices, their test seams and blocking edges.
Published issues #320–#325 have verified native blocking relationships.
See [publication receipt](hf-06-publication-receipt.json). Keep the
existing HF-06 parent; do not create competing tickets for #315–318. Each slice
owns a complete observable path. Serialize shared CLI/MCP/profile/controller
writes even where the logical dependencies permit concurrent work.

| Slice | Blocked by | Observable delivery |
| --- | --- | --- |
| [HF-06-A](https://github.com/CochranResearchGroup/codex-wake/issues/320): Own-session policy and truthful refresh admission | HF-02/#315, HF-07/#316 | Configure global/profile/session action policy; inspect it and admit/refuse own refresh through CLI/MCP. No UUID enrollment loop. Distinguish permission from unsupported scoped refresh under #318; no broader effect. |
| [HF-06-B](https://github.com/CochranResearchGroup/codex-wake/issues/321): Automatic handoff and approval continuity | A; existing qualified lifecycle path | Configure a trigger, admit one handoff, verify successor reuses only applicable task approval with original allowance/expiry; original-session approval remains local. Unsupported lifecycle returns no effect. |
| [HF-06-C](https://github.com/CochranResearchGroup/codex-wake/issues/322): External enforcement permissions | A; existing qualified enforcement path | Allow enrollment, require approval for increase/disable and explicit observation-stop recovery, and show current permission/capability at the real enforcement caller. Preserve operator unenrollment and stop/accounting history. HF-24 owns new portable controls. |
| [HF-06-D](https://github.com/CochranResearchGroup/codex-wake/issues/323): Two-sided A2A permissions | A | Send and receive through the same policy; either side's deny prevents delivery/claim. Correlated reply/claim retains task scope and does not grant tool rights. |
| [HF-06-E](https://github.com/CochranResearchGroup/codex-wake/issues/324): Wake route permissions and safe fallback | A, HF-13/#317 | Register an ordered permitted route list, restart and dispatch only an allowed supported route. Permission change fences queued work; uncertain submission prevents fallback/duplicates. Missing route execution stays unsupported. |
| [HF-06-F](https://github.com/CochranResearchGroup/codex-wake/issues/325): Legacy convergence and cross-action acceptance | A–E | Reconcile legacy grants/denials and old intents with explicit adoption and diagnostics. Remove the refresh-only bridge only after all consumers pass shared policy/compatibility acceptance. |

Issue318 is a dependency for proving real scoped-refresh completion, not a hard
blocker for A's permission/capability diagnostics or unrelated action consumers.
If it needs an upstream change, retain the explicit unsupported result while
that separate work proceeds. B/C/E do not implement the missing HF-18/19/20/24
runtimes; readiness of those paths is separately reported.

Approved tests: public CLI/MCP requests plus independent effect-controller tests,
with disposable policy roots and injected verified runtime responses. Real
installed runtime/peer-connection qualification is a separate acceptance gate.

Published to the configured GitHub tracker with existing ready-for-agent and
enhancement labels; all 12 native blocking edges were read back. Labels describe
specification readiness, not cleared prerequisites or started implementation.


Issue319 separately gates proof of observation-fault recovery. C must classify
recovery authorization and refuse premature latch clearing; its general policy
work does not require waiting for that runtime repair. No recovery can reset
resource authority or be inferred from native goal resume.
