# P233 T8 live qualification progress — incomplete

The operator approved one bounded live packet: twelve Grok responses, two OpenAI
worker responses, sixteen local tool calls and fifteen minutes. Qualified start
was 2026-11-15T19:45:25Z; the original deadline remains 20:00:25Z. This is manual
monitoring, not independently enforced external supervision. No allowance reset.

Official Grok 1.0.77 device sign-in succeeded. The pinned official model listing
completed successfully and advertised grok-4.7 as default. Authentication presence
and catalog access do not qualify inference or coding capabilities. No tokens,
verification material, credential files or private working history are copied
into this receipt. Native package hashes were rechecked against all six files.

The first standalone native probe failed before inference because Wake rejected
the official native auth lock's 0644 mode. The credential file remains 0600.
The existing public CLI/private-bearer regression was extended with that actual
lock mode and failed before the fix. Wake now accepts other-user read permission
on the nonsecret synchronization file while retaining owner, regular-file,
no-symlink, inode and flock checks; other-user write permission still fails.
The lock is not chmodded or replaced. Focused auth checks: twelve PASS in 2.123s;
existing catalog check: one PASS in 3.326s; diff check PASS. A private, no-refresh
real native bearer read passed without exposing the value.

A second fresh native probe then failed with `inference request outcome unknown;
automatic replay withheld`. No assistant answer or local coding tool execution
was observed. The resulting tree is held, aggregate usage remains unknown, and
no replay or further paid work is authorized on that tree. Bootstrap auth-command
invocations are not response counts: twelve failed emissions in the first probe
are retained separately, and successful emissions in the second are also retained.
No OpenAI worker inference was dispatched. Current diagnostics suppress HTTP
status for generic failures; a bounded local diagnostic regression is in progress
before any decision about another provider request. Do not infer an HTTP status
or provider outcome from this generic message.

Native source/package remains at the prior qualified revision until that pending
diagnostic change is validated. The Wake auth fix changes runtime code, so the
previous wheel's auth acceptance must be rerun against a newly identified wheel;
unaffected UID1017 native package gates remain historical evidence, not proof of
a changed native package. T8 #639 and parent #628 remain OPEN. Seven children are
closed; broad review and post-review remediation counters remain zero. No working
profile installation, restart, deployment, provider logout or automatic login retry.

Private execution receipts are under the existing p233-t8 state directory;
raw synthetic histories and process/job identifiers remain workstation-local.

## Diagnostic source accepted; changed package pending

Native commit `df4a89bbd7df49691df280674130e3f5e8eedc7e` retains numeric HTTP
status for generic HTTP failures without provider bodies, headers, URLs or token
material. Unknown outcome and no automatic replay remain explicit. Local RED
compiled successfully and failed the missing-status assertion; GREEN passed all
four focused Grok client cases in 32.688s including compilation, 0.20s execution.
The exact patch reconstructs native tree
`bf1976b51b6f5a270696d4a9eb509eaad3463dce`; source hashes and private bundle digest
are retained in `runtime/grok-native-233/t8-source-manifest.json`.

The Wake auth fix was built from `a8a9e0c65cc7ab1c456ec787484b0467921eb8f1` into
wheel SHA256 `5d94731b6e5d00d8b69e41db12ca88f2b090996c1c546c4bc323922bf7d0ddc9`.
Installed under the existing isolated UID1017 prefix, all 336 module/resource
files match that exact wheel. Installed auth/catalog13 PASS7.253s and usage16
PASS1.057s. Initial installer invocation failed due to an inaccessible working
checkout; checks against the still-old installation correctly failed and are
retained. Corrected installation used the same declared environment, offline,
from an accessible directory with config discovery disabled. No working-profile
installation occurred.

The existing worker owns one causal complete-package rebuild and UID1017
runtime requalification using existing fixtures, preserving the prior immutable
package and rollback. No further provider request or replay is scheduled.
These local checks qualify the diagnostic change, not Grok inference readiness.

## Changed package requalified and verified by primary

The complete diagnostic package at native `df4a89bbd7` has entrypoint SHA256
`e69b170edb1ab87d7f398796746833bc43538bca34013c9420b6a92b0a0c8d6a` and content
digest `5443b8cf21ca6be7c6b613916b91f30bc8658e3d7b155934eaaacedeb4596c46`.
The original package and rollback remain preserved. Its immutable portable
inventory and job results are in `runtime/grok-native-233/t8-http-package-manifest.json`.

One serialized build passed in 1114.847s. Required UID1017 gates passed:
upgrade/history/multiclient/reconnect/rollback88.068s, failed-start repair and
rollback88.960s, saved-history22.856s, and private ownership/refusal10.102s.
Primary independently verified all six source-package hashes, 34 isolated-user
package/receipt file hashes, and all five terminal job results. A fresh OS
process readback matched the 13 protected persistent processes; no owned process
remained. Worker cache/artifact custody returned without repository edits.
The previously verified changed Wake wheel and its installed checks are reused.

This qualifies the changed package in the isolated environment, not live Grok
inference. The earlier manual live window expired at 20:00:25Z. No later provider
request, automatic replay, login, refresh or allowance reset was performed.
The next proposed gate is one new text-only diagnostic request using this exact
package, at most one Grok inference request, zero OpenAI responses, zero tool
calls and two minutes, subject to explicit operator authorization. It retains
prior unknown usage and the held tree; it does not resume or reset them. Auth
must validate without refresh before dispatch. Any renewed uncertainty holds.
T8 and parent remain OPEN, with broad review/remediation counters zero.

