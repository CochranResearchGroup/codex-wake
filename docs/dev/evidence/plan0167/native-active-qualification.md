# Real native active-turn controls with localhost-injected Responses

Verdict: PASS_NATIVE_ACTIVE_INJECTED_PROVIDER (second/final allowed packet).
Installed candidate `/tmp/cw167-installed/bin/python`, product source6b4b233;
absolute Codex0.163 `/home/ecochran76/.local/bin/codex`. No product core edits.

Native app-server runs with a private empty CODEX_HOME, no auth file or provider
credentials, and only the explicitly configured localhost Responses endpoint.
Physical Unix socket owner/private parent and SO_PEERCRED exact launched PID
were verified before thread RPC. SSE event format comes from version-matched
OpenAI codex `rust-v0.163.0/codex-rs/core/tests/common/responses.rs` helpers
`ev_response_created`, `ev_assistant_message`, `ev_completed_with_tokens`.

A real blocked goal and one native turn received injected20 total tokens,
including10 cached input tokens; actual native rollout recorded that response.
Goal activated with native tokenBudget1 and next localhost response held open.
Independent installed watcher and public CLI enrollment used1000tokens/30s from
ORIGINAL goal.createdAt1792281208; fixeddeadline1792281238, default60s checkpoint
reserve. No deadline extension or fake clock. Native goal display is not used
as cached-inclusive accounting. Three local Responses POSTs occurred: initial
completion, blocked active response, and steer-triggered replacement stream.
Total wall32.626seconds, below90seconds. No external provider/model calls.

Watcher receipt proves actual native turn/steer acknowledged for exact active
turn01a14c48-ea1d-7e71-ad4b-0420df1ce921, then at originalallocationexpiry actual
thread/goal/set paused + exact turn/interrupt acknowledged. Independent native
readback has goalpaused, originalturncompleted and active turninterrupted;
controller stopped/allocation_exhausted/stop_prooftrue. Checkpoint acknowledgement
is request delivery, NOT proof that a model wrote a checkpoint artifact. Injected
provider usage is NOT billing, real provider cancellation, or delegated proof.

First packet `/tmp/cw167-native-active1/result.json` is retained FAILED_PACKET:
initialCLI enrollment returnedheld/ValueError without persisted enrollment;
exact cause not reproduced. Later authorized directpublicdiagnostic enrollment
after original30seconds was alreadyexpired, yielding realpause/interrupt but no
checkpointacknowledgement. It is not relabeled a complete pass. No third attempt.

Second raw receipt `/tmp/cw167-native-active2/result.json`; curated receipt is
native-active-receipt.json. Both own watcher/native processes exited0, generation
identities absent; fresh exact-home census empty, own alias/physicalsocket absent
(cleanup-readback.json). No shared sessions, services or daemon termination.
Local provider server was shut down. No raw provider request body is retained;
only path/count and bodyhash. Memory disposition forbidden: bounded lane permits
script/evidence only, no external memory write.
