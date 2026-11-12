# Native governor controls · #572

The presentation preview is `preview.html` (synthetic values, no operations).
The implementation is the real Codex Rust TUI, retained as `governor-ui.patch`.
`manifest.json` binds the patch, native source base/commit and file hashes.
This is a supplemental patch over the retained native167 base, not a patch over
stock upstream. Existing native source, installed binaries and rollback packages
remain untouched.

The native `/wake` command dispatches typed local events. Operator governor actions use
fixed executable `codex-wake` with argv `governor VERB SELECTOR --json --endpoint
UNIX_ENDPOINT`; explicit mutation submissions add request IDs and an observed
revision when available. The Python owner authenticates local operator authority;
no model field grants authority. Forms are local text prompts, not model prompts.

The persistent strip displays the current task; another selected task is named
in the palette/details. Status uses the existing shared local owner over private loopback HTTP. One
pipe-only CLI bootstrap validates the same-user process and yields a credential
held only in native task memory. The HTTP client disables proxies and redirects,
bounds response size, and polls serially (completion plus three seconds when
enrolled or awaiting activation, 30 seconds when disabled/disconnected; 15-second request
timeout), with widget/thread cancellation. No per-poll Python process starts. Live governor/self-limit MCP completion
notifications and native action results invalidate the polling sleep. Transport failure
shows disconnected/accounting unknown; no zero-usage or advisory fallback.
Read-only catalog entries reuse existing wakes/tabs/sessions/accounts commands.
The target picker accepts owned Codex rows across qualified Unix daemons and
accounts. Each selected row retains its endpoint and home for explicit operator
actions; the persistent strip continues to observe the current thread.
Messaging is visibly unsupported without a qualified actor binding.
No destructive operation is exposed, so no destructive confirmation is needed.

Validation stages and immutable package qualification are recorded in
`validation.json`; private raw Cargo Signal receipts are retained outside Git.
Working-account installation, service restart and provider turns are excluded.

## Watcher-loss enforcement seam

Plan0220 also requires the app-server-owned `thread/governorLease/set` operation.
It accepts the exact thread/lease/controller/enrollment identity, a 1–10,000ms TTL,
and bounded task members with exact turn IDs and optional goal creation times.
`query` and `release` are read/disarm controls and omit TTL/members. A first
capability query does not create an allowance, guard mark, goal or turn. An
unsupported scope returns `supported:false` before strict engagement.

The native owner binds the actual internal goal ID and exact causal turn roots.
Core propagates scoped cancellation tokens through native parent lineage and
causal roots before provider work. Existing tasks receive an exact-turn monitor;
automatic goal continuations carry the same guard. A fresh operator causal root
is independent. This closes the child-spawn gap between Python watcher polls.
Python remains the accounting/allowance owner; the native lease counts no usage.
Yielded unified-exec commands retain their actual causal root in the existing
process store. Expiry confirms termination of those exact handles, including
commands started before enrollment and late child commands. Per-root admission
fences publication of in-flight starts; abandoned or ambiguous starts keep stop
verification false. All scoped tool termination shares one five-second window.

Linux `CLOCK_BOOTTIME` includes suspend time. The native timer checks it at an
awake interval of at most 100ms and rejects expired renewal. This is not a claim
of a universal OS scheduling or external-provider cancellation latency bound.
Expiry latches until a newer enrollment revision; release never resumes work.
`armed`, `expired` and `stopVerified` are separate proof fields.
Release verification is a separate boundary: an in-flight expiry may still be
finishing an exact-goal pause. `releaseVerified` remains false until that work
drains; a disarmed timer alone is not proof that a later pause cannot arrive.

Private, atomic guard and membership/goal records live under the native
`CODEX_HOME/governor-leases` directory. They contain IDs, not transcript bodies.
Cold resume consults the scoped records before Core creates the runtime, pauses
only an exact matching retained goal and holds owned automatic recovery across a
native server restart. Active goal-less work is supported without creating a goal.
Idle goal-less future-task isolation and legacy V1 delegation are explicitly
unsupported. Windows/SSH qualification remains outside this delivery.

An explicit resume can use `guardedStart` on the same lease operation. Its
request ID is reserved in a private durable journal before Core starts the turn;
the new causal root receives its lease before provider work. Queries expose the
reserved/started/uncertain state and exact started turn ID without replaying the
request. This resumes stopped goal-less work without creating a hidden goal.

Both patches are retained: `governor-ui.patch` applies to the preserved native167
base; `full-native-0167.patch` reconstructs the complete native source from the
upstream revision in the manifest. Only disposable qualification may run the new
package; working-account installation and restart are separate gates.

Package-v3 (`bd519d5232aef6f55a4a665cd0c7461ec5b223f9`, entrypoint `1171e7f63ae255426738c5d1a2e44250d322031f7758b13426082be4615706aa`) additionally pauses the exact captured blocked goal. The zero-POST actual RPC probe `/tmp/p220blocked2/receipt.json` passed in 2.502s: captured goal paused, peer preserved, no task started, owned native cleaned up. Full managed UI/cold-resume acceptance remains pending; all prior packages/failures retained.

Managed UI v3 reached reset successfully. `/tmp/p220u7/receipt.json` then captured the 15-second native CLI timeout during explicit extend-and-resume (request `287fd2ba-19eb-42e3-b51c-f87921fa11cb`), after the allowance update but before any continuation inference. This remains an open acceptance failure; one warmup local POST, zero external provider calls, empty owned process census. The native artifact is unchanged.

The resume timeout above is resolved by Wake fix `a3dcde29`: explicit resume was reacquiring its already-held shared allocation lock. The installed updated wheel (`7a5c5e6c...`) with unchanged native `1171e7f6...` passed the complete managed UI, active watcher-loss and cold-resume journey in65.462s, three localhost fixture POSTs, zero external calls and empty final owned census. See `ui-acceptance-20261112.json` and `resume-timeout-diagnosis.json` for exact provenance and retained red attempts. Reconnect acceptance now explicitly selects the existing native **Leave paused** choice before sending controls. Aggregate #574 qualification remains separate.

Current review remediation: native source `15626ed7031a0246543b1703be69dbbc22e917d2` fixes effective remaining tokens and displays the limiting scope plus shared allowance details. Six focused governor rendering/command tests passed after the retained red cases. Complete immutable package-v4 entrypoint is `ca29d5cf77402cdc0a6fd71ddaf3b7365fb44250da96b42ffa58d94de83f7402`; all six package members are recorded in `validation.json`. Exact UID1017 managed UI, watcher loss and cold resume passed in64.475s with three localhost requests, zero external calls and empty final owned census. Actual captures show shared allowance/token/time details and the limiting task label. See `ui-v4-acceptance.json` and `remediation.json`; prior v3 evidence and failed v4 setup attempts remain historical evidence. Primary aggregate upgrade/failure/delegated qualification and final cleanup remain separate gates.
