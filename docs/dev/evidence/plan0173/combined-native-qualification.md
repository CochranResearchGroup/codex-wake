# Combined native qualification

State: SCOPED_STATIC_PASS after bounded match-arm repair; broad native suite remains open.
Bounded successor qualification; no historical goal was resumed and
no prior resource allowance was renewed. Original resource-stop evidence remains
at source45c0820320f5ca0867c56b137d2ca92fcfb7b47d.

## Custody

Wake source45c0820320f5ca0867c56b137d2ca92fcfb7b47d on
`test/combined-native-qualification`. Native source
b0ce988429488a3e37966c318f3fe0bfdf3af77a, based on
6115475dd95f6ffd525992bd5f98051d543a4c68, checked out separately on
`test/combined-goal-native`. Original native worktree retained its three pending
MCP unit-expectation edits and untracked CodeGraph index; neither was modified.

Private installed app-server bytes were freshly hashed as
86fad00e38f0c26a5c8d2eb2dbe34536c74655fb2fb45b4efc5d94e97e683b1f,
matching its user-scoped manifest and the accepted native journey. This is custody
of an experimental development binary, not activation or a new release.

## Observed historical evidence

Original logs copied without alteration to the user-scoped
`~/.local/state/codex-wake/combined-native-qualification/` evidence directory:

- historical-schema-final.log: schema writer completed successfully.
- historical-protocol-final.log:254tests passed, including generated JSON and
  TypeScript fixture parity.
- historical-usage-rpc-tests-final.log:2public no-turn notice cases passed.
- historical-clippy-final.log: recipe fix terminated by SIGTERM. It did not pass.

These receipts clarify the resource-stop handoff; they do not establish a fresh
final-source pass. The independently reported broad native two failures remain
unclassified and cannot be replaced by targeted successes.

## Fresh bounded checks

`git diff --check` passed on original native source. `just fmt-check` reproduced
Rust formatting failure across changed native files. `just fmt` succeeded in the
owned native successor. Three stale MCP test expectations now include the genuine
runtime sessionId and callId; no production logic was changed by this successor.
Final `just fmt-check` passed (exit0). Full patch reverse-application check and
`git diff --check` passed. Protocol/schema and scoped Clippy remain pending.

No shared native installation, daemon, watcher, production policy, provider,
allowance or service was changed. CI was not run. No memory write was authorized.

## Preserved fresh build failures

The first fresh protocol command began while an independent copy of historical
Cargo artifacts was materializing and rustc crashed in serde_with (SIGSEGV).
After the copy terminated, its error identified a disappearing source-cache rlib;
a second protocol attempt failed with missing parking_lot crate metadata. Neither
attempt executed tests or proves a source regression. Both logs remain retained.
The unusable copied cache was removed only from the owned checkout. The historical
cache and native worktrees were untouched. A clean isolated target retry uses
`just --set rust_min_stack 16777216 test -p codex-app-server-protocol`, honoring the
compiler's suggested larger stack. No cache copy is concurrent with that retry.

Patch SHA256:cd0cec867c5daa7098d53fbee333e197a9c47f053f7aeec39e4d082123350afd.
Owned successor diff SHA256:675d90d9cbb9f30781b73d2c8494ecd883541beec65dd7d560754624add98653.
Native successor remains uncommitted pending primary coordination.

## Fresh clean protocol and generated schema gate

PASS: `CARGO_TARGET_DIR=OWNED_CLEAN_TARGET just --set rust_min_stack 16777216 test
-p codex-app-server-protocol` exited0,254tests passed,0skipped. Both JSON and
TypeScript schema fixtures matched generated output. This run compiled the owned
successor source from a clean target and does not reuse the failed copied cache.
Receipt: combined-native-protocol-clean.log in the user-scoped evidence directory.
Scoped `just fix` is now running for core, protocol, app-server,
app-server-protocol and tui; its terminal result remains pending.

## Independent broad native failures identified

