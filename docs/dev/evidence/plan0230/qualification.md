# LOCAL-P230 source qualification

Base: e8c79a79da0b0482e2403e634394c70f5c66e333.
Branch: fix/notification-binding-lifecycle. Reviewed source candidate; not activated.
Primary-owned isolated worktree retained for source review and custody. The main
checkout and other 120 registered checkout records were not changed or cleaned.

## Root cause and red evidence

The public host-delegated send path provisioned only its caller. The previous
question/reply test explicitly polled the recipient before sending, masking the
first-contact order dependency. Removing that prerequisite reproduced the original
error: authorization_denied, recipient has no matching active enrollment capability.
One focused regression completed in 0.398s and failed before the source fix.

A separate dispatcher regression omitted the intended recipient binding while
retaining an unrelated binding. The original worker submitted zero notifications
and deferred with capability_unavailable (0.219s). The existing binding registry
was a static per-client projection, not maintained for newly contacted sessions.

## Source repair

Host delegation now provisions the verified recipient at exact send admission,
including pinned informal routes. It retains revocation, receive denial, enrolled
root and cross-root restrictions. Fixed-actor launches remain explicit.

The worker/dispatch option --discover-tmux-socket enables exact pending-recipient
discovery and replacement-client rebinding. It checks original notification
authority before binding, retains live native identity, ambiguity and composer
checks, preserves non-tmux bindings, and does not retry uncertain effects.
Explicit mode remains unchanged. Tmux writers merge under a bounded private lock.
A missing initial binding file is allowed only in discovery mode.

## Local validation

Interpreter: existing 0.22.0.dev13-34b7362 release Python3.12 dependency environment;
PYTHONPATH points at this source. Initial system-Python attempt lacked websockets;
that was an environment error, not red bug evidence. No dependency install needed.

PYTHONPATH=src:tests <python> -m unittest test_native_mailbox_bootstrap
 test_a2a_delivery test_a2a_tmux_delivery test_a2a_scheduler
 test_a2a_scheduler_faults test_a2a_cli test_messages_cli

63 PASS / 19.411s at the first qualification boundary. After adding cross-root
coverage and caching each newly resolved binding during a dispatch tick:

PYTHONPATH=src:tests <python> -m unittest test_native_mailbox_bootstrap test_a2a_delivery

25 PASS / 9.627s. All changed branches pass; the combined distinct selection now
contains 64 tests (the other 39 remained unchanged).

PYTHONPATH=src:tests <python> -m unittest test_a2a_mcp test_tab_targets_mcp
 test_tab_targets test_a2a_mailbox test_a2a_mailbox_faults

50 PASS / 17.456s. Total distinct selection: 114 tests. Regressions cover initial
contact, revoked and unenrolled peers, denied cross-root/receive, missing bindings,
replacement generation, wrong namespace, explicit-mode preservation and existing
busy/draft/uncertain delivery behavior. Native runtime observations are injected
in source tests; real private socket mailbox delivery is exercised by the existing
harness. These results are not working-host activation or fresh native-live proof.

Public source CLI worker help exposes the discovery option. Policy wiring PASS;
active goal planning audit PASS; git diff --check PASS. No hosted CI or full suite.
Compared with hosted validation: one local Python3.12 environment, focused selection,
no Python3.11 matrix, no wheel installation or entire product/legacy-smoke suite.

## Operational boundary and follow-up

Prior live diagnostic proved manually bound WebB notification/read/claim/completion.
It did not qualify these new source changes. No installed worker/MCP/daemon was
replaced, and no shared service configuration was changed in this source slice.
Review, explicit commit/integration and qualified host activation remain outstanding.
The intermittent earlier composer_protected event was not reproduced; this repair
does not relax that safeguard or claim its historical cause.

No temporary logging or raw transcript fixtures added. Memory disposition forbidden:
no external memory write authorized for this source slice; evidence stays here.

## Continuation: review and installed candidate

Operator continued source delivery. Serial Standards/Spec review against the same
base: Standards 0 accepted, Spec 1 accepted/resolved. See review.md. A regression
first reproduced SharedSourceError escaping the dispatcher; it now defers as
runtime_unavailable, preserving the original pending intent and avoiding saved
recipient reopening on unavailable native evidence.

