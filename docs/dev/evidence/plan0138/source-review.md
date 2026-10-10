# Plan0138 serial source review

Frozen implementation ef953cd0f5cbdf1384b232f362dbb39393d006ff; comparison
`git diff d9354a819f28893126845ea87eedb9956cdde5d5...ef953cd`.
Primary performed Standards then Spec; no independent evaluator is claimed.
Standards: repo policies0003,0005,0006,0014,0016 and Matt code-review smell baseline.
Spec: Plan0138 and approved explicit same-saved-recipient decision. GLOSSARY.md
supplies deadline and uncertainty vocabulary. No docs/agents/issue-tracker.md is
present; repo-native Plan0138 is the specification, not an invented issue.

## Standards

No accepted blocking standards findings. Native queue outcome formatting resembles
the existing scheduled-wake path, but sharing a larger transport abstraction is
not necessary for this bounded feature. External I/O is finite; raw output and
capability secrets are not retained. Tests use public mailbox/dispatcher interfaces,
isolated native-protocol peers and real queue subprocesses. Existing source seam
helpers represent external Codex/tmux I/O; no database side-channel is the acceptance
oracle. Private runtime material stays outside Git. Default envelope fingerprint
is unchanged; no new database schema or implicit enrollment.

## Spec

Accepted blockers from initial scan:

- P68-S1: notification_context checked original intent expiry but did not recheck
  current dispatcher and recipient lease generations. A released/replaced lease
  could remain eligible before the original intent lease deadline.
- P68-S2: malformed runtime status could raise AttributeError and stop the worker
  rather than hold the original message visibly.
- P68-S3: operator notification documentation described unconditional human
  reconnect, contradicting the approved per-message exception.

One consolidated remediation pass adds existing scheduler lease fences to each
effect context, rejects unqualified runtime status and documents opt-in behavior.
Red public regressions:19tests, one failure and one error for S1/S2. Green:19PASS
7.191s. S3 corrected against the CLI contract. No remaining accepted blockers in
this source unit. Installed request/reply, release parity and cleanup are still
required; source review does not certify them.

Additional red/green evidence: original dispatcher test0submitted→1submitted;
runtime observation error→visible hold; changed-identity reason generic→specific;
native reply bookkeeping crash left arm firing→submitted without resend.
Earlier focused91PASS28.619s; final affected-suite result will be recorded separately.