Canonical predecessor evidence is user-scoped under codex-wake/318-319:
`native-scoped-app-tests.log` records930tests:923passed (1flaky),7failed,1skipped.
`native-remaining-failures-serial.log` records2remaining cases,0passed,2failed:

- `suite::v2::hooks_list::hooks_list_warms_plugin_capabilities_for_thread_start`:
  deadline elapsed after approximately31seconds, both attempts.
- `suite::v2::safety_check_downgrade::model_verification_emits_typed_notification_and_warning_v2`:
  fails because an unsolicited skill-description-budget warning arrives while the
  fixture requires no warning for a verification-only response. Both attempts
  show the specific warning, along with untrusted /tmp project configuration.

These logs identify the symptoms. They do not prove whether baseline behavior,
host skill/config contamination, timing, or native changes caused them. Both
remain independent open gates; the254passing protocol checks do not close them.
Original logs are preserved and copied into the qualification evidence directory.
No source fix or fixture relaxation was made for either broad failure.

## Formatter normalization audit

An independent git archive of b0ce988 was formatted with the identical Rust
formatter backend (`cargo fmt -- --config imports_granularity=Item`). Every
successor-modified source file was byte-compared to that formatted baseline.
The only remaining difference was six JSON expectation fields across three
existing MCP tests in core/src/mcp_tool_call_tests.rs. All product source changes
were byte-identical after normalization. The exact normalized diff is retained as
normalized-source-delta.diff in the user-scoped evidence directory. This audit is
repeated after Clippy terminates; it does not claim a newly built behavior binary.

## Bounded single-variable failure classification

The historical cached app-server test harness was reused read-only, with
CARGO_BIN_EXE_codex-app-server explicitly overridden to the qualified86fad00
binary. The harness source custody is historical; its exact hash is retained in
broad-failure-comparison.json. The native executable hash was checked again.
Credentials were identically removed from both child environments. No global
configuration changed, no new native build was substituted, and no fixture
assertion changed.

- Safety verification: inherited HOME reproduced failure (exit101,5.41seconds,
  unsolicited skill-budget warning). Changing only child HOME to an owned private
  directory passed (exit0,2.56seconds). This isolates host-home contamination for
  that fixture on the qualified native candidate; it does not establish a broad
  suite pass.
- Hook warming: inherited HOME failed (exit101,31.25seconds); private HOME alone
  also failed (exit101,32.09seconds). Both returned the correct hooks/list data
  and timed out waiting for thread/start response. HOME contamination alone does
  not explain this failure. A final TMPDIR-only control relative to private HOME
  is pending; no baseline causality or source correction is claimed.

## Coordinated build pause

At the primary's request to remove compilation contention during the separate
180second native restart journey, only the verified owned scoped-Clippy process
group2671662 received SIGSTOP. All group members were freshly observed stopped.
The contemporaneous build-pause.json preserves the exact command, timestamp and
scope. This is a reversible pause, not a failed Clippy verdict or restarted build.
The build remains pending until its later SIGCONT and terminal result.

Hook TMPDIR control also failed (exit101,31.55seconds) with the same correct
hooks/list response followed by thread/start timeout, despite private HOME and
private TMPDIR. Thus neither inherited home skills nor /tmp ancestor configuration
alone explains the hook failure. Remaining hypotheses are plugin capability
cache/startup behavior, unreachable plugin-server startup ordering, or a separate
predecessor/runtime defect; no hypothesis is promoted to proven cause. A future
bounded packet should compare the unchanged hook case against the pinned scoped
refresh baseline with the same private environment, or capture a minimal public
RPC trace. No broad suite rerun, assertion weakening, or source fix was attempted.

The owned build resumed with SIGCONT at19:39:22.407478UTC. Its pause lasted
113.57992seconds; fresh states were S/Sl with no stopped member. The primary
explicitly allowed a bounded15minute extension only to finish this current scoped
Clippy and the already planned hook control, without renewing the historical goal
or authorizing any global runtime effects. Hook control is terminal; Clippy remains
pending at this checkpoint.

