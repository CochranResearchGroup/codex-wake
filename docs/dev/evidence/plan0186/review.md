# Review1: native upgrade recovery repairs

State: COMPLETE. One review and one bounded remediation pass; accepted findings resolved on candidateC.

Frozen native comparison: `git diff 6efee650fb0633a229adbd33bb826e3f85b899a3...HEAD`, HEAD `f8e5a5c24da256dda64853c8d6c36e3a8ef78a49`. Frozen Wake comparison: `git diff 3e65fdfd92acd273fb0e3183097a2066145a570b...HEAD`, HEAD `eb6e165e3cb0cef3e98308811aa0c0487e11a9a4`. Both bases resolve and diffs are nonempty. Commit lists and immutable diff packets are retained in user state `plan413/review1`.

Independent read-only reviewers: `/root/review413_standards` and `/root/review413_spec`. Parent#413 body was fetched again and matched its frozen SHA256. Primary verified every candidate against the frozen source and relevant policy. This is the one broad review, not two successive rounds.

## Standards

- **ST1 P2, blocking:** Plan0186 Current State/table still said running/unvalidated while its final readback said validated. Policy0002 requires unambiguous current planning authority. Accepted; reconcile current fields and label historical checkpoints.
- **ST2 P3, nonblocking_backlog:** `inventory_snapshot(home, _refresh)` ignores the advertised true/false mode. Accepted heuristic possible speculative generality/mysterious name; remove the unused mode within this bounded pass.
- **ST3 P3, nonblocking_backlog:** Immutable native goal binding is compared through repeated JSON key groups in authority declaration and resume validation. Accepted heuristic possible duplicated code/primitive obsession, not a current behavior defect. Concentrate the small immutable binding without changing persisted schema.

Standards sources included native contributing/README documentation and Wake policy0002/0005/0006/0014/0016/0021, domain/runtime proof guidance and GLOSSARY. No applicable CODING_STANDARDS file exists. Nested native AGENTS outside changed paths do not apply. Tooling-enforced style was excluded.

## Spec

- **SP1 P1, blocking:** TUI `thread_goal_set` always sends `recovery_authority: None`; only an explicit declaration establishes native-only policy, while missing policy correctly holds. The positive journey injects that declaration directly through RPC. Consequently ordinary newly created TUI goals cannot automatically recover. This violates eligible-work resumption through the existing user workflow without enrollment ceremony. Accepted after source verification. The28 API-driven journeys remain valid for their tested inputs; they do not prove this TUI creation path.

## One bounded remediation packet

Observe red on the actual TUI goal-creation/public managed-upgrade seam before implementation. Route original native policy through the trusted TUI user action; never infer authority from an absent declaration or model-written handoff. Preserve unknown legacy/external controls rather than silently upgrading their authority. Add only the focused compatibility regression required by this contract. Then perform selected component/protocol checks and critical exact-package regressions. Reconcile the documentation and the two small owning-module smells. No second broad review is authorized; any unresolved blocker remains explicit.

## Focused resolution evidence

SP1 resolved: real fresh TUI goal creation red on A, then green; unknown/external authority compatibility red on intermediateB, green on C. Final C30 managed journeys pass. ST1 resolved by consistent final Current State/table, with old evidence labeled historical. ST2 resolved by private advance_inventory without an unused mode. ST3 resolved by shared immutable goal binding preserving version1 format and equality semantics. Six C recovery tests and five admission tests pass. See final-c.json and qualification.md. This is focused verification within remediation1, not another broad review.

Accepted findings: Standards3 (highest P2); Spec1 (highest P1). All resolved.
