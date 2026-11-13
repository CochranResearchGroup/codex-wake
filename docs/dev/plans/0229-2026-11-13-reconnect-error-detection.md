# P229 | Reconnect error detection and monitor deployment

State: CLOSED
Workflow: DONE; merged and deployed
Work item: https://github.com/CochranResearchGroup/codex-wake/issues/596
Owner: primary / ecochran76
Branch: fix/reconnect-error-detection
Base: 4b7da1f9dc2ad16e67f091f1cbc8d85468252407
WIP limit: one serialized lane; no subagents required

## Scope and acceptance

Detect the three operator-reported reconnect failures, including ANSI red output
above an editable draft. Exclude the composer suffix; retain message redaction.
Correct the heartbeat test's wall-clock assumption using monotonic waiting.
No schema, wake dispatch, native daemon, governor or existing terminal input changes.

## Execution

1. Preserve tested root edits in one isolated integration checkout; owner primary,
   purpose PR integration, cleanup after merged remote custody and deployment.
   Registered checkout count120 before/121 after; unrelated ownership unchanged.
2. Review Standards and Spec against the operator report and repo policies.
   Initial Spec finding: composer suppressed preceding errors; repaired and tested.
3. Validate local changed-surface tests and exact wheel; no hosted CI. Python3.12
   is the local environment; do not imply the hosted3.11/3.12matrix ran.
4. Publish/merge one PR under operator's explicit Okay go authorization.
5. Build/install immutable merged package with existing dependency versions;
   replace only the tab monitor owner with preserved settings. Verify tab16
   redacted error, monitor health and preserved pane processes/draft, retain rollback.
6. Close issue only after actual live readback; remove task checkout after clean
   merged remote custody. Root stays main; preserve unrelated sessions/services.

## Evidence and current state

Source/wheel evidence: docs/dev/evidence/reconnect-errors/qualification.json.
Prior baseline270tabtests PASS132.297s; final preintegrationwheel19PASS13.186s.
Heartbeat diagnostic traces show wall-clock backstep while six-second monotonic
publication succeeds; fixed test3PASS18.728s. Exact live tab16 source probepresent.
Installed working monitor and stable CLI are now dev14 from merged6150e5a5.
Native daemon unchanged; deployment evidence below supersedes prior qualification.

## Definition of done

Merged source, qualified immutable dev14 package, exact monitor restart readback,
redacted present on the retained tab, unchanged draft/pane identities, recorded
rollback, issue closure and task-worktree cleanup. A standalone package test does
not prove production replacement. Stable Time supplies UTC for time-critical work;
monotonic counters govern local bounded waits.

## Deployment closeout

PR597 merged6150e5a52036c9c611c229ae43fa988665f11fcc. Exact merged dev14
wheel73ef27e01c13de1fd48b18f10ae2ade9e5626653d11c4286c49cab3e87f68475
matches324source/installed members;31dependency versions preserved. Installed
traits/default-error/observer/publication23PASS14.276s. Native daemon build gate
not applicable: no native executable change or restart.

Replaced only monitor PID103657 with1587828; one current owner, no last error,
identical settings bytes, all9stable launchers verified. Actual tab16 errorpresent,
redacted; same pane and two Codex process birth identities. No terminal input sent.
Whole-screen byte-equality check failed because status durations update; subsequent
probe changed only that timer row. No pre/post draft-byte equality claimed.
Private rollback mapping and old immutable prefixes retained outside Git.

Stable Time supplied qualified_live NTS UTC readbacks. Local waits use monotonic
bounds. Primary Standards/Spec review has no remaining code finding. Initial test
failures and clock diagnostic remain retained. No hosted CI. This worktree was
reused for the docs/reconnect-monitor-closeout receipt and retires immediately
after its merged remote custody; primary remains main. No other checkout cleanup.
