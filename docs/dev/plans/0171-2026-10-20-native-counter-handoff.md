# Reliable stable-time native counter handoff

State: OPEN
Owner: ecochran76
Work item: https://github.com/CochranResearchGroup/codex-wake/issues/302
Branch: fix/302-native-counter
Base: 242bdb73b3663f28bf2a8918966de40c86296d2d

## Current State

Bots Plan0031 reproduces five-second Windows counter subprocess timeouts despite
qualified stable-time responses. Need a minimal discriminating read-only probe,
then a regression and provider fix; preserve authenticated finite bounds and
native counter identity/age/rate checks. No guest UTC fallback or checkpoint reset.

## Execution

One serialized owner, no subagents. Compare subprocess boundaries before choosing
implementation. Expected surfaces: counter adapter, its public-interface tests,
release metadata and canonical plan/runbook. Qualification: focused tests,
read-only installed service loop, original isolated Bots idle/busy exchanges.
Publish through guarded PR; install only exact merged release under existing
operator authorization. Preserve all prior failures and unrelated sessions.
No production prompts, bus migration, grants, host clock or service changes.
Done when provider fix is installed and native acceptance passes, or exact
remaining boundary is recorded without an unsupported completion claim.

## Diagnosis and implementation

Inherited/closed stdin comparison24pass; open-pipe comparison12pass. Standalone
adapter20pass and four-caller32pass did not erase actual native failures. Native
instrumentation reproduces5s timeout before any counter output; tasklist also
times out. Alternate WSL relay routes both time out. Tiny direct Windows counter
executable and PowerShell each time out3times in paired45s probe. Persistent
counter/new-process paired probe: persistent220pass while new-process129pass/1
timeout over the same45s; final counts retained privately. This supports avoiding
repeated Windows launch, not a claim about Windows internals or host UTC repair.

New host_counter.read_counter returns only freshly correlated QPC/frequency via
private0700 directory/0600 socket, one serialized PowerShell producer. Same-user
bridge auto-starts from exact source/release, no setup/credentials or network
listener. Reject mismatched/late output, expire after60s idle, close stdin and
retire only its owned producer. Client acquisition remains bounded5s; producer
response bounded4s. Cold launch can still safely hold. Both stable_time and
native_clock preserve their existing signed-service evidence/age/rate guards;
no guest time, cached counter response or effect replay confers authority.

First regression red: missing host_counter module; basic fresh/independent reads
then green. Current focused4 bridge+6stable+5native checks pass. Permission test
initially inherited umask077 and failed to construct unsafe directory; explicit
chmod fixes fixture. Cold spawn exposed setsid unsupported by Python build;
POSIX setpgroup0 passes cold native read. Source idle+busy real web/native/Wake
checks2pass/0fail/0skip47.14s;12adapter reads network/max8.93ms. Retain all earlier
failed native receipts and diagnostic probes outside Git. Full regression and
exact-main installed qualification remain gates. No production mailbox migration,
clock/service change or runtime-controller restart.


## Regression environment correction

Initial comprehensive invocation used bare Python without declared MCP extras and
inherited the real stable-time client:1265tests,13failures/48errors/3skips207.51s.
Errors include missing jsonschema; native legacy fixtures observe real configured
network mode. Retain this run; it is not a clean regression result. Repeat with
installed dependency-complete interpreter and CI environment: empty explicit
stable-time configuration plus isolated XDG_CONFIG_HOME/XDG_STATE_HOME. Focused
15checks pass on that interpreter. Pinned Ruff undefined-name and policy wiring
checks are separate gates. No production source/state edited by these fixtures.