Candidate version 0.22.0.dev15. Wheel SHA256:
0aaa823ec71210f33d8112f4c9c7f71dc711961b78404501c21d504f54c8a57d.
All 324 packaged payload files equal source. Dependencies constrained to the
existing dev13 qualification environment; no dependency upgrade. Installed into
an unused immutable candidate prefix; active entrypoints and services unchanged.

The combined twelve-module selection above, now including the new source-failure
regression, passed 115 tests/65.018s from source. The same 115 tests passed against
the exact installed candidate with PYTHONPATH=tests (no src override), 50.126s.
Installed source_registry_smoke passed, removed its temporary root, and created
no wake root/journal. Source CLI exposes opt-in discovery. These are focused
qualification results, not the full suite or real native-session acceptance.

Installed `scripts/a2a_mailbox_smoke.py --scheduler --operations --cli <candidate>`
FAILED at retention preview with clock_anomaly: clock continuity is uncertain;
no effect authorized. Initial failure is retained; no blind retry, clock-checkpoint
reset, guard relaxation, live bus mutation or host clock change performed.

A fresh 60-sample/6-second host clock probe measured wall-minus-monotonic step
minimum -5.6768345685559325s and maximum +5.173025323834736s. Workstation is WSL2,
current kernel clocksource tsc. This demonstrates an ambient clock-continuity
failure, not a passing release gate. No claim is made about its ultimate host cause.

Working-host activation and full installed-smoke qualification are BLOCKED until
host clock continuity is restored and the original smoke passes. Draft source
publication is permitted; do not call the candidate runtime-qualified or merge-ready.
No daemon replacement, active MCP reload or notification worker restart occurred.

## StableTime operator correction and final candidate

The operator directed StableTime use instead of host-clock modification. Both the
StableTime MCP and the installed Wake adapter returned finite, NTS-verified bounds
from Cloudflare and Netnod. The production bus readback was already schema3 /
network-first with the existing provider-selection adapter; the failing smoke had
created a fresh schema2 legacy-guest bus. Conflating those boundaries caused the
incorrect host-clock proposal. No clocksource switch was performed.

Added explicit --require-stable-time activation through the existing time-policy
seam and --stable-time to the same installed smoke. The new persisted provider pin
rejects plain sources or missing/uncertain StableTime, prevents downgrade, retains
legacy checkpoints and refuses pending legacy-work migration. Older readers reject
this policy. The existing production policy was not migrated or changed.

A closed-world regression also exposed an existing in-memory Mailbox instance not
observing a newly activated pin. It went red (no BusError), then green after checking
policy inside BEGIN IMMEDIATE. No earlier fixture or failing result was discarded.

Final immutable candidate version 0.22.0.dev16 (r2 qualification prefix). Wheel SHA256:
bf192632cf31b05b67670ad8287063541dd6a79231e5fb73ac813d1b3a62eeaa.
All324 wheel payload files equal source. Installed qualification, PYTHONPATH=tests:

<python> -m unittest test_network_mailbox test_stable_time test_host_counter
 test_time_provider test_a2a_delivery test_native_mailbox_bootstrap
 test_a2a_tmux_delivery test_a2a_scheduler test_a2a_scheduler_faults test_a2a_cli
 test_messages_cli test_a2a_mcp test_tab_targets_mcp test_tab_targets
 test_a2a_mailbox test_a2a_mailbox_faults

163 PASS /102.398s. Focused, not comprehensive. The initial candidate passed162
but did not yet cover the stale-instance pin finding; final163 includes that repair.
The installed original mailbox workflow with --stable-time --scheduler --operations
PASS:2requests,1reply,2received receipts,1scheduler projection, operator operations,
22connections closed, zero runtime effect methods, zero introduced child residue,
temporary bus/roots removed. Actual service supplies time; native identity metadata
is injected as in the existing smoke, not claimed as fresh native-live acceptance.

The legacy-guest failure remains historical evidence. It no longer requires a host
clock fix: operator-selected authenticated-time qualification passes. Future host
activation can preserve the current compatible network-time policy; applying the
stronger pin requires upgraded readers and a quiescent domain. No production bus
migration, shared-MCP reload or host clock change occurred in this qualification.
