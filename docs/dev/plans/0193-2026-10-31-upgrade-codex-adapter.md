# Native Codex coding adapter for #448

State: CLOSED
Owner: upgrade-bot coordinator
Specification: #444 / Plan0193

## Current State

Actual disposable native source maintenance is accepted: two coding contexts and
one independently authenticated native reviewer completed the original69-path
port with valid reports, real Rust verification and canonical complete166 package.
Fresh installed A-B-A metadata/account qualification and native journeys passed.
See [package](../evidence/issue0444/semantic457-package.md) and
[installed acceptance](../evidence/issue0444/native453-acceptance.md).
This closes the adapter delivery; configured labels alone still do not establish
provider account identity. Source-maintenance usage and zero-turn qualification
remain separate. No production activation is included.

## Host configuration

Use one private, owner-controlled JSON file per role. Configure different role
identities and dedicated homes for independent worker/reviewer accounts. The
repair executor already rejects identical identities or identical role commands.
Configuration is host input, not an API/MCP caller-supplied path.

```json
{
  "schema_version": 1,
  "role": "worker",
  "identity": "upgrade-test-account-A-worker",
  "test_root": "/absolute/disposable-test-root",
  "codex_home": "/absolute/disposable-test-root/account-A",
  "executable": "/absolute/pinned-complete-native-package/bin/codex",
  "sha256": "<exact executable SHA256>",
  "timeout_seconds": 600,
  "model": "<operator-configured coding model>"
}
```

`model` is optional. The selected account must already exist strictly below the
configured test root; root and account ownership must match the executing user.
No login, token copying, token-file reading, ambient account selection or
production fallback is implemented. A missing authentication session is a native
execution failure to report, not a reason to initiate login or try another home.

Configure the repair executor's worker/reviewer argv separately:

```text
python -m codex_wake.upgrade_codex_worker --config /private/worker.json --role worker
python -m codex_wake.upgrade_codex_worker --config /private/reviewer.json --role reviewer
```

The host executor supplies `CODEX_UPGRADE_PACKET` and `CODEX_UPGRADE_RESPONSE`.
The adapter reads the former and atomically writes a validated successful role
response to the latter. On failure it exits nonzero with a bounded classification
on stderr; it does not write an invalid/unvalidated output destination.

## Native launch contract

The pinned modern help was checked without a model turn. The adapter uses the
existing descriptor-pinned executable and dedicated-home ownership lock, then:

```text
codex --no-daemon --ask-for-approval never exec --ephemeral --ignore-user-config \
  --sandbox workspace-write --cd /owned/source --output-schema /owned/schema.json \
  --json --color never --output-last-message /owned/native-final.json -
```

The reviewer instead uses `--sandbox read-only`. Each invocation creates a new
context; neither role resumes or forks a prior worker conversation. `--ephemeral`
avoids persisted session files. `--ignore-user-config` retains explicitly chosen
`CODEX_HOME` authentication while avoiding unintended user configuration/MCP
connections. Existing execpolicy rules remain enabled.

The model receives the complete canonical source packet through stdin, including
pinned patch intents, current candidate/test digests and prior findings. Worker
instructions require every patch disposition and concrete equivalence evidence
for retirement. Reviewer instructions require independent source/test inspection
and rejection when behavior is unproved; worker claims are not evidence by
themselves.

The wrapper generates a fixed-key JSON schema for every required capability and
patch identity, validates the final model response locally, rejects reviewer
source mutation, and computes truthful post-worker source/test digests. A native
JSON final response alone does not constitute installed capability qualification.
The outer repair executor also validates reviewer identity and content binding.

Native events and stderr remain private per-invocation artifacts. Returned
adapter provenance identifies the configured account home, role, pinned binary,
sandbox and event-log digest. It distinguishes coding execution from installed
qualification and authenticated metadata-only acceptance canaries.

Native subprocesses have bounded timeouts and owned process sessions. Wrapper
SIGTERM is forwarded through cleanup to the owned group; final kill/reap runs
on normal completion, error and timeout. The outer repair job still owns total
attempt/deadline/storage limits and disable fencing. The configured native
sandbox and disposable operating environment remain meaningful containment
boundaries; process grouping is not a general OS sandbox.

## Testing and remaining acceptance

Public wrapper tests use a fixture CLI executable whose exact hash is pinned.
They verify argv, role separation, dedicated account environment, schema-bound
responses, missing/mismatched identity refusal and suppression of ambient
provider keys/session IDs. They do not contact a provider or prove model quality.

The integrated acceptance must execute actual worker/reviewer model turns in the
designated disposable accounts, independently inspect their repair/review output,
and run complete build/runtime qualification. Those coding turns are counted as
source-maintenance work, not silently relabeled metadata-only model canaries.
No such model turns were executed while implementing this adapter.
