# Spec274 / tickets275–278 acceptance audit

Scope: validated implementation branch, not merge/release/deployment. Frozen native
source beeacfa; final durability remediation4ce6ae5 changes the shared persistence
protocol only. Review compares0a5c8d1...1b0848a; exactlyone broadpass, one remediation.

| Explicit requirement | Authoritative evidence | Qualification |
| --- | --- | --- |
| 275.1 explicit controls and pre-effect ledger reservation | refusal-public.log; native-probe/public-containment-stop.json; full-beeacfa-isolated.log; tests/test_strict_execution.py | Strict opt-in, legacy behavior retained |
| 275.2 dedicated executor and durable actor/native/unit/cgroup identity | native-probe/public-containment-stop.json; native-probe/native-successor-handoff-public.json | Exact invocation/process generation |
| 275.3 real executor/tool/build/test/child and effective kernel limits | native-probe/public-containment-stop.json; native-probe/native-token-exhaustion.json | Native execution, separate injected host cases |
| 275.4 unsupported/missing/shared admission refusal and exclusions | refusal-public.log; docs/agents/strict-objectives.md | Same-user IPC/provider/shared services excluded explicitly |
| 275.5 exact stop/empty and sentinel preservation | native-probe/native-successor-sentinel.json; native-probe/native-successor-cleanup.json | Sentinel verified after objective stop, separately cleaned |
| 276.1 original independent deadline | native-probe/native-deadline.json; native-probe/native-deadline-external-live.json | RPC unavailable during real blocked work |
| 276.2 blocked tool/TERM-resistant child | native-probe/native-deadline.json | Empty3.425s before originaldeadline; exact final descendant signal not isolated |
| 276.3 restart/suspend semantics/refusal | deadline-continuity-integrated.log; docs/agents/strict-objectives.md | Executable restart and changedboot; BOOTTIME jump injection/contract, no host suspend |
| 276.4 lost responses/exact identity | lost-launch-public-host.json; reconcile-focused-final.log | Actual systemd/publicCLI; replacement invocation tests |
| 276.5 timing/host limits disclosed | native-probe/native-deadline.json; docs/agents/strict-objectives.md | No universal real-time guarantee |
| 277.1 native cumulative/cached/preflight/failedwork sampled stop | native-probe/native-token-exhaustion.json; native-probe/native-lifecycle-partial.json; native-probe/native-successor-summary.json | Native cached-input totals, all attempts counted |
| 277.2 invalid/missing/stale/decreasing accounting | accounting-focused-corrected.log; guard-host-accounting.json; review-durability-green.log | Fixtures plus independent executable/OS tests |
| 277.3 actual observerdeath/transportloss | native-probe/native-observer-death.json; native-probe/native-deadline.json |22ms detection/1.351s empty observed; not universal bounds |
| 277.4 observation versus usage/latency/overshoot | docs/agents/strict-objectives.md; accounting-readback-green.log | Native publication delay explicitly unmeasured; configured poll cadence; maxovershoot unknown |
| 277.5 actualnative versus injected evidence and unrelated preservation | native-probe/native-token-exhaustion.json; native-probe/native-observer-death.json; native-probe/native-successor-sentinel.json | Failed startup/probe attempts retained |
| 278.1 aggregate actors/preflight/reviewers/successors/retries/failedwork | native-probe/native-lifecycle-partial.json; native-probe/native-successor-final-reconcile.json; accounting-focused-corrected.log | Concurrent600k reservation third denied; preflight included once; unknown actors fence |
| 278.2 refresh/handoff/restart accounting and deadlines | native-probe/native-successor-handoff-public.json; native-probe/native-successor-summary.json; deadline-continuity-integrated.log | Source45910 +successor145652=191562, aliasesoffset45910/55175; original deadlines retained |
| 278.3 failed checkpoint same allowance/artifact/deadline | native-probe/native-lifecycle-partial.json; native-probe/native-deadline.json | Actual failed atomic replacement; inheriteddeadline stopped failedpreflight generation |
| 278.4 exhaustion fence/explicit renewal history | native-probe/native-lifecycle-partial.json; native-probe/native-lifecycle-final-reconcile.json; final-usage-native-m.json | Known history settled before renewal; unknown final cost refuses renewal |
| 278.5 bounded publicnative full lifecycle and no unrelated termination | native-probe/native-successor-summary.json; native-probe/native-successor-preflight.json; native-probe/native-successor-sentinel.json | One actual command, goalcomplete. Local providerturn axis FAILED4vs3; extraDONE no command, fullycharged. This does not invalidate functional identity/accounting/deadline evidence |
| Required wholebranch review and remediation | review-adjudication.json; review-durability-red.log; review-durability-green.log | Spec0 findings; standardsS1 confirmed/fixed4ce6ae5; no broadreview restart |

Spec user stories1–6 map275;7–10 map276/277;11–14 map277/278;
15–17 map276/278;18–20 map278/275. Implementation decisions and testing
requirements are covered by the corresponding rows. Out-of-scope actions were
not performed. Shared services and unrelated user worktrees remain untouched.

Final source `4ce6ae5` passed 1,326 full-suite tests with one optional host skip
in 726.676 seconds. The final isolated installed-package selection passed all
69 tests, including actual systemd. Its 106 Python files match source; the wheel
hash is in `installed-final-parity.json`. The durability regression failed before
the fix and all closed-world checks now pass. Standards finding S1 is fixed; the
spec review had no substantiated finding. No accepted blocker remains.

Tracker issues remain OPEN and `origin/main` remains `0a5c8d1`. This completes
the approved implementation branch scope; merge, release and deployment remain
separate actions.
