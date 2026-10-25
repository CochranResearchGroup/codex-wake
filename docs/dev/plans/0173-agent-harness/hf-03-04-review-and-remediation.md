# HF-03 / HF-04 single review and bounded remediation

State: CLOSED
Owner: ecochran76 / primary coordinator
Work items: #330, #331
Frozen base: 37a5cbb03e1c9e7db5026c99d6dca3cbf443ee5f
Frozen tip: 009238e
Diff: git diff 37a5cbb...009238e
Discovery passes: 1 of 1 consumed
Remediation passes: 1 of 1 consumed; S1 fixed

## Standards

Independent reviewer /root/frontier_standards found no actionable hard violation
or heuristic smell. Sources: AGENTS, glossary, discovery/runtime-proof guidance,
policies0003/0004/0005/0006/0014/0016/0021. No CODING_STANDARDS or CONTRIBUTING file
exists. Baseline smells were included; tooling-enforced nits excluded. Source
inspection only, no broad test rerun.

Accepted findings: 0; highest severity: none.

## Spec

Independent reviewer /root/frontier_spec returned S1 only. Primary independently
reproduced it through the actual read-only native metadata adapter, external
FakeConnection protocol fixture, current OS process and exact RuntimeIdentity.

S1: blocking, P2. agent_observation.py:131 defaults absent activeFlags to an empty
list, making partial status {type:active} fresh working. wait(working) returned
matched. Frozen HF03 requires complete exact-thread status and partial required
sources to project unknown. Require an explicit valid flag list for the active
variant, retaining idle/notLoaded union variants' existing no-flags shape.
No additional missing/unasked/wrong HF04 behavior was substantiated.

Accepted findings: 1; highest severity: P2.

## Bounded remediation

Add one omitted-active-flags case at the public runtime observer seam, observe red,
make the smallest classification correction, observe green, rerun the original
public wait reproducer and critical observation/resource/caller regressions.
Do not start another broad review or expand into baseline PR329. First comprehensive
run remains frozen at009238e; wait for its terminal receipt before changing source.
Installed wheel smoke will be rebuilt/repeated against the final source.

## Remediation receipt — outcome_progress

S1 regression added an omitted activeFlags case to the real runtime observer
protocol test. Red command:
`PYTHONPATH=src python -m unittest discover -s tests -p test_agent_observation.py`.
It failed with working != unknown. Minimal fix requires an explicit valid list
for active; idle/notLoaded retain their union-variant absence behavior. Same
command green:10tests onPython3.12 and3.11. Original reproducer now returns
timeout with stateunknown instead ofmatchedworking. No second broadreview.

Critical final selections:13resource and7publicharness tests passed on3.12;
3.11 had the same selections green immediately before the two-line statusfix.
Undefined-name, compileall, policywiring anddiffchecks pass. Rebuilt isolatedwheel
matches131Pythonmodules; actualCLI and52-toolstdioMCP ready/matched checks pass,
partialactivestatus cannotmatchworking, unattestedresourceclaim remainsdenied.
WheelSHA256:0bb0544cedc75cac1da0071329876bd138e239cc66453a5067fa989618cf8a57.

Frozen pre-remediation comprehensive3.12:1521tests,1failure,1opt-inskip,565.025s
(test runner;567.865s launcher). Failure is existing handoffpreflight scope_drift
subcase at exact_idle_owned_client_not_ready; no modified handoffmodule. Isolated
retry passes1method including its subcases. Retain the first failure as flaky
validation evidence, not a clean comprehensive pass. Baseline comparison is
recorded in the final ledger. No full-suite retry, quarantine or unrelated repair.

Accepted findings: Standards0(highest none);Spec1(highestP2), fixed.
Remaining accepted review blockers:0. Sourceacceptance and remote tracker closure
remain separate from main integration or production installation. CI skipped.
