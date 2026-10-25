# HF14 worker source evidence (#336)

Lane: feat/336-background-jobs; base457030622d59d2ec47f5190b2025fbb7ea50ca79.
Scope: background job owner module, dedicated command adapter, focused tests,
user documentation and frozen HF14 spec. Shared CLI/MCP/glossary integration,
issue state and source acceptance closure remain coordinator-owned.

## TDD receipts

Command for each vertical cycle:
`PYTHONPATH=src python -m unittest discover -s tests -p test_background_jobs.py -v`

- First red: missing background_jobs public module. First green: submitting
  Python process exits while detached command survives and retained exit7,
  stdout/stderr and original generation are readable after reconstruction.
- Second red: cancellation terminal receipt lacked actor (KeyError cancellation).
  Green: exact original generation, attributable actor and real TERM-resistant
  process-group descendants receive bounded KILL; returncode-9.
- Third red: public command inspection lacked authorize_inspection. Green:
  public owned inspection succeeds and foreign owner refuses.
- Fourth red: cancellation queued while supervisor stopped still signalled after
  mandatory permission revocation. Green: supervisor rechecks job.cancel at effect;
  the original command completes0 and refused cancellation remains attributable.
- Existing-daemon await acceptance initially failed because filesystem source
  reconstruction uses Resume.cwd as watched root. Correct supported fixture
  uses identical adapter.root/Resume.cwd; completion before registration fires
  once through the actual reconstructed existing source. Parent native absolute
  file-wake integration can preserve command workspace independently.

## Focused validation

10 background job tests pass, covering real subprocess/shell survival, controller
reconstruction, exact result/log identity, cancellation with owned descendants,
revocation, exact-owner admission, one-launch/conflicting intent, hard combined
log/wall caps, supervisor-loss unknown/no replay, unknown-version retention,
real ResourceClaims.guard release fencing and existing daemon await reconciliation.

`PYTHONPATH=src python -m unittest discover -s tests -p test_resource_claims.py`:
9pass.

Initial system Python session-permission selection had4environment errors from
missing jsonschema, not behavioral assertions. Isolated dependency rerun:
`PYTHONPATH=src uv run --no-project --with jsonschema==4.26.0 python -m unittest discover -s tests -p test_session_permissions.py`:
12pass,3.199seconds. This is the environment repair, not a silent test retry.

`uvx --from ruff==0.14.2 ruff check` for both owned modules and dedicated tests:
pass. `python -m compileall -q` for those three files: pass.
`git diff --check`: pass.

## Limits and remaining integration

These are provider-free source proofs, not installed/runtime deployment, host
reboot, service acceptance or provider resume evidence. Supervisor loss without a
terminal receipt remains unknown and may leave its old process group running;
product does not automatically relaunch or signal a guessed identity. Cooperative
non-daemonizing groups are supported; setsid escape and hostile same-UID execution
are outside this containment contract. Arbitrary command artifacts are outside
captured-log bounds. Mutation profiles need a host-verified fresh claimant; stale
claim evidence holds execution. No independent broad review performed in lane.

Memory disposition: forbidden; explicit worker task prohibits memory writes.

Final boundary check: cancellation discovered before exec now closes the gate and
publishes an attributable cancelled/no-command-release receipt. Its first focused
run exposed a revoked pre-release cancellation incorrectly changing the separately
authorized job to unknown (1failure/10). Corrected refusal retention consistently
before/after release. Final focused run:10pass,4.606seconds; full changed-file ruff,
compileall and diff-check pass. This preserves the failing run rather than
reporting the prior provisional checkpoint as accepted.
