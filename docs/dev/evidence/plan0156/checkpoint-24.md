# Plan0156 checkpoint24 — native failure diagnosed and accounted

Plan0156 remains OPEN / IN_PROGRESS. This packet preserves a failed acceptance
attempt and fixes its instruction-output delivery; it does not establish product
acceptance. Branch feat/agent-lifecycle, tested candidate ff708d8, isolated
installed12. Parent deadline1791908966 and two-million campaign stop unchanged.

Native live-handoff04 same-tab+rollback failed preflight allowance: source48125,
receiver188386, known fixture236511; allowance150000 unchanged. Receiver helper
actually completed preflight successfully but admission was blocked on spending.
Read-only fresh native readback: source goal paused budget201875, counters0/0;
receiver goal null, turn completed, command results0. No goal activation,
continuation or rollback. Readback app-server exited0; fresh /proc census found
no owned app-server/tmux/resume processes. No provider assignments during diagnosis.
Curated receipt installed-handoff-04.json retains exact IDs, raw locator and limits.

Actual trace: first instructions call used inner exec_command limit20000 but
outer functions.exec default10000; result12654 tokens was explicitly truncated.
Receiver reran instructions and returned two slices before executing preflight.
That required four tool calls instead of two and exceeded the original allowance.
Runner AGENTS now specifies outer max_output_tokens20000 and direct text(result.output)
as well as inner limit20000. Source check compiles; existing runner supervision
checks PASS5/0.001s; git diff --check PASS. This is an evidence-driven prompt repair,
not a fabricated automated RED/GREEN or successful native retry.

Ledger includes eleven assignments, known lifetime826870, reset-window499975;
one old receiver remains unreported with provisional250000 reserve (not measured
or a hard bound). Root native counter at prior report621600/7268s; refresh before
next purchase. Do not rerun expired intents or increase caps to obtain a pass.

Fresh review candidates: SP-01 late source counters after activation do not reduce
receiver allowance; SP-02 checkpoint qualification omits promised restart-safe
fields. Both remain awaiting primary seam reproduction/adjudication and bounded
remediation. ST-01 duplicated allowance math is nonblocking heuristic, no confirmed
numerical defect; no separate refactor authorized by this packet. Broad review is
consumed; restrict follow-up review to these findings/remediation.

Next: public regression for SP-01 with source600→700 of1000 while successor retains400;
reconcile before/during activation. Then SP-02 complete checkpoint contract and update
writer/fixtures. Native proof in both modes, nonnull refresh goal/instruction proof,
required local CI, integration/release, installed rollback/cleanup, clean main and
issues248–251 closure all remain outstanding. Memory disposition unavailable:
no reviewed Codex Wake Graphiti target; retained prior non-write receipt.
