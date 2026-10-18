# Control/accounting repair review

Fixed point: dbd37ca09f9a13f4ae54b98f8f8ea4b0888a86c5. Review of working diff,
not a committed integration result. Reviewer handle /root/control_repair_review.
One broad source review used; no new discovery loop is authorized by this note.

Standards: no candidate findings under the named repo policy and Matt smell
baseline. Spec: no candidate findings in the bounded control/accounting repair.
Primary adjudication: no accepted blockers on either reviewed axis. Reviewer
inspected source and supplied tests; no independent production acceptance claim.

Frozen contract: fresh input plus output default, cached input excluded; explicit
inclusive option; persisted basis/deadline/spend; qualified basis conversion keeps
prior evidence and does not clear stop latches. Campaign interruption captures
exact work turns; later operator messages remain usable. Qualification-loss grace
is persisted, max60seconds, capped by checkpoint reserve and original deadline.
Streaming accounting preserves all consumed attribution/lineage records and scan
bounds. Missing grant is no-effect and explicitly permits operator interaction.

Full issue289 provisioning/continuity remains incomplete and was not treated as
a newly discovered regression in this repair review. Installed isolated fixture
receipts are separate evidence. No native production or provider effects ran.


Closed-world native acceptance verification by the same reviewer handle found
no critical evidence regressions. Valid red2 and candidate share corrected fixture
hash,4requests within5cap. Candidate exact operator turn is active after watcher
heartbeat advancement, has no interrupt effect, then completes with expected
assistant output in native rollout lines36/39 bound to the same turn. Delegation
45fresh/90inclusive and absent exact owned PIDs verified from retained evidence.
This is verification of new acceptance evidence, not a second broad review.

## Host-delegated enrollment — closed-world criterion verification

The operator accepted host-delegated self-enrollment. Same reviewer verified
only the new accepted criteria and critical regressions introduced by this code.
Accepted findings: missing allocation-wide grace latch; old allocation charging
post-renewal work; retry finalizing a different boundary from the persisted target.
All reproduced at public enrollment/poll seams, then repaired and exact verified.
Final verification confirms persisted target reset_anchor equals selected renewal
anchor before old finalization; mismatch holds conservatively. No remaining
finding on the examined criteria. No second broad discovery pass performed.
Focused33tests PASS5.618s; exact source/native proof is native-public-final.json.
Full-suite red results and an intermittent unrelated disposition failure remain
disclosed in delegation-validation.json. No release gate waiver.

## Final0.18.0delta review —447359e...d88da16

Operator-approved frozen comparison:git diff447359e...d88da16; one commit,
d88da16 Prepare0.18.0rollout with preserved renewal boundaries. Closed-world
review scope: initial host renewal boundary import, v2legacy grant preservation,
wrong-allocation refusal, and introduced critical regressions. No second broad
discovery pass or unbounded hardening.

### Standards

Reviewer:/root/control_repair_review. No blocking/nonblocking candidates under
AGENTS, codex-stack/discovery guidance, policies0005/0006/0009/0013/0016/0021and
the full judgement-call smell baseline. Primary adjudication:0accepted findings.
Versioning/compatibility, public seam tests and delivery gates are preserved.

### Spec

Reviewer:/root/native_authority_capability. No missing/partial named requirement,
scope creep or introduced critical regression found. Source preserves imported
start/anchor, seeds boundary owner before successor admission, requalifies
history, rejects future/changed boundaries, retains exact legacy caller grants
and holds conflicting allocation selection. Native import is root-first10->30;
successor-first35and negative cases have explicit public-controller assertions.
Primary adjudication:0accepted findings.

Summary:Standards0accepted, highest severity none; Spec0accepted, highest
severity none. This is source review, not production acceptance proof.
