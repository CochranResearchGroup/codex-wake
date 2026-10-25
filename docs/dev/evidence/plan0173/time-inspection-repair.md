# Offline time inspection diagnosis and repair

Scope: PR341 full-suite failure diagnosis, focused local tests only; no CI,
provider, network, installed-state mutation or runtime source changes.

## Red and minimized reproducer

At source checkpoint `e6e2227c63f3b7cc22a6a921db686b5a1e78ba9c`, run:

```sh
PYTHONPATH=src:tests /home/ecochran76/workspace.local/codex-wake-harness-frontier/.venv/bin/python -m unittest test_time_inspection.InspectionTests.test_offline_command_shows_all_candidates_and_no_trusted_time
```

Observed one error in 0.119 seconds: `KeyError: 'sources'` at the assertion
reading the public CLI JSON report. The minimized trigger is
`cli.main(['time', 'inspect', '--offline'])` with ambient installed stable-time
configuration. No acquisition is needed for the failure.

## Hypotheses and controlled probe

Ranked and communicated before probing:

1. Ambient stable-time configuration selects the service-consumer schema;
   explicitly disabling that configuration should restore the candidate registry.
2. CLI offline routing differs from direct command routing; direct command
   invocation should disagree with the CLI.
3. Serialization drops candidate diagnostics; direct inspection should retain
   sources while the CLI without configuration loses them.

Changing only `CODEX_WAKE_STABLE_TIME_CONFIG` to an empty string made the exact
red command pass in 0.083 seconds. This confirms hypothesis 1. The command
intentionally uses distinct report schemas for installed-service consumption
and legacy candidate inspection. The test had failed to declare which mode it
required. Production behavior therefore needs no change.

## Repair and bounded validation

The existing public CLI regression now explicitly disables installed-service
configuration for its candidate-registry expectations. A complementary public
CLI test supplies explicit installed-service configuration and verifies uncertain
status, no observation, and no acquisition call in offline mode. Both fixtures
are independent of the user's installed configuration and restore the process
environment afterward.

Focused `test_time_inspection`: 9 tests passed in 0.102 seconds, including the
original exact symptom and both offline configuration modes. Paired-module
`test_time_inspection test_stable_time` validation passed 15 tests in 0.205
seconds using the same Python executable and `PYTHONPATH=src:tests`. No instrumentation
or temporary prototypes remain. Full-suite and CI acceptance belong to the
primary lane; this packet does not claim either.

Residual risk: live service acquisition and platform collection were deliberately
not exercised. They are unchanged. Memory disposition: not_durable; narrow
pre-existing test-fixture isolation repair is retained in this source evidence.

Primary final reconciliation: comprehensive3.12 at16c2501 passes1651tests in
823.097s, OK(skipped1), exit0 under900s. All three targeted repairs now qualify;
issue342 closes. Earlier provisional open/pending statements are historical and
superseded. No production/provider effects or CI run. Primary memory disposition
is forbidden(no explicit memory-update request); lane-local non-write labels
above do not authorize a memory write.