## Terminal scoped static result

FAIL: scoped `just fix -p codex-core -p codex-protocol -p codex-app-server
-p codex-app-server-protocol -p codex-tui` exited101. The clean build reached
codex-mcp-server, a transitive TUI dependency, and found a real exhaustive-match
omission: `mcp-server/src/codex_tool_runner.rs:218` does not cover the new
`EventMsg::RawResponseCompleted` variant. This is a source compile failure, distinct
from the earlier cache/environment failures. No production Clippy fix was applied.
The post-terminal normalization audit again found only the three MCP test
expectation changes beyond formatting. The missing arm remains a separate bounded
repair gate; no broad static pass is claimed.

A bounded stock0.164.0 counterfactual for the hook failure was attempted using the
same historical harness/private HOME/private TMPDIR and an owned wrapper executing
`codex app-server`. It failed before initialize because stock0.164 rejects the
harness flag `--disable-plugin-startup-tasks-for-tests`. This is harness/runtime
incompatibility and cannot establish a baseline hook verdict. Stock binary SHA256
b93f6811d3f653f0fb83be4050d857fb9abbb111dfa2ce160563327daff7f306.
Exact stderr and counterfactual metadata are retained user-scoped. No unsupported
flag was silently removed and no stock runtime/service was changed.

## Explicit follow-up: bounded exhaustive-match repair

The primary adjudicated the compile failure after verifying that every event is
forwarded through send_event_as_notification before the local exhaustive match.
At19:43:48UTC a new bounded15minute packet added exactly one product line:
`EventMsg::RawResponseCompleted(_)` beside RawResponseItem in the existing group
requiring no further local MCP tool handling. It preserves the preceding event
notification forwarding. The original compiler error is the regression red.
Affected scoped Clippy is running for codex-mcp-server, codex-app-server and
codex-tui. No unrelated product changes were made.

Normalized source delta now consists exactly of this one exhaustive-match arm and
the three existing MCP test expectation corrections; all other changes normalize
to the formatted b0ce988 baseline. The earlier format-only patch hash is retained
above. Updated full patch SHA256:
6bf54ce897901778f38c9da5a0a33e6868b6fa6d0da2bf89705fa112d6f305ac.
This is a successor source patch, not a claim that the existing86fad00 binary was
rebuilt from these bytes.

Stock-counterfactual restraint: the rejected debug-only flag sets
runtime_options.plugin_startup_tasks=PluginStartupTasks::Skip in the candidate.
Removing it would change startup semantics central to the hook fixture; therefore
no supposedly equivalent baseline verdict is inferred from silently stripping it.
The hook failure remains an explicit independent gate.

## Compatible scoped-baseline hook counterfactual

The existing332 native prefix retained sourcea50f43518c10e5cb94271dc484c97a973067311e.
Its installed app-server was freshly hashed as
73053555dc132dc34ce64fd3121f17c438eec6e4da682599a4ae751f1ecf3375,
matching the manifest. One45second-bounded control changed only the app-server
executable relative to the candidate's private HOME/private TMPDIR test. The same
historical harness and test-only startup flag were retained.

Result: baseline failed after31.47seconds with the same successful initialize and
hooks/list response followed by thread/start response deadline. There was no
unsupported-argument error. This demonstrates that the hook failure also exists
on the pinned scoped-refresh predecessor; it is not uniquely introduced by the345
patch. It does not establish the underlying baseline/runtime/fixture cause or
convert the broad suite to green. Receipt:
hooks-scoped-baseline-counterfactual.json and matching full stderr/RPC log in the
user-scoped qualification directory. No baseline build, shared daemon operation,
credential use, or additional model request was performed.

## Repair static gate: PASS

