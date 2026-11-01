# Integrated actual 0.166 acceptance (#453)

State: CLOSED / ACCEPTED2026-11-01. Actual public semantic166 package, independent
review, installed A-B-A/all11 native checks, future selection/pinning, public
future launch/reconnect and actual compatible rollback passed. See
[final native acceptance](../evidence/issue0444/native453-acceptance.md) and
[one final review/TDD](../evidence/issue0444/final-review.md).
Working production is unchanged; the disposable final165 selection is intentional
rollback acceptance. The old failed/expired runs below remain frozen history.

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


## First compile hold

The third regeneration command reached actual GNU/dev-small Rust compilation.
The storage monitor then raced Rust deleting a temporary `lib.rmeta` file and
held the job with `FileNotFoundError`. This was a controller sizing failure,
not a Rust compiler rejection. The original completion receipt reports held;
no 0.166 package, independent approval, qualification or promotion exists yet.

`held-1-readback.json` records three charged attempts, original deadline
`1793478757.2470584`, and the unchanged retained 0.165 selection (CLI SHA256
`0d511c4a77c56b0a09f8549f6e43218ee899d0b66598725d4b67c71dc935a973`).
Owned job processes were absent after cleanup. Terminal cleanup reclaimed
348,215,537 bytes of owned compiler cache; public dependency cache and all
source/reports remained retained. The interrupted command keeps its intent
record and owned PID/start identity; no successful exit is inferred.

Only `codex-rs/Cargo.lock` changed after worker 3, during owned Cargo generation.
The test digest is unchanged. The current candidate digest is
`922ba019ce189349f336b4ad4a156fbc0483bcf3e89d44a1ca513e3a30a986a6`;
the last worker's pre-generation digest is
`e0a68325910a7f6c79b471bcb6d905e836f9229e81a5c7f1a80725e9de67751d`.
Continuation must preserve this generation provenance and original accounting.

The missing test dependency was corrected in the disposable distro:
`zstd 1.5.5+dfsg2-2build1.1`. The full actual candidate packaging-helper suite
then passed 29 tests, with `PYTHONDONTWRITEBYTECODE=1` and before/after Python
helper hashes unchanged. `supplemental-package-helpers.json` and `.log` retain
that source-only evidence. No frozen driver, configuration or candidate code was
manually edited.


## Verification-only continuation

Run 2 executes controller revision
`82a61a17d6dcc5e443a2215dd131f59471369df7`. Only the six corrected controller,
pipeline, repair and storage modules plus the separate continuation launcher were
installed into the disposable source/prefix. `controller-update-2.json` records
old/new module hashes and verifies every frozen qualification input unchanged.
Candidate source, recipe, host programs and original job accounting were untouched.

`upgrades.reconcile` returned `verification_ready` on this same job. Its receipt
binds the current source inventory and last completed worker report, records the
interrupted regeneration leader/group as dead, and retains the original monotonic
and wall deadlines and three attempts. Run 2 never invokes enable or start.
`launch-2.json`, `run-2/checkpoint.json`, `run-2/completion.json` and `run-2.log`
identify the unique continuation. It has resumed actual Rust/C compilation.
The later `4bb3586` cached-inflight readmission guard is source-tested but is not
part of this frozen execution; the original first-reconciliation path is unchanged.

Actual operator witness 6 recorded all four retained canonical events, including
the held event. Its original grant expiry `1793479039.1637716` remained unchanged
when the exact notice control capability was added. The failed scope-refusal
journal from witness 5 remains retained. A fresh private native backend then read
the exact held notice ID/text from durable history with model context available;
`operator-witness-6/cold-readback.json` records zero model requests and no remaining
owned reader process. Blocked background proxy CONNECT attempts are reported
separately from successful external requests.

Operator witness 7 now holds an actual old 0.165 private client through the public
build launcher while a separate exact-health-bound TUI receives job notices.
Its ready/progress/terminal artifacts retain the original process identity,
selection, grant expiry and notice journal. It must observe selection before
closing its owned clients. The independent reviewer, final package and fresh
0.166 installed qualification are still pending.


## Terminal result: unqualified native candidate

The verification-only continuation held at `1793475950` with
`verify_only_verification_failed`. The actual app-server library test build
reported two source-port errors:

