# Controller393: one review and one TDD remediation pass

All 20 implementation tickets and parent #393 are closed from qualified source/disposable evidence. [Wake draft PR419](https://github.com/CochranResearchGroup/codex-wake/pull/419) and [Bots draft PR239](https://github.com/ecochran76/grok-bots/pull/239) publish the source; main integration and production activation remain separate. Python 3.11/3.12 each passed 1,909 tests with one skip on `8e2bacd`.

Review fixed point: `9538354ce2d8ec9f097664946ea4847079fba9c3`. Frozen Wake snapshot: `415607bd6eda7a0bbff0161eec4917988ed02c91`. Supporting Bots diff: `864a93967..0614856ec340da6d2d84f1b5cb5104fd26528403`. Independent reviewers examined Standards and Spec once. Primary adjudication is recorded in `docs/dev/evidence/plan0190/review393-adjudication.json`.

## Standards

Two candidates accepted as blocking based on concrete operational evidence. Expected SQLite failures could repeatedly leave a fresh running scheduler heartbeat; the fix publishes held/scheduler_owner_unavailable, with a real corrupt-store regression. Linux duplicated the portable OAuth transport and accepted oversized responses without its bound; both CLI entrypoints now share the bounded transport, private-token checks and explicit response_limit failures. The duplication classification was a judgement, not an automatic hard standards violation.

## Spec

Four candidates accepted as blocking. Controller build launches now apply the same effective scoped configuration as compatibility launches, with explicit caller overrides still last and native homes unchanged. Existing flows retain their original private function registry snapshot, so adding a future version does not invalidate them. Durable flow elapsed anchors prevent clock rollback from extending original budgets. Qualified counters continue during visible wall-clock uncertainty; boot/counter loss holds work. Foreach nodes accept independent cumulative child limits which tighten parents, preserve reservations across handoff/retry and cancel only the expired item’s owned work before joining. Uncertain cleanup observes original handles; peers survive and prompts are not replayed. Exact native enforcement remains unqualified; estimates require explicit opt-in.

## Validation and authority

Public-seam red/green logs remain in the private controller393-resumed/review-one artifact directory. Before remediation, comprehensive local Python3.11 and3.12 checks each passed 1,896 tests with one skip. Post-remediation installed acceptance passed all five Grok interfaces and 15 flow programs and all seven aggregate flow programs. Final comprehensive local Python 3.11/3.12 checks on `8e2bacd` each passed 1,909 tests with one skip. The final wheel build, installed source/session/MCP smokes, Ruff, compilation and policy wiring passed. Final evidence: docs/dev/evidence/plan0190/review393-final-validation.json. The prior efc5fa1 matrix passed 1,907 tests with one skip on Python 3.11; Python 3.12 exposed an existing startup-timeout fixture assumption. A deterministic delayed-start repro now verifies preserved uncertainty and zero-or-one observed calls, using append-only fixture evidence; the correction changes no production timeout behavior and passes on both versions. Applicable local checks replace hosted CI under the operator's cost policy; no hosted capacity or billing changes are requested. The unchanged Bots candidate separately passed 805 Node tests with 235 opt-in skips.

Qualification distinguishes source, installed synthetic effects, actual native metadata/loop evidence and production. Native Windows execution owners remain unsupported; Windows callers and WSL-authorized psmux presentation were separately qualified. Grok native stdio initialization is actual, while prompt/flow effects remain synthetic fixtures. Native Grok WebSocket serve, exact TUI health, exact turn cancellation, fork, exact metering and tool isolation retain explicit limits. Production380 and closed-tab/reboot recovery #368/#370 remain separate.

Review summary: Standards: two accepted (highest: misleading scheduler heartbeat); Spec: four accepted (highest: P1 configuration parity, immutable versions and clock continuity). One bounded TDD remediation pass; no second broad review.

The first post-review Grok fixture stopped at clock uncertainty before semantic dispatch. Its exact bad sample was not captured. A fresh exception-traced run passed without clock overrides, then a focused one-microsecond wall-regression reproduction justified the counter-qualified refinement. Original failure/diagnostic receipts remain retained; final uninstrumented installed acceptance passed. No claim attributes the first sample to a specific clock fault.

Memory disposition: queued in reviewed private codex_bots_main cloud for the qualified Bots integration only; queue acceptance is not persistence or retrieval proof. User-scoped receipt: controller393-resumed/closeout-memory.json.

Parallel semantic operands and explicit in-flight condition migration remain unsupported; supported foreach parallel/join behavior is qualified separately.

Cleanup: removed only this task’s 16 GiB native Rust target cache after confirming no compiler processes. The qualified native package and its CLI hash `5597f709…` remain intact; other caches/workspaces were preserved.
