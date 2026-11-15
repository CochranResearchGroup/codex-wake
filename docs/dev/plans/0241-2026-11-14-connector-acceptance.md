# 0241 — External connector acceptance

State BLOCKED on operator scope decision. Owner ecochran76. Spec #663 owns scope; tickets #664–672 own acceptance. Execution ledger: 0241-execution.json. Frozen base and review point: 882aae8007e71cc2641c66a742e340e6cf007310. Integration branch feat/connector-acceptance. Three substantive lanes maximum; root takes #664 and workers take one ticket each, with remaining unblocked tickets scheduled as capacity opens. Live resource ownership is tracked in private receipts; no disruptive action on operator sessions. Existing tests and native owners only; no fixture framework. All dependencies empty; live scheduling/resource serialization is not a blocking edge.

Finish by validating each integrated ticket, closing accepted child tickets while leaving parent #663 unchanged, then exactly one Standards/Spec review and one bounded TDD remediation pass. No broad review loop. Preserve unrelated root dirty files. Installed acceptance uses dev28 baseline; product fixes require local checks and separate-user package qualification before deployment of merged exact source. Hosted CI skipped under cost policy.

Cleanup trigger: ticket integrated and remote custody established; close worker checkouts promptly. Integration checkout retained until review and final validated handoff. Memory disposition forbidden: no explicit memory write request.


## Current checkpoint

Eight child tickets closed from actual deployed acceptance: #664, #665, #666, #667, #669, #670, #671, #672. #668 remains open; no visible due restoration proof is claimed. The proposed restrictive policy is reviewable in docs/dev/evidence/0241-visible-wake-668.md. It would activate the common resolver for the whole controller root, beyond disposable profile configuration. No such policy was activated.

Two real prerequisites were repaired through merged PR673 and PR675: one process census for all pane TTYs, and a bounded15-second full native wake observation budget. Installed prefix version0.22.0.dev30, exact wheel SHA256 c7d7279a6a57c0f66045eba8833adabb10eba35c1f3d50680dc6a792d5b420a3. Native Codex daemon PID2082/startticks2000 remained unchanged. Consolidated local presubmit64PASS36.168s; policy wiring, compileall and diff checks pass. Source/UID qualification and live receipts retain their distinct roles. HostedCI skipped under costpolicy.

Exactly one broad Standards/Spec review and one bounded TDD remediation pass remain pending, following the operator's requested order after tickets close. Neither pass has run. Root must not silently count targeted prerequisite checks as that review or mark the parent issue closed.

## Resume

1. Recover exact remote feat/connector-acceptance tip and 0241-execution.json. Preserve unrelated dirty primary checkout; recreate the owned integration checkout only if needed.
2. Read the operator's scope decision before touching common-policy adoption. Root-wide adoption is not isolated to one profile; use the reviewed restrictive proposal only under that authority. Worker connector_visible_wake retains #668 ownership and remote checkpoint test/connector-visible-wake d7b1be68; its prior setup failures are not acceptance.
3. If authorized, qualify actual visible restoration of the same conversation/harness/cwd and cleanup before closing #668. Provision a monitor only after checking root pending work and current owner; the task monitor has exited and its process absence is verified. Existing submitted native delivery records are retained accepted proof, not permission to replay or fabricate agent acknowledgments.
4. Then freeze exact tip, review once against base882aae8007e71cc2641c66a742e340e6cf007310 along separate Standards/Spec axes, adjudicate findings and execute one bounded TDD remediation pass. Verify accepted blockers and update issue/PR evidence truthfully.

Private user-scoped receipts are under connector-acceptance-spec and ticket-specific Codex Wake state directories; never copy tokens, credentials or raw private histories into Git. Memory disposition forbidden: no explicit memory write request.