- `E0223`, `app-server/src/request_processors/thread_notice.rs:86`: the old
  agent-message construction does not match the 0.166 `ThreadItem` API.
- `E0061`, `app-server/src/request_processors/thread_listener_shutdown_tests.rs:67`:
  the goal processor constructor now requires an additional authentication-manager
  argument.

`repair/20-verify.stdout` retains the complete compiler output. No fourth coding
worker or manual native correction was issued. Independent source review,
complete 0.166 package, qualification, promotion and new-package rollback were
not reached. **#453 remains open.** No 0.166 source/package acceptance is claimed.

`final-held-closeout.json` and `final-held-source-inventory.json` retain the final
9,786-file source digest
`1ea75d639a83bb0e487baf36630c2f929a5f0469b627f9e8b24d01132a7c8fef`
and test digest
`cbd569da9c6b7c6750c933d6f8285fd1bc100f1c2203dfb6a8d0a2997160e11c`.
The working 0.165 CLI and complete package remain selected and unchanged
(package digest `34be699bbbd6fee8f9f87c2f81fa7e28d15bc3636b265d9d3b9edc2b509fd38a`).

Operator witness 7 confirmed that its actual old 0.165 private client remained
pinned through this terminal failure; retained job notices were recorded and its
owned clients were closed. The final fixture process census was empty. The
sampled peak job file size was 7,183,492,823 bytes, below the 24 GiB cap; terminal
cleanup reclaimed 6,958,987,125 bytes of owned compiler cache while retaining
source, reports, public dependency caches and the known-good package.

An explicit bare local `upgrades disable` completed at `1793476613`.
`disable-local-readback.json` proves `enabled=false`, generation 1 to 2, and the
entire held job dictionary unchanged, including identity, three charged attempts
and original deadline. No worker, existing profile or shared native service was
restarted.

`successor-preparation.json` contains locators and proposed bounds only: one
additional actual coding attempt and 90 minutes under fresh disposable authority,
with the failed original retained. It creates no successor, grant or model call.
Future-child private-umask corrections are source-tested but were not installed
or exercised in this failed original run. Production activation and managed
running-daemon cutover remain separately gated by #380 and #413.


## Approved successor checkpoint

The operator approved one additional coding context and 90 minutes overall in
disposable `wsl-test`. Successor `88ffcb281213459da987156e8af41984` uses a
separate root, `upgrade453-successor-20261031`, and unchanged frozen configuration
`a6871b6c31dc6c43fa28e711ddd29c342c50335a475d655a78114024d8365ac9`.
The coding allowance is charged 1/1. Its original job deadline is
1793483044.1438994, with overall deadline1793483643.8781624; persisted monotonic
deadlines remain authoritative when guest UTC rolls back. No deadline, coding
allowance or resource authority has been renewed.

The native worker wrote both reported Rust corrections but was interrupted
before `turn.completed`; no worker report is inferred. Its source digest was
`3d74750c5b85faab4baf8297eda3162fea18778170069a3222796c8793ded5f4`.
Explicit `verify_review_only` recovery retains the original worker identity,
exit census, native events and charged context. It requires host verification
and independent review of every patch; `worker_completed` remains false.

A first recovery launcher omitted the sealed Cargo wrapper from PATH, causing
a redundant dependency fetch. Its verified owned regeneration group was stopped;
the failed command and receipt remain retained. No candidate source was manually
edited. Controller628a1ed permits another deterministic verification admission
with a fresh census and no coding/reviewer replay. Run3 uses the sealed wrapper
first in PATH, pinned GNU/dev-small Cargo and two compiler jobs. At1793481875,
regeneration11 was compiling actual0.166 utility/network crates without reported
errors, using1.46GB of workspace data. Independent review, complete package,
qualification, future-launch selection and rollback remain pending.

Local comprehensive validation at source26b52dcd384a852d7cbefec7d6c026e672e84b41
passed all seven checks under Python3.11.15, including2013 tests in788.298seconds.
The Python3.12 run is still in progress. Receipts are private `/tmp/w26v/`;
the explicit unavailable time fixture avoids Windows clock inspection. Latest
repeat-admission source628a1ed has five focused and18 existing Repair tests passing.
Final broad review/findings TDD counters remain0/0 pending actual ticket acceptance.


## Successor terminal result

