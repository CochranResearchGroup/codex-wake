# v0.7.0 release candidate

Parent Plan0119 / issue181, primary serialized release branch
chore/p63-v070-release. Base9ea38d7a9844150b96ab3cfd85a84dc089058214 includes
PR213 live cancellation, clean reconnect return and owned-worker restart proof.
PR213 required Python3.11/3.12 CI run37250102958 passed before integration.
GitHub interpreted a negated closing phrase in the PR body as a closing keyword;
issue181 was immediately reopened and the body corrected. Current issue is OPEN
with ecochran76 accountable owner. This release does not complete its outcome.

## Candidate changes

Python package and CLI version0.7.0; shared reader clientInfo uses the package
version. Actual A2A setup/service documentation includes native enrollment,
bindings, delegation, managed reader before arm, actor exchange, reconnect,
clock/uncertainty boundaries and rollback compatibility. Shipped bounded
user-service example invokes the ordinary installed CLI, stops after3600seconds
or20notifications and does not restart automatically. README/skill/support
boundaries match the existing stock-Codex workflow. OpenClaw plugin version and
installed gateway/plugin are untouched; shared Codex daemon is untouched.

## Local validation

- Source full suite:908tests,93.715seconds, OK.
- Focused shared-reader suite:10tests,0.257seconds, OK.
- compileall and git diff --check pass.
- systemd-analyze --user verify accepts the shipped A2A unit.
- Isolated build produced0.7.0wheel and sdist.
- Installed wheel in /tmp/codex-wake-v070-candidate reports codex-wake0.7.0.
- Installed session discovery smoke accepted:18connections closed, descriptors
  before/after5, no lifecycle methods or transcript output.
- Installed product_smoke returned0 with CLI0.7.0, isolated provider-free
  filesystem/runtime/source fixtures and dispatch-disabled supervisor smoke.
  monitor_ready=false/product_readiness_overall=blocked is expected in its
  isolated no-live-monitor fixture; this is not live delivery acceptance.

Logs/artifacts:
/tmp/codex-wake-v070-unit-tests.log,
/tmp/codex-wake-v070-product-smoke-result.json,
/tmp/codex-wake-v070-product-smoke.

## Remaining release and goal gates

Publish only after required hosted release gates pass and the candidate enters
origin/main through its PR. No tag/public release or ordinary global installation
has happened yet. Public-tag installation, actual native owned-unit M1, second
root success/unenrolled denial, installed downgrade/refusal/compatible readback,
and real30-minute owned soak remain open. Never substitute this candidate build
or fixture smoke for those gates.
