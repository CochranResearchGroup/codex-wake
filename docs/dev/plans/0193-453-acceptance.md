# Integrated actual 0.166 acceptance (#453)

State: RUNNING. Plan0193 and specification #444 remain the scope authority.
This record distinguishes source verification, the actual disposable job and
production activation. No production activation is authorized or claimed.

## Frozen run

- Source checkout: `codex-wake-accept453`, branch `feat/upgrade-accept453`.
- Executed public source: `f7adb2958e239d66dfbbc28d4cc88da077f9d419`.
- Environment: Ubuntu 24 in disposable `wsl-test`, UID1000; private prefix
  `/home/ubuntu/codex-profile-lab/upgrade453-20261031/venv`.
- Root: `/home/ubuntu/codex-profile-lab/upgrade453-20261031` inside that distro.
- Job: `6ca6cce33db1406db89087c3b9fe54c0`.
- Frozen configuration SHA256:
  `398255aae8a33b63f7d35c86f59ca749c6522122c64f3ea34c298a71f653e6e4`.
- Official 0.166 commit: `6ff1e1ca3b30fc8b914720681fcf5fe62e95f856`;
  archive SHA256 `1e33229b8b63237f666d62ba1476134383400d66032cdfde10b7f79debd15d28`.
- Original limits: three semantic attempts, two hours, two compiler jobs,
  24 GiB owned temporary data. Manual monitoring; no resource renewal.
- Coding worker/reviewer: independently authenticated disposable A/B accounts,
  fresh ephemeral contexts, pinned combined native 0.165 executable. Their real
  coding calls are source maintenance. Installed authenticated qualification
  canaries remain metadata only, with zero provider model turns.
- Native patch bytes, account metadata, raw source/model logs and full receipts
  remain private and are excluded from public Git.

The root retains `launch-1.json`, `frozen-inputs.json`, `run-1.log`,
`run-1/checkpoint.json` and the unique terminal `run-1/completion.json`.
The terminal artifact is completion evidence only after its result is verified.

```sh
<private-prefix>/bin/python <private-source>/scripts/upgrade_bot_acceptance.py \
  --root <private-root> --recipe release --evidence <private-root>/run-1
```

A detached, identity-recorded process owns this invocation. Every phase uses a
fresh `UpgradeJobs` instance at the public job seam. The launcher does not replace
repair, build, review or qualification executors with successful fixture reports.
A held candidate retains its original budget and is not silently retried.

## Source checks

Local checks, rather than hosted GitHub Actions, satisfy the CI cost policy.

- `PYTHONPATH=src python -m unittest discover -s tests -p test_upgrade_bot_acceptance.py`:
  2 passed (terminal hold/budget preservation and production-target refusal).
- `PYTHONPATH=src python -m unittest discover -s tests -p test_upgrade_repair.py`:
  14 passed at the frozen source.
- `PYTHONPATH=src python -m unittest discover -s tests -p test_upgrade_codex_worker.py`:
  4 passed at the frozen source.
- A subsequent test-only commit adds an older-package substitution refusal:
  `PYTHONPATH=src python -m unittest discover -s tests -p 'test_upgrade_bot_*py'`:
  3 passed. This does not change the executing probe bytes.
- `python -m py_compile` passed for the new launcher and native/history probes.

The host source checks use Python3.12; hosted CI's Python3.11 matrix is not
represented by these commands. The primary owns final integration checks and
one broad review. These focused checks do not establish installed acceptance.

## Preflight evidence and limitations

The first WSL file-copy connection failed with `Wsl/Service/WSAETIMEDOUT`.
A separate pending source-sync completed, and exact module/script readbacks
identified which copy succeeded. Only the missing verifier copy was repeated.
No WSL restart or unrelated process termination occurred.

The dependency prewarm copied no production Cargo cache or credentials. It
fetched public dependencies into an owned cache, then was explicitly stopped
before actual compilation. Its detached process exit code is unavailable;
`prefetch-observation.json` states this and claims no dependency readiness.
The actual job must verify/fetch all dependencies itself.

Build and verification explicitly select `x86_64-unknown-linux-gnu`, Rust1.99.1,
`dev-small`, two compiler jobs and the owned external target directory. This
avoids the canonical builder's default Linux musl target. V8 archives/bindings
are verified through the pinned upstream package helper and trusted manifests.
Generated standard/experimental protocols, SDK types, config schema and locked
Cargo metadata are included before independent review. Compiler/interpreter
outputs are kept out of the reviewed source snapshot.

A deterministic fixture marker is added during package construction, before
package inventory and qualification. Fresh probes run on the exact new package:
missing-output normalization/accounting/notices, foreground TUI health, scoped
reload, and failed-start/history/compatible rollback journeys. The full
qualification executor separately binds authenticated metadata, source, package,
module, tests and configuration identity. Old 0.165 receipts qualify only the
retained rollback baseline.

Remaining evidence: actual repair/review dispositions; final source/package
hashes; fresh 0.166 probe and authenticated metadata results; future-launch
selection with old-process pinning; registered notice delivery; explicit rollback,
disable and final owned-process/resource census. Until these exist, #453 stays
open. Managed running-daemon cutover and production profile activation remain
separately held by #413 and #380.

## Same-job execution checkpoint

The three real coding contexts completed, and all 69 intended patch paths remain
represented in the candidate. These are worker dispositions, pending independent
review and actual compilation. Regeneration after workers 1 and 2 failed because
the private host adapter imported the upstream package helper without
`CODEX_REPO_ROOT`. Both failures remain in `repair/8-regenerate.stderr` and
`repair/12-regenerate.stderr` under the job directory. No input was edited,
no fourth worker was started, and no deadline or counter was renewed.

Worker 3 added a checked standalone helper root fallback, preserving explicit
root overrides, with focused root/V8/Cargo helper tests. Its broader Python
packaging checks reported four missing-`zstd` environment errors; those are not
passing tests. Host regeneration command 16 has now passed the root import and
is completing the public dependency checkout. Rust compilation, independent
review, complete package and installed acceptance remain pending.

Native aggregate usage reported by completed coding contexts (allocation and
underlying provider request count are unknown):

| Context | Input tokens | Cached input | Output tokens |
| --- | ---: | ---: | ---: |
| Worker 1 | 1,966,820 | 1,837,568 | 10,929 |
| Worker 2 | 1,217,092 | 1,126,656 | 7,959 |
| Worker 3 | 670,308 | 613,760 | 5,559 |

`restart-dedup-readback.json` records a fresh installed CLI process re-admitting
this release: the same job, key, creation time, deadline and three charged
attempts were returned, without replaying work. This proves admission continuity
across processes, not crash recovery of an interrupted stage.

A separate read-only observer records phase changes, owned job processes,
temporary file bytes and shared-kernel resources in `monitor-1.jsonl`. It exits
when the job becomes terminal. Its launch and terminal receipts are separate
from job acceptance. At the latest checkpoint, temporary job data was
221,594,783 bytes, with public dependency cache accounted separately; the live
V8 Git pack's fresh modification time demonstrated checkout progress.
