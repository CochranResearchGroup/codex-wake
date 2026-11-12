# Native wake launcher continuity (local ticket P0226)

State: READY — source validated; review/installation/recovery not applied
Owner: primary agent; priority high; dependencies none for source-only repair.
User request: diagnose morning Sentinel wake8 fa84b127 delivery failure with the
diagnosing-bugs skill. This artifact is the repo-local ticket because external
tracker publication was not requested. Origin/main base ee03db70; lane
fix/native-wake-launcher-continuity. One isolated checkout, primary dirty work and
all other lanes preserved. Retire after source custody/approval boundary settled;
review within24hours. No delegated workers requested.

## Outcome and scope

Preserve the operator-selected stable executable pathname when registering native
intents instead of freezing the symlink's disposable release target. Literal build
paths remain literal pins; no account/PATH fallback for existing missing pins.
General executable resolution for lifecycle/build/other callers remains unchanged.
Source-only prevention plus exact private diagnosis/recovery proposal. No working
installation, live dispatch, wake edits/cancellation/replay, daemon upgrade, deadline
extension or campaign policy change authorized by diagnosis.

## Acceptance / definition of done

- Real native registration→JSON persistence→native runtime observation regression
  goes RED after launcher rotation/removal, then GREEN after source repair.
- Explicit deleted build pin remains unavailable; no guessed replacement.
- Existing executable resolver callers retain canonical behavior.
- Focused registration/native/wake-policy tests and original installed read-only
  reproduction reported separately. Existing immutable stale targets remain held
  until separately approved recovery; never pretend a source change repaired them.
- Document confirmed cause, cleanup debug probes, prepare reviewed source custody
  and bounded recovery manifest preserving original due/expiry and zero-attempt state.

## Feedback loop / competing hypotheses

Installed0.22.0.dev12 read-only adapter observation from original wake target:
/tmp/repro-sentinel-wake-observation.py RED twice in0.1s, unavailable/
runtime_observation_unavailable. No submit/resume permitted. Minimized to required
native transport, exact thread, endpoint and executable; clock/TTL/prompt irrelevant.
Ranked before probes: stale executable, stale endpoint, response-shape mismatch.
Probe captured SharedSourceError; old0.167.0 path absent, current launcher0.167.2.
Changing ONLY command or ONLY endpoint yields correct busy state. Native discovery
executes recorded command to find socket; removed command prevents that discovery.
Related Plan0220 fixed service PATH for active_tab; different issue, no takeover.

## Validation checkpoint

New regression test_native_launcher_continuity: stable-launcher rotation RED;
explicit literal-pin control GREEN. Uses real registration, serialization,
locator subprocess/owned Unix socket and runtime adapter. Only final protocol
reader is synthetic; no live message or production data. Phase1 live target remains
read-only and unchanged. Source repair next; qualify before proposing installation.

## Source validation

97focused tests pass; built isolated wheel passes3regressions and source byte
checks. See docs/dev/notes/0226-native-launcher-continuity-diagnosis.md. Original
installed stale intent remains RED intentionally, pending separate live authority.
Seven exact zero-attempt records enumerated privately; due/expiry preserved in
proposed recovery only. No queued review or working installation changed.
