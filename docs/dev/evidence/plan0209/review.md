# Single review and bounded TDD remediation

One broad review compared20e396b5aa469ed814c123218cc356a68b229936...c63c5075ac4e3f78f29917256e718030fbba819a.
Independent reviewers: /root/review503_standards and /root/review503_spec.
Primary verified each candidate against the frozen source and spec503; no second
broad review was performed. One bounded TDD remediation pass addressed F1–F3.

## Standards

No confirmed blocking documented-standard violation. Two P3 judgment findings
are accepted as nonblocking backlog, not hard violations:

- S1, possible Feature Envy: tab_reattach_traits.py adds synchronization/probe
  budget state through owner.__dict__. Verified the mutable state is protected
  and bounded; no demonstrated correctness failure. A future explicit owner
  reservation interface would concentrate ownership (policy0014).
- S2, possible Divergent Change/ownership coupling: tab_recovery.py imports
  generic private storage/locking helpers from goal_supervision/tab_monitor.
  Monitor-specific lock diagnostics can surface in recovery. A neutral shared
  primitive is a later bounded refactor (policy0014); current lock semantics and
  recovery safety are qualified. No speculative refactor was added to this pass.

## Spec

All three accepted behavior findings are resolved:

- F1 / P1, story31: restored coding slots were always held when occupied by
  shells. Public realtmux red showed held for both marked and unmarked slots.
  Commit6d7701a now qualifies one local interactive shell at the captured
  placement, preserves its exact process and unsent input in a separate window,
  and restores the exact saved conversation to its intended name/index. Busy,
  pinned, linked, ambiguous or changed slots hold. No shell command is replayed,
  no existing process is killed and no input is sent. Pending effects retain
  the original intent. Installed native proof restores two distinct real git
  repositories, both original shell processes/drafts, physical ordering/undo
  and same-key replay with no duplicates or provider calls.
- F2 / P2, story15: a later explicit visible resolution did not clear an earlier
  error. Commit0e9d9f2 follows the latest explicit Error/Resolved marker; ordinary
  success text cannot clear an error and a newer error wins. Existing
  privacy/draft/redaction rules remain. Actualtmux red/green on3.11/3.12.
- F3 / P2, story26: same-image backend descendants could satisfy profile-create
  success. The needs-evidence candidate became a confirmed defect through a
  backend-only public red. Commitda00a8f requires the exact direct foreground
  client invocation plus pinned wrapper/process births and registered image/
  home. Independent native installed proof verifies the returned client role,
  repeat-safe creation and cleanup. Remote provider account identity remains
  explicitly unverified; no credentials or raw argv are emitted.

Red/green and final validation are recorded in remediation/validation.json and
review-f3-foreground-role.json. F1 red: /tmp/codex-wake-503-F1-red.log; F1 green:
/tmp/codex-wake-503-F1-green.log. F2 red/green paths retained in worker receipt;
F3 original failed backend-only and native preflight failure remain recorded.
The earlier distinct-repository recovery partial remains immutable in514; a
fresh explicitly trusted repository fixture now passes. The earlier partial's
cause is not retrospectively claimed fixed or diagnosed.

Final product94012f3:91 affected checks each3.11/3.12; final contract checks21
source3.11 and22 normally installed3.12; installed public CLI/API/nativeMCP/
OAuthMCP passes. Full2205tests/version belong to the frozen pre-remediation
bfded49 baseline and remain separately attributed. Exact native behavior6d7701a
transfers to94012f3 through280 unchanged Python members; only the data-only
capability/help statement differs. The final281 installed Python members match
the immutable wheel. Native Windows bridge/client/schema owners are unchanged;
actual Windows/PowerShell proofs retain their original qualification source.

Accepted findings: Standards2, highestP3 nonblocking backlog; Spec3, highestP1,
all resolved. Remaining blocking findings:0. Broad reviews1; TDD passes1.