`CARGO_TARGET_DIR=OWNED_CLEAN_TARGET RUST_MIN_STACK=16777216 just clippy
-p codex-mcp-server -p codex-app-server -p codex-tui` exited0 after7m11seconds.
This includes test-target compilation. The previously missing RawResponseCompleted
arm is now covered. No additional production source edit was made. This is scoped
static acceptance, not a whole-native test-suite pass or successor binary journey.
Final formatter/source-normalization custody follows below; no behavioral tests
are rerun after the formatter under the native repository instructions.

## Final bounded packet readback

Final `just fmt` and `just fmt-check` both exited0. `git diff --check` and full
patch reverse-application check passed. Final normalized audit retained exactly
one product arm and the three MCP test expectation corrections; no additional
Clippy or formatter product edit appeared. Full patch hash remains
6bf54ce897901778f38c9da5a0a33e6868b6fa6d0da2bf89705fa112d6f305ac;
source diff relative to b0ce988 hashes
822a911b8a478f52836ebb630c1aed3fb2287b2d43e798c75d63062e295f1658.
Machine-readable final-scoped-receipt.json is retained user-scoped.

No successor app-server binary was built in this bounded packet. The qualified
86fad00 binary remains tied to b0ce988 and its existing real journey evidence.
The successor static source contains the additional MCP server compile repair;
byte-for-byte source/binary equivalence or successor runtime qualification is not
claimed. Source and evidence remain uncommitted pending primary coordination.

Remaining independent boundary: whole-native-suite acceptance is not green.
The safety failure is environment-isolated; hook timeout is reproduced on the
predecessor but its root cause remains open. A matching successor build and any
wider native-suite campaign require their own bounded scope. No CI, activation,
shared daemon/service change, provider effect or historical goal renewal occurred.
Memory disposition: forbidden; no memory write authorized.

## Qualified source checkpoint and separately authorized artifact build

Primary-authorized native source checkpoint:
98d5c6736ac66f06c62b9eaa275adb8a30baa431 on test/combined-goal-native.
Its exact patch and normalized delta are the qualified hashes above. The native
worktree is clean. A new bounded15minute artifact-build packet was explicitly
authorized, with at most2compiler jobs, an owned cache, disk-reserve check and a
new immutable private prefix. The old86fad00 prefix is not overwritten. A matching
build will establish artifact custody only; targeted scoped-refresh and real
journey acceptance remain separate and primary-coordinated. The historical goal
was not resumed and no global runtime operation was authorized.

## Matching successor artifact: BUILT, runtime acceptance pending

The explicitly authorized locked/offline build with2Cargo jobs exited0. Cargo
reported14m05s; its UTC interval was769.47seconds, so the monotonic Cargo duration
is retained for the15minute bound. Initial free disk221124284416bytes exceeded the
64GiB reserve plus32GiB projected build budget; free disk after build was
209418510336bytes. Exact command:
`cargo build --locked --offline -j 2 -p codex-app-server --bin codex-app-server`.

Matching source:98d5c6736ac66f06c62b9eaa275adb8a30baa431.
Private immutable artifact prefix:
`~/.local/share/codex-wake/native/combined-98d5c6736a-20261025T195259Z/`.
Binary:bin/codex-app-server.
SHA256:299a49c85e107d9b48c9d24155867fa659bfaa68c1f74d345033c32839826aad.
Adjacent manifest.json records source, full patch, build command and custody.
The installed private copy and built artifact hashes matched. Source was clean
before and after. Fresh owned process-group census found no remaining member of
PGID2953160. The old qualified binary was rehashed unchanged as86fad00...683b1f.

This artifact has not yet passed the targeted scoped-refresh and real-native/TUI
journey; those are primary-coordinated gates. The old86fad00 journey does not
qualify this new binary automatically. Matching artifact custody is complete;
activation, whole-native-suite acceptance and shared runtime effects remain absent.
Receipts: matching-native-build-start.json, matching-native-build-final.json and
matching-native-build.log in the existing user-scoped qualification directory.