The public job and Repair controller report `held: deadline_exhausted`. First
observation was1793482874.446 / monotonic25656.316, about9.84seconds after the
original job monotonic deadline25646.475213728. Observation latency alone does
not establish exact process stop timing; the terminal census must resolve it.
The original overall monotonic deadline26246.475213728 remains unchanged.

Host regeneration completed: standard and experimental schema fixtures each
passed one test; SDK and configuration schema generation completed. Verification
then passed protocol fixtures4/0failed/1ignored in9.45seconds. App-server/TUI-health
compilation was interrupted by the deadline; no new compiler error was reported.
The two Rust source corrections therefore remain incompletely verified. There
was no independent reviewer, complete166 package, qualification or promotion.
Ticket453 stays open. No additional coding context or extended deadline is
authorized. Final broad review/findings TDD remain0/0 because acceptance is unmet.

Python3.12 comprehensive validation timed out after900seconds; its receipt is
retained and does not qualify that matrix entry. A separate verbose diagnostic
uses the frozen source explicitly. An earlier ad hoc diagnostic omitted source
PYTHONPATH and imported an older installed package; it was stopped and excluded.
Python3.11 comprehensive remains seven checks PASS,2013tests/1skip.


The enforcement decision was monotonic25647.050692496,0.575479seconds after the
job limit. Exact child signal/exit monotonic times were not journaled. An
independent root census at25671.313 found no owned processes,24.838seconds after
the job deadline and within the original overall deadline. Local disable at
25707.863 changed generation1to2 and preserved the entire held job. The original
job and eight frozen inputs are unchanged. Final independent post-disable census at25778.716 scanned78process entries,
with zero unreadable and zero owned processes, within the original overall bound.

Final successor source:9,784files, digest
`bb296cbefc1f576acc54f8aae153708b2911c732f6555538e4aab7dddc2012fe`;
test digest remains
`1c7a648508a8bb315369694668458664ef36c3d9dd8a110ef29162ff58ed66bc`.
Sampled peak job data was6,054,948,083bytes; terminal GC reclaimed4,075,991,076bytes
of owned compiler cache. These partial artifacts are not a qualified package.


The retained165 client stayed pinned through the terminal event and closed. The
active recipient recorded all ten canonical notices. Four historical delivery
failures to already-closed recipients remain visible. No new provider model turn
was used for these notice checks. Final terminal receipt SHA256:
`22b9ebb77c37bfcfb8c2ea6b5e0970d0236a3c860936b318ad098425065a00ad`;
post-disable census SHA256:
`e10e989c5cb60ecb51c72892a255000b367a88acbb79ccf23579df73f1ca87be`.
Curated private receipts remain in the ticket453 actual166-successor packet.
Published terminal readback: issue453 comment6549533282. Neither native held job
is resumed, and no additional native work is authorized by this checkpoint.


Python3.12 source diagnostic completed2013tests in677.459seconds with23failures
and1error, all in refresh scenarios. It inherited working environment and is not
a canonical qualification result. Re-running that group through the canonical
isolated source-bound runner passed29tests in16.435seconds. The initial full
canonical900-second timeout remains unresolved; neither diagnostic replaces it.
No clean full3.12 matrix is claimed.


## Follow-up diagnosis (source-only, no native retry)

Operator approved diagnosing-bugs after the terminal hold. A differential probe
runs existing public Repair clock tests against pristine3b31bdf and current
source: the old revision holds on a five-second UTC rollback; current passes
while preserving deadline and boot/counter uncertainty holds. Logs are private
`/tmp/wake-diagnosis453/{before,current}-clock.log`. This qualifies that regression
fix, not the historical interrupted sample, whose exact subtype remains unknown.

A new public validation-runner regression reproduced lost partial stdout on a
0.2-second timeout. Fix8595293 retains stdout/stderr with replacement decoding,
marks `timed_out=true` and still blocks later checks/actions. Six runner tests
pass. A single diagnostic comprehensive3.12 run uses immutable8595293, verbose
output and unchanged900-second check limit; result pending. Its initial argument
ordering failure is retained separately from the corrected run.

Host PATH omission now has a subsecond public Repair reproduction. Optional
sealed `repair.host_tools` declarations pin command resolution and bytes before
replay/every subprocess; fallback/changed wrappers hold without a coding charge.
No original or successor fixture config or job is changed, and no native retry
is started. This diagnostic work does not count as the final broad review or
post-review findings TDD round.