## One authorized text-only diagnostic: HTTP 426, held

The operator approved one fresh text-only request, capped at two minutes with
no tools or retries. All six exact package hashes and account-bound bearer
expiry were checked before dispatch, without refresh. The standalone fresh
session exited in 3.786s with HTTP426 and explicit unknown outcome/no replay.
No coding tool, worker or assistant completion was observed. Aggregate usage
remains unknown/null. The previous held histories are untouched; this result
neither resets their usage nor authorizes another request.

Official sampler source at revision
`2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8` sends
[`x-grok-client-version` for proxy version gating](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-grok-sampler/src/client.rs#L524).
The native adapter currently omits that header. This is a concrete request
contract gap and the leading explanation for HTTP426; a live correction has
not been demonstrated. A focused regression extends the existing request test
to require an explicit reviewed wire-compatibility version and a distinct
`codex-wake-native` client identifier. The adapter must not claim to execute
the official Grok CLI or inherit ambient OpenAI headers. Local RED is pending;
no production header change or additional live request has been made.

## Version header source accepted; package qualification pending

Native `b77a743f7e07edbc5e2f7c30d4e20a56ea4f3df8` adds an explicit reviewed
Grok Build wire-compatibility profile (`1.0.77`) and the distinct
`codex-wake-native` client identifier. Codex product version/User-Agent remains
unchanged, and ambient provider headers are still excluded. This profile matches
the pinned official auth client used in this qualification; it is not a claim
that Codex runs the official Grok CLI. Profile changes require renewed protocol,
package and real-account qualification.

The existing native request/continuation test failed before the fix because the
version header was absent (three other cases passed). With the fix, all four
focused client cases passed in 20.469s including compilation, 0.21s execution.
Exact source patch/tree/file hashes and bundle digest are retained in
`runtime/grok-native-233/t8-version-header-source-manifest.json`. This proves
local header construction, not the live HTTP426 hypothesis.

The existing worker owns one new complete-package build and required UID1017
qualification, with the prior packages and rollback preserved. No additional
live request, retry, login or refresh is authorized. T8 remains OPEN.

## Header-enabled complete package accepted; live gate remains pending

The complete package at native `b77a743f7e` is qualified under isolated UID1017.
Entrypoint SHA256 is
`fc9439b45efc5e1005911d54260b0bc47e0e7b4842ba8bfcecf07d15a0a65f74`;
content digest is
`cdd772c6ace5f248452530b1ad3454d0abb3c956eaa25da112b74e9340715174`.
Exact inventory and job/receipt hashes are retained in
`runtime/grok-native-233/t8-version-header-package-manifest.json`.

One complete build passed881.851s. UID1017 upgrade/history/multiclient/reconnect/
rollback passed107.393s; failed-start repair/rollback108.029s; saved-history20.362s;
private ownership/refusal8.257s. Primary independently verified all six source
and isolated package hashes, 28 additional installed-package/receipt hashes,
and all five terminal jobs with their receipt digests. A fresh OS census showed
the original13 protected persistent processes and no owned leftovers. Prior
packages and complete rollback remain preserved; worker writer leases returned.
The unchanged Wake runtime's installed336 hashes/auth13+usage16 acceptance is
reused, rather than repeated.

This acceptance does not establish live HTTP426 resolution. The one-request
live diagnostic authorization has been consumed, with its held session retained.
A concrete fresh text-only diagnostic is prepared against this exact package:
one Grok inference request, zero OpenAI requests, zero tools, 120seconds,
no retry and no refresh, after explicit operator approval and fresh account/expiry
and package-hash checks. No additional live request is scheduled or dispatched.
T8 #639 and parent #628 remain OPEN; broad review/remediation counters remain0.

## Header-enabled live diagnostic: stream reached; usage held

The operator approved one fresh text-only request against the qualified header
package. It exited in4.597s without HTTP426, reached a Grok stream reporting
`grok-4.7-build`, then held on inconsistent usage. No tools, retries or refresh
occurred. There is still no accepted completion or qualified aggregate usage;
unknown remains null, and the held session is not replayed. The one-request
approval is consumed. This is evidence that the request progressed beyond the
prior version-gating failure, not completed coding or account readiness.

The displayed OpenAI cyber/fallback warning is not independent Grok moderation
evidence: the current Core `maybe_warn_on_server_model_mismatch` constructs that
specific warning and `HighRiskCyberActivity` reason for every differing server
model label. The Grok adapter emits the observed model as `ServerModel`, reaching
that shared path. An existing public Grok worker test is being extended with an
observed model alias to reproduce the false classification. Existing OpenAI
moderation behavior must remain intact; real provider refusals remain held.

The inconsistent-usage error currently omits the numeric counts needed to assess
the provider accounting contract. A small existing API-stream test extension
requires numeric-only diagnostic evidence while still rejecting inconsistent
usage and omitting opaque provider data. No accounting rule is relaxed and no
missing counts are invented. The exact provider counts were not retained by the
current diagnostic; their relationship remains unknown. Local RED checks are
running before production changes, with no additional live request authorized.
