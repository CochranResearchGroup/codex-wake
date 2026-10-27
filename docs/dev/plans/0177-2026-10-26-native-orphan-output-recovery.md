# Native orphaned-output recovery / #364

State: OPEN — qualified private candidate; shared cutover pending
Owner: ecochran76 / primary
Wake integration branch: fix/native-orphan-output-364
Native source branch: fix/ar2-orphan-custom-output
Native source baseline: fbfe287f4d (modern0.164 native features retained)
Wake integration baseline:96f0f01
Authority: operator says continue diagnosing bugs after confirmed AR2 panic. Complete source fix/regression and qualify a private candidate; no shared native restart or live-history repair. Manual resource monitoring, no goal enrollment/reset.

Objective: a resumed completed custom tool call lacking its result must retain the original call, synthesize explicit aborted output and permit the new turn to complete in both debug and release builds. Never replay historical business commands or fabricate successful output.

Feedback loop: private installed-binary app-server replay from original AR2 history and minimized one-call history. Isolated Codex home, owned process, loopback-only provider, no external credentials. Custom orphan panics/no provider request/no terminal event; stock orphan synthesizes aborted and reaches deterministic fixture terminal event; paired custom call succeeds. Private source artifact /home/ecochran76/.local/state/codex-wake/repairs/ar2-missing-output/diagnosis.md. No private transcript content belongs in Git.

Acceptance:
- Normalization handles ordinary and inherited missing custom outputs without panic under debug assertions.
- Resumed-history integration observes explicit aborted output and terminal TurnComplete with no old tool replay.
- Focused source tests and actual private candidate replay qualify independently.
- Source commit, artifact hash, installed identity and activation are separately recorded; unchanged shared daemon is not called repaired.
- Original missing-output provenance remains a separate investigation. No unrelated normalization/control behavior change.

Execution: two build jobs, dedicated temporary cache ~/.cache/codex-wake-ar2-repair, incremental compilation disabled. Previously cleaned53GiB cache remains untouched. Native AGENTS requires just test; full workspace suite needs separate approval and is not required for this bounded focused diagnosis. No broad workspace test or provider experiment admitted. Retain red/green logs, use one serial Standards/Spec review of frozen patch, then preserve candidate evidence. Build/cache and memory checked between expensive units.

Current state: native source fix is committed as b706004728800f4cba08e5554b854f1bd5461f25 (baselinefbfe287f4d). Qualified red/green: ordinary debug normalization red then green;95context-manager tests pass; persisted-history resumed-turn integration passes. Canonical private package built and both minimal/original-history offline replays pass with recovered aborted output and deterministic terminal event. See docs/dev/evidence/issue0364/acceptance.md and candidate.json for commands, setup corrections, hashes and exact remaining boundaries.

Private candidate CLI SHA2560696309a7cf4f140287901079a15117553701b5813a2f820282e21fde509776c; package native/ar2-orphan-b706004728, NOT selected by the shared daemon. Existing feature helpers match the installed runtime and are unchanged. Temporary8.18GiB build cache cleaned after qualification; candidate hashes verified afterward.

Primary Standards/Spec review complete with no remaining blocking source finding. Shared runtime application remains the exact approval boundary: prior operator instruction excludes shared native restart. No activation, live-history edit, goal/allowance mutation or business/provider work was performed. Issue364 remains open. Handoff issue365/plan0178 is independently merged, installed and complete; no dependency between acceptance boundaries.