A second timeout regression reproduced an owned child surviving the runner's
expired command. POSIX checks now launch in a new session; timeout cleanup kills
that owned process group before collecting output. The regression uses a real
child ignoring SIGTERM and observes its exit, then verifies failed status and no
success actions. Seven runner tests pass on both3.12 and3.11. The
ongoing comprehensive snapshot8595293 predates this process-group change and
host-tool preflight2d928ba; those changes have focused validation, not that full
run's identity. Non-POSIX fallback terminates the direct child only.


### Diagnostic terminal outcome

The corrected comprehensive3.12 run at8595293 also timed out at900seconds. Its
new receipt retains1281completed test rows with no failure lines, stopping during
`test_operator_cli_issues_separate_grok_actor_with_real_audit_receipt`. The entire
five-test runtime A2A group then passed in3.416seconds through canonical isolation;
the observed last test took0.278seconds. It is not established as a stall. The
full isolated suite exceeds its budget, but the cause of cumulative cost is still
unresolved. No third full replay or raised budget. Diagnostic owned group census
is empty. Per-test profiling is the next performance seam.

Latest2771981 source-bound presubmit passed all10checks on3.12. Seven runner
regressions pass on both versions;25Repair/interrupted-worker tests pass3.12,
and the new tool/runner selection passes8tests on3.11. These focused fixes do
not qualify the full3.12 matrix or native166. No native context, original job
renewal, deployment or shared restart occurred. Final broad review/TDD remain0/0.
Private diagnosis summary and source-bound receipts: `/tmp/wake-diagnosis453/`.


## Profiling result and explicit temporary storage (2026-11-01 UTC)

The operator authorized per-test profiling. A matched scheduler test made217
fsync calls in both configurations, taking1.033202seconds on disk and0.006431
seconds on RAM. This confirms a substantial temporary-fixture storage cost;
production fsync/durability operations are unchanged.

The initial external helper omitted the repository import root. Five entries in
its150-row samples were import errors, not passing tests. Its attempted full run
collected1679instead of2018tests and was explicitly stopped in its owned group.
Those failed receipts remain retained; the earlier statement that150tests passed
was incorrect. The valid145-test subset measured64.757/25.895/68.495seconds for
disk/RAM/disk, but none of those initial selections qualifies as a passing run.

The corrected helper verifies the full ordered test-ID digest against ordinary
unittest discovery before any test executes. At immutable311d7e5, the verified
first150tests passed on disk in98.266seconds; the identical first150 in the full
RAM run passed in40.544seconds. Public `local_validation.py --test-temp-root`
creates only a private mode0700 TMPDIR child under an explicit existing parent,
records that root and its acceptance boundary, preserves unrelated files and
rejects candidate-internal roots. Default placement remains unchanged. Four
public launcher regressions pass on each Python3.11/3.12.

The full guarded3.12 run at311d7e5b66063ccaafda0f46851c44ed521a66b5 passed
2018tests/1skip in548.785seconds; all seven comprehensive checks, including
packaging, passed. It used explicit `/dev/shm` TMPDIR and a900-second diagnostic
ceiling. Its observed unit duration is below the unchanged600-second default.
This is RAM-backed functional source validation, not physical-disk durability or
native166 qualification. Earlier disk-backed timeout receipts remain failures.
No third disk-backed full run, removed tests, disabled fsync or increased default.

Private durable evidence: `testing/ticket453/profiling-20261101/` under user-state
Codex Wake. Full receipt SHA256:
`7a1adb920ffe7a060cebbf6fa2a49895948f1052bf181ccfd249d9cc8d9b65bf`;
verified disk150 receipt:
`be46a38ff4aa91eb5e3eb6cf91c51e454cd651dbd12bf444ffdb36569b101588`.
Raw import failures, helper versions, collection guard and syscall summaries are
retained privately. Created RAM test directory was removed by the launcher.
Native453 package/verification/review/qualification remains open. No native job
action or deployment occurred; final broad code-review/findings TDD remain0/0.


## Fresh zero-coding native verification | 2026-11-01

