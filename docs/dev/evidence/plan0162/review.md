# Plan0162 review

Frozen primary review:439f1e5 vs5b14c05. One independent reviewer
/root/tab_target_review; complete, no edits/effects, no nested agents.
Standards axis: no candidate findings. Spec axis: two accepted blocking findings.

- SPEC-01:P1, normalized numeric names lost exact-name precedence and could
  target a different index. Regression failed (`policies` vs`18`); moved normalized
  name match before numeric interpretation. Regression and resolver suite pass.
- SPEC-02:P2, a completed preparation stayed busy permanently after a transient
  busy read. Revalidate the original pinned identity on every completed retry;
  starting→resolved→busy→resolved regression passes without another effect.

Primary reconciliation also retained the first busy message target instead of
resolving its descriptor again on retry. Real mailbox regression verifies a
replacement receives no message. Lifecycle regression uncovered optional tmux
fields breaking pre-existing fixture observations: confined detailed shell
metadata to the new target workflow.92 lifecycle/target tests then passed.

Installed observations exposed saved thread/list omitting a newly materialized
empty conversation. Explicit resume IDs now use exact thread/read metadata and
canonical-CWD validation, then revalidate again before launch. No implicit fresh
fallback or transcript fabrication. Regression observed red before green.
SourceKinds include CLI, VS Code and app-server interactive origins (the native
controller's own new thread was recorded as VS Code). Metadata output remains
allowlisted and bounded. Own initial failed/partial receipts are preserved.

Disposition: both reviewer findings remediated. Runtime and integration claims
remain separate from source review. No second broad discovery/review pass.
