# Acceptance freshness diagnosis and repair

Issue342, PR341. Baselinee6e2227; primary-owned WorkAcceptance public seam.
No provider/production effects; CI remains skipped. Existing30-second resource
fence is retained unchanged.

## Reproduction and minimization

Existing test loop10instances of
`test_work_acceptance.WorkAcceptanceTests.test_required_verifier_failure_rejects_work_and_infrastructure_error_is_unknown`
reproduced2owner_unqualified errors in7.100s. One-verifier20instances passed7.108s;
two-verifier10instances passed4.339s. Removing repeated evaluations reduced the
reproduction rate, so they remain load-bearing in the observed failing scenario.
A single10-case instrumented sweep passed6.785s; next bounded30-case numeric
boundary sweep reproduced3errors/15.343s. First failures and successful diagnostics
are retained separately; no clean claim is inferred from diagnostic retries.

Ranked hypotheses communicated before instrumentation: wall-clock backstep makes
observation future; elapsed observation exceeds30seconds; invalid identity shape.
Only boundary values were logged; original guard behavior was preserved.
At refusal, observed1792900349.2578254 versus now1792900348.4991457,
age-0.7586796283721924. Next refusals were-0.7136955261230469 and-0.6613361835479736.
All identity fields had expected shape. These values confirm future observation
from a backward wall-clock step, not30-second expiry. Default ResourceClaims clock
was verified identical to time.time. A100000 immediate-pair sample saw no backstep;
that passing sample does not invalidate the captured real refusal.

## Deterministic regression and fix

Use the existing host-owned WorkAcceptance(now=...) and ResourceClaims(now=...)
interfaces to pin the test observation and claim clock to100.0. The exact existing
verifier-classification test then deterministically reproduces3errors/0.378s,
because evaluation previously constructed ResourceClaims with the ambient clock
instead of forwarding its configured clock. This is the missing clock seam,
not a reason to accept future observations.

One-line source fix forwards WorkAcceptance.now into its resource guard. Default
production behavior continues to use time.time; neither permission nor freshness
policy changes. Tests inject one consistent clock for their observations, claims,
judgments and evaluation. Real process identity and real approved subprocesses
remain in use. A public evaluation regression also verifies clock99.0 and131.0
refuse an observation100.0 before any marker effect; clock100.0 admits that same
command. No sleeps, global time patch or extra replay is used.

Initial repaired WorkAcceptance+ResourceClaims selection18passes/3.781s.
Subsequent focused3.11/3.12 results include the explicit discontinuity regression
and offline-time mode tests. The final comprehensive result is owned by the join.

## Receipts and cleanup

Raw repro/instrumentation logs are retained in user-scoped validation receipts;
`[DEBUG-freshness-342]` instrumentation existed only in temporary diagnostic
scripts, never production source. Temporary scripts are removed after their
receipts are preserved. Repository glossary remains the terminology authority;
no new clock domain or scheduling semantics is introduced.

Final focused34tests pass3.12/4.408s and3.11/4.247s; installed isolated wheel's
10 acceptance tests pass5.172s outside repository. Joined comprehensive run at
17c1d4c passes1651tests/636.042s, OK(skipped1), exit0. Previous first failures remain
retained and the independent handoff component remains unproven/open in issue342.

Primary final reconciliation: comprehensive3.12 at16c2501 passes1651tests in
823.097s, OK(skipped1), exit0 under900s. All three targeted repairs now qualify;
issue342 closes. Earlier provisional open/pending statements are historical and
superseded. No production/provider effects or CI run. Primary memory disposition
is forbidden(no explicit memory-update request); lane-local non-write labels
above do not authorize a memory write.