The operator re-invoked implement-spec to finish453. Primary owns the remaining
ticket; other children are validated and tracker-closed. New controllerc9aafa4
adds zero-coding limits and strict independent per-patch review. Public upgrade
regressions pass88tests each3.11/3.12; exact fresh-prefix Jobs/Repair hashes match
fd14b934/8bf1f360. WSL prefixPython3.12.3, CodexWake0.22.0.dev2, MCP2.2.0.

The normal new job replays a mechanically derived124-path delta (all69 original
handwritten paths), with original patch ID/intent and four prior coding contexts
retained separately. A pinned mode-only normalizer validates all9784paths/bytes
and restores1131modes, reproducingbb296/tests1c7. No old source file is edited.
Both old job dictionaries and eight original inputs remain unchanged/disabled.
Public dependency/V8 caches are copied into the new scope without old hardlinks.

Fresh job `72caa827b813497e80d2c7c16c3708cd` was publicly started once, with zero
coding attempts and one required native independent source review. Canary model
turns remain zero. Created1793534081.088541 / monotonic80476.137646633; job
monotonic deadline87676.137646633, overall88576.137646633. Limits7200seconds
plus900reserved cleanup, compiler2, temporary24GiB, manual monitoring. Source
review is distinct from the final broad controller review/TDD, still0/0.

Fresh witness2 pins actual165PID1242. Its private helper lifetime was corrected
7500to9000 before job creation; the expired witness was cleanly closed. A final
prestart guard caught control authentication7.136seconds short of the reserve.
Primary replaced only that new fixture's prestart control grant once, with same
target/scopes/resources and expiry1793543079.808495. This did not renew any old
job, goal or resource allowance. No work clock existed before this start.

Freeze-v2 SHA256
`d350f6f935dfcdc7f3c3d9d2c7bb8546c7d0b1968fb604baebafe7cbde47801f`;
configuration
`7715c5723672c8ee1babc71bcaa2c1edfe9dd819d3d64c15b35f6831d0cd53d4`;
recipe remains
`de1ae0e7862b8ac8f7bbed9d23c48cc407d8bc2f7130487f79bf10641d275538`.
Host private freeze/start proofs live in ticket453/fresh-verification-20261101.

First runtime evidence: clean patch replay and metadata normalizer pass, then
actual regeneration8 runs two Rust compiler processes without a dependency-fetch
loop. Atmonotonic80774.945, worker/reviewer counts0/0 and115minutes job remain.
No native166 package, qualification or promotion is yet claimed.


### Host Git drift after successful regeneration

Job72 completed full regeneration8 with exit0: standard/experimental fixtures
passed1each and configuration-schema build/run completed. Before verification,
the host tool guard correctly held on `/usr/bin/git` SHA mismatch. Ubuntu's
unattended updater independently upgraded git/git-man from7.3to7.4; actual
Git1:2.43.0-1ubuntu7.4 is root-owned0755 and matches dpkg's installed checksum.
Pinned SHA2a8c18fbf43da9f692d75474c72bea9dfd796c260b0f3dfe456376abc3bbd668
changed toeb54b535467e0975c1284d4c4d08eea779aeb248a5d34b02e2ee171382e22201.
Configuration7715 and all frozen inputs were unchanged. No verification command,
reviewer, coding worker or package ran. Passive supervisor disabled the new
fixture, preserved the held job and closed its witness; post-acceptance did not run.

Actual post-generation sourcece74/tests1c7 contains9785files: all9784 retained
files have identical bytes/modes, with only one additional Ruff cache file
`sdk/python/.ruff_cache/0.15.12/618090957912755795`. Original source is untouched.
Completed generation is retained primary evidence; the Git drift is a separate
failed environment gate, not a Rust compiler error. Terminal GC reclaimed
3,831,735,307bytes and removed that job's compiler target.

Primary authorizes one bounded retry, still under original monotonic job87676
and overall88576 limits, with zero coding/one unspent native source review. Use
a private immutable trusted Git7.4 copy and component manifest instead of
restoring/changing system Git or weakening the guard. A pinned cache validator
may reuse actual completed generation only after verifying report hashes and
exact retained source parity, explicitly retaining the Ruff cache difference.
Actual Rust verification, review, package, qualification and post checks remain
mandatory. Share the new owned compiler target between verification/package
through the canonical builder's supported CARGO_TARGET_DIR; no flags/tests waived.
No7200second restart, third attempt, global update, old goal/resource renewal or
extra model review. Retry duration is computed from remaining original deadline
immediately before public start. Native acceptance and final review/TDD remain open.

