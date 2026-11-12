# Missing release executable blocks native wakes

Local ticket/authority: Plan0226. User requested diagnosing-bugs for the missed
Sentinel review8. This is source repair and read-only diagnosis, not installation,
review execution or live wake recovery. Primary/root dirty work preserved.

## Feedback loop and minimisation

The exact installed native adapter observes the existing wake's recipient and
asserts ready/busy, without submit/resume. Installed0.22.0.dev12, source55a2ee5.
Private repro-sentinel-wake-observation.py ran RED repeatedly in~0.1seconds:
`unavailable / runtime_observation_unavailable`. Private probe/runtime evidence
and recovery manifest stay outside Git; no raw prompt, contacts or secrets here.
Minimisation removed clock, TTL, prompt, startup and resume policy. Four required
fields remain: native transport, exact thread, endpoint and selected executable.
No live wake was changed to obtain a green result.

Before probes the ranked hypotheses were stale executable, stale endpoint, and
response-shape incompatibility. Tagged exception instrumentation isolated
SharedSourceError before any thread response. Frozen command selected Codex0.167.0,
which had been removed; current stable launcher selects0.167.2. Changing ONLY
command to the existing stable launcher yields correct busy state. Changing ONLY
endpoint to the freshly observed owned socket also yields busy, bypassing missing
CLI discovery. This is not evidence the generic unix:// endpoint itself is stale.
No schema-response failure occurred. Source path:
registration _request → resolve_codex_cmd dereferenced symlink → saved release
pathname → locate_shared_endpoint executes that pathname → missing file →
SharedSourceError → generic unavailable observation → background route held.

Plan0220's previous active-tab PATH fix is different: it intentionally used the
recorded executable consistently. This defect is loss of durable launcher identity
when registration dereferences an operator-selected alias to a disposable release.
MCP harness-native delegates to native CLI with default codex lookup, so the PATH
registration regression covers that selection boundary too.

## Correct-seam regression and source repair

The regression uses real _request registration, JSON persistence, launcher symlink
rotation, deletion of the old build, owned Unix socket locator/subprocess and actual
CodexRuntimeAdapter. Only final protocol reader response is synthetic. Before fix:
rotation case RED; explicit-pin control GREEN. After fix: all3cases GREEN, including
PATH-selected alias, stable fingerprint across rotation, unchanged default canonical
resolution, and no guessed fallback for a deleted explicit pin.

resolve_codex_cmd has opt-in preserve_launcher; only native intent registration
opts in. The selected absolute launcher pathname persists, while default callers
still resolve canonical executable pins. No schema, permissions, account fallback,
queue, deadline, busy, acknowledgment or provider behavior changes. Existing immutable
records are NOT automatically rewritten. Explicit release paths remain literal pins.

97focused tests passed:75native (includes3new),14app-server,8wake-policy. Intent19
is a native-suite subset, not added again. Native suite emitted connection-close
fixture diagnostics while passing. Policy wiring/compile/whitespace checks pass.
A local same-version wheel is an unreleased content-hash candidate only; it was
installed to disposable target, not the working prefix. Wheel3regressions pass and
both changed runtime modules match source byte-for-byte. Exact wheel/module hashes
retained privately in candidate-proof.json. No hosted Actions or daemon build.

## Live boundary and proposed recovery

Original installed probe is STILL RED: its protected old target is unchanged.
Source candidate with a COPIED target using stable launcher is busy/observable.
Do not claim full original symptom fixed live. Seven remaining reviews8–14 have
missing old executable, zero attempts and no native delivery recorded. Private
wake-launcher-recovery-proposal.json enumerates original IDs/due/TTL/fingerprints.

After separate operator approval and working CLI qualification: reconcile exact
absence of acceptance, cancel old zero-attempt intents through supported control,
and register attributable successors at ORIGINAL due/TTL using stable launcher.
No raw in-place fingerprint edits, silent fallback, duplicate reviews, duration
extension or campaign policy change. Existing keys are immutable requests: do not
reuse a key with changed target and pretend idempotency proves the repair.
The overdue morning review may run only through that approved original-window
recovery. Six future reviews retain their existing fixed scheduling windows.

Production native daemon/package was not upgraded; no wake cancelled, recreated,
resubmitted or changed. Debug instrumentation remains only in a marked private
wake-launcher-diagnosis directory; none in production source/tests. Source fix is
ready for review, but live repair/installation and original acceptance remain open.

Final local candidate wheel SHA256
50e75833241d8fa80db78e8ccd28b49d0fd7d87a7599ad7bc9978cdd7dfccb97.
Both changed module hashes match source; private artifact retained by that hash.
Build used disposable Python3.12 venv/pip wheel because uv/build were unavailable;
no global dependency or installed package changed. This same-version candidate must
not overwrite any immutable installed release; an approved release needs its own
versioned package/qualification. Native daemon unchanged. Source docs/Git custody
can proceed independently; no installation approval is implied by a draft PR.
