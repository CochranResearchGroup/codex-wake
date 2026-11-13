# Native wrapped-footer correction

Base: eac0d01ef60d4fd04807ba36a40b709d57a0b79d (merged PR600).
The deployed automatic binding code passed real native first contact. The recipient
had zero actor rows before contact and did not poll or bind. New sender admission,
automatic tmux binding, native submission, read, accepted claim and completion all
observed. On client replacement, binding PID/generation refreshed automatically.
A narrow idle native footer then blocked the second message as composer_protected.

## Reproducer and minimized evidence

The exact installed parser returned false for the idle owned diagnostic pane;
unsafe_pane_reason was null and placeholder exactly Ask Codex to do anything.
The title alone wrapped from Wake P230 onto recipient, making four nonempty rows
instead of three. Tail-only replay also failed: no transcript/body context needed.
Original side-effect-free parser verdict was false; metadata-aware candidate verdict
true, while the same replay without metadata remains false.

Ranked hypotheses: strict row-count rejection (confirmed by footer-only replay);
unrecognized prompt (refuted by exact placeholder); unsafe modal (refuted by null
classification). No composer was cleared or input overwritten.

## Correct seam and qualification

Regression test observed False-is-not-true before implementation, then passed.
Second test drives TmuxBinding.probe with fresh native metadata. Exact installed
candidate tests: test_a2a_tmux_delivery + test_a2a_delivery,25PASS/5.543s. Drafts,
unknown continuations and mismatched session identity remain refused. Both eligibility
and pre-submit composer checks receive fresh metadata. No generic relaxed row count.

Candidate0.22.0.dev17, wheel SHA256:
b8648f4f7181fe1d43724cece2ec32be1a72ed87ca3ee3430ecf5335605b8436.
324wheel payload files equal source. This focused delta follows dev16's163installed
checks and StableTime-backed smoke; no redundant full-suite or hosted run.

Closed-world source review accepts one Spec finding (wrapped footer), fixed under
exact metadata; Standards0. Original pending notice is deferred/provably unsent,
not an uncertain submission. Integrate this correction before activation; then
reconcile that notice without replay or a new intent key. No host clock change,
StableTime policy migration, draft clearing or safety-guard bypass authorized.