Private diagnostic SHA033b9390d134d0b6b35ea11ee1081d6b976954da74981b43064f8bdda1121598;
source diff SHAf7de0de1237b61a80d16518150ce9204a5f6954b7dbffe48e4eb240bf3073324.

### Bounded retry started

Public job `9e709dff983a423886954202a739351d` started once in disposable
`/home/ubuntu/codex-profile-lab/upgrade453-retry-20261101`, from controller
`c9aafa4367ee98159cd3e8c8316a2d6ffd3199a7`. Duration3211seconds, monotonic
start84455.241567116, job deadline87666.241567116, post/cleanup88566.241567116;
both deadlines precede the original packet's limits. Freeze SHA
`53de7da884e6d69b1bdd27651fdea6d0ed980269a5ef8f3e973f943ee6104398`.
The ledger retains config/recipe and cached-generation pins. Generation reuse
validated actual completed job72 output; it is not a regeneration rerun.

Latest verified observation at monotonic86268.28: protocol tests4passed/0failed/
1ignored, actual app-server TUI-health compilation running, coding0/reviewer0,
no complete package. Owned files5.21GB; Linux available39.88GiB and Windows
physical free5.61GiB. Later control reads timed out; the last good snapshot is
explicitly stale. The in-distro monitor and passive post supervisor were placed
once; no duplicate launch or third attempt is authorized.

An attempted five-minute self-wake retained intent
`wake_intent_967af61945e540f48f6fee96d144978e`, but was NOT armed: monitor ready,
`original_utc_unavailable` / `relative_origin_unanchored`. It is not delivery
proof. Primary retains bounded foreground supervision with manual resources;
no replacement intent, governor enrollment or allowance renewal occurred.

Native qualification remains pending. Final broad review/TDD remain0/0.

### Retry terminal outcome: acceptance remains blocked

Retry9e is HELD `deadline_exhausted`. Protocol4passed/0failed/1ignored and
app-server TUI-health3passed/0failed are actual results. Turn-admission compilation
was interrupted; its test outcome and the remaining TUI check are unqualified.
No coding worker or independent native reviewer ran, no complete166 package was
produced, and qualification/promotion/post-rollback were not run. #453 stays open.

Job clock latest87666.843407547 exceeds its monotonic deadline by0.601840431s.
This is detection timing, not an exact descendant-stop timestamp. Supervisor
observed hold87667.752124274; public disable exited0 at87672.045419929, generation
1→2, preserving the entire held job dictionary. Final cross-group process census
at87683.376588649 found zero owned descendants, with no unreadable entries; all
cleanup completed within original reserve. Terminal GC reclaimed6,048,477,337B.

Witness status `observed_terminal_hold` confirms old-session pinning and unchanged
selected165 executable SHA
`0d511c4a77c56b0a09f8549f6e43218ee899d0b66598725d4b67c71dc935a973`.
Model/provider requests0/0. Passive post supervisor correctly did not run.
Raw private terminal receipt SHA
`a11257cb04a4d0c2a8e5da917088d3511678e95aa7f22b455a11244417d11a8d`.
No third attempt, deadline renewal, governor activation or production effect.

The requested final broad review and findings TDD remain0/0 because not all
tickets have passed acceptance. #413/#380, native recurrence and broader raw
orphan-output/HF-20 boundaries remain unresolved. Next packet must first address
build execution/cache economics, then obtain complete native acceptance; do not
replay this expired job or silently grant another full duration.

Final curated private closeout SHA
`a7d7b045461242bc5d0fdcf821233476ba3ef54c02cce506ce778ff8a7c62320`
confirms exact sourcebb296/tests1c7 (9784files), protected original/successor/72
controls unchanged, first recorded empty owned-process sample87670.12330836,
whole-root sampled peak7,538,784,750B and4 canonical recorded notices. Verification
journal remains `intent`; no exact child exit timestamp is fabricated. The
witness trap blocked10 background CONNECT attempts; successful external provider
requests0. Final Linux available35,965,836KiB, disk available988,380,250,112B;
Windows physical free4,473,952KiB and virtual free41,274,296KiB.
