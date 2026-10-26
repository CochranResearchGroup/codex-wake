# Modern native port review

Review target: upstream `6aaac694803004a63c6f393d153c96d22521a6b9`
through `fda3733d6a` on `fix/wake-native-0.164`.
Spec: [modern port plan](../../plans/0173-agent-harness/0006-2026-10-25-modern-native-port.md).
Independent reviewer: `/root/modern_port_review`. One discovery pass; no compilation or edits.

## Standards

No candidate findings. The review checked existing processor, per-thread
serialization, configuration-refresh and history-recording seams. External
lockfile dependency identities remain unchanged. Primary accepts this result;
no structural cleanup is added to scope.

## Spec

No candidate findings. The reviewer checked loaded-thread lookup, non-mutating
scope probing, captured runtime status without global discovery, no-turn context
injection, durable notice history, idempotency and confirmed connection writes.
Generated notices and runtimeOnly exports are present; reload remains experimental
as declared. Primary accepts the source-review result.

This is source review, not runtime acceptance. Focused integration tests, modern
managed roundtrip, actual TUI rendering, matching final package and live requesting
session acceptance remain separate gates. No accepted findings require remediation.

## Additional smoke

The initial complete package ran `/bin/sh` inside its real read-only sandbox.
It printed `sandbox-ok`; a cwd write failed with `Read-only file system`, and
no file was created. The private root had an explicit profile extending
`:read-only`. Two earlier invocations used obsolete syntax or omitted the now
required profile and failed during command setup; neither is a runtime regression.
Private receipt: `native-modern-0164/sandbox-readonly-smoke.json` under user state.
