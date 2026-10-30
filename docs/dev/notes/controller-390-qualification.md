# Controller390 native TUI loop qualification

Authority: [ticket390](https://github.com/CochranResearchGroup/codex-wake/issues/390),
[spec393](https://github.com/CochranResearchGroup/codex-wake/issues/393), and
[plan0190](../plans/0190-2026-10-29-cross-host-controller-specification.md).
This is implementation/qualification evidence, not a replacement plan.

The private Linux GNU package passed actual installed CLI, direct OAuth API,
OAuth MCP, host-mapped native MCP, and OAuth remote CLI checks. No production
package was activated and no shared native process was restarted. Machine
provenance and receipt hashes are in [the qualification receipt](controller-390-qualification.json).

## Native ownership and acknowledgement

The cumulative [native patch](../../../patches/codex/modern-0.164-tui-health.patch)
applies to official `rust-v0.164.0` base
`6aaac694803004a63c6f393d153c96d22521a6b9`, includes the previous modern Wake
patch, and reproduces native source tree
`7cdb7769fc5f1a207263a5c763daaffbf534f9e6` exactly. Local isolated native branch
`feat/wake-tui-health-390` commits through
`95cd89dd5f3cddeb241a9de75a3cc255a9484606` provide source provenance. It was not
pushed to OpenAI's upstream repository; the complete reconstructible source
change is published through Wake's existing patch owner.

`tui/health/register` binds an actual native connection to its kernel-observed
local peer PID, Linux process birth/boot, authoritative native server account
home, provider, logical backend, channel, and fresh connection generation.
`tui/health/describe` exposes registration metadata only. It is never positive
health evidence. The TUI uses the daemon's existing `codexHome` metadata rather
than confusing it with client-local preferences. The daemon independently
checks its owning home and kernel peer identity.

`tui/health/probe` sends `tui/health/challenge` on that existing native connection.
Only the foreground `App.handle_server_request_event` path acknowledges it,
before approval/input/history/repaint handling. It checks the displayed
conversation, controlling backend/view, account/provider, connection generation,
and expiry. The acknowledgement reports the actual Linux OS TID using
`/proc/thread-self`. Exec mode explicitly refuses this TUI-only request. No new
Bots bus or generic MCP plugin can provide positive evidence.

The Wake owner checks a fixed private host binding, live process birth/boot,
executable SHA256, exact response identity, fresh challenge, absolute monotonic
deadline, and that the returned OS TID belongs to the expected process. Native
decimal-string start ticks are compared exactly with the existing integer
process sample; changed/ambiguous identity still fails closed. Only the existing
explicit owned Unix endpoint is used. Bare `unix://` cannot discover or spawn a
server. Disconnect, missing capability, mismatch, stale/expired response, or
capacity exhaustion produces nonpositive `unknown`/`unsupported` evidence.
Observation grants neither recovery nor input/control authority.

Bounds: eight concurrent Wake observers; 64 cached image hashes; private registry
at most1MiB/256 bindings; qualified health body at most16KiB; native registration
at most256 connections; eight queued-or-expired challenges per connection;
64 challenges per30-second replay/rate window;50..5000ms native deadline.
Expired callbacks are removed while bounded tombstones remain until the exact
origin drains them or disconnects. Health never enters native approval/input
replay queues, and a full outgoing channel refuses it immediately.

The common protected operation uses exact flattened string grant dimensions,
including `process_pid`, `process_start_ticks`, `process_boot_id`, backend,
channel, and connection generation. OAuth callers cannot supply trusted actor
identity or select endpoint/configuration paths. Native MCP uses the fixed
host-approved service grant through the same protected gate. Local CLI access
is the explicit host operator surface; OAuth remote CLI exercises service-client
admission.

## Actual package and installed evidence

The upstream package owner staged the complete package at
`/tmp/health390-native-package`, including CLI, helper, verified rg and bwrap.
The supported checksum-pinned OpenAI V8 artifact resolver was used; the initial
upstream default rusty_v8 URL404 remains recorded. Rust1.99.1, jobs2, owned
`/tmp/codex-native-390-build`, normal dev binaries and owner `--strip all` were
used. No shared cache was deleted. The package manifest records every artifact
hash in [the patch manifest](../../../patches/codex/modern-0.164-tui-health-manifest.json).

The disposable Wake wheel was built from combined base `c20132a` plus the owned
health admission correction `31fbb81`. Runtime imports came from
`/tmp/health390-installed-venv/lib/python3.12/site-packages`; observed source file
hashes are retained in the receipt. The frozen-source protocol suite passed317
with one ignored export writer; the routing/bound core passed three focused
checks. Seven final focused Wake health/admission tests passed.

Core receipt `/tmp/health390-core-ui-5/receipt.json` proves actual UI PID3863285,
actual `codex-main` OS TID3863306 and a0.327638-second acknowledgement.
`PTRACE_SEIZE` plus `PTRACE_INTERRUPT` stopped only that TID: its state was`t`,
all other UI tasks remained`S`, and background daemon diagnostics RPC still
answered. Health returned`unknown`; after detach, a new challenge acknowledged
on the same TID. This is an actual native package/UI result, not a fake observer
closure, RustThreadId, transport ping, notice delivery or queue acknowledgement.

Expanded receipt `/tmp/health390-expanded-ui-3/receipt.json` proves:

- Five public frontdoors returned five distinct fresh native acknowledgements.
- A host-only broad grant received403`insufficient_scope`; revoked access received401.
- A typed synthetic private draft and cursor position remained unchanged.
- Native history/turns and the current conversation's native queued item remained unchanged during health.
- A real TUI-owned `!` shell task remained active with the same process identity.
- Nine stalled-loop observations were nonpositive; native queue overflow was explicitly refused.
- Old/duplicate challenge, wrong conversation/backend/account/provider/process/boot/channel/generation, and an unrelated registering process were refused.
- Late frames were not reused as fresh acknowledgement; post-resume challenge succeeded.

The source-shaped synthetic SessionMeta is initial fixture data. Initial native
UI resume attaches that fixture before any health probe; no health operation
resumes a conversation, appends a notice, creates a model turn or executes a
command. The expanded fixture's shell task is explicit setup, not the probe.
Because native enqueue auto-wakes an idle loaded thread, the fixture first holds
its own provider-free native shell task, then enqueues while native status is
active. It deletes only its queued sentinel before explicitly ending that task,
so the sentinel never becomes a provider turn. Normal work timer rendering is
allowed; the draft text and cursor are compared separately.

The clean child homes contained no provider credentials. Five native startup
CONNECT attempts to GitHub/ChatGPT metadata endpoints were denied by the local
503 trap before TLS. They are retained rather than reported as zero. Health
added zero requests and created zero provider/model turns. Fresh OS readback
found zero remaining owned native/helper/MCP/shell fixture processes.

Executed expanded command:

```sh
env -u PYTHONPATH /tmp/health390-installed-venv/bin/python \
  /tmp/codex-wake-health390-installed/scripts/controller_health_native_acceptance.py \
  --codex /tmp/health390-native-package/bin/codex \
  --models /tmp/codex-native-390/codex-rs/models-manager/models.json \
  --artifacts /tmp/health390-expanded-ui-3 \
  --wake-cli /tmp/health390-installed-venv/bin/codex-wake
```

The driver refuses to overwrite artifact directories; a repeat needs a fresh
fixture path. `--core-only` runs just the native positive/stall/fresh-answer gate.
The installed candidate requires the repository MCP extra and fixture
`pyte==0.8.2`. Real provider/model services and credentials are never required.

Failed setup and harness logs remain outside Git: empty/unmaterialized session
discovery, the decimal process-generation admission correction, attempted
resume before a materialized rollout existed, fixture shell quoting, and the
standard OAuth denial-envelope expectation. Their exact locators/hashes are in
the machine receipt. No failure was erased or converted into a passing claim.

## Limits

This qualification is Linux x86_64 GNU through the host-local existing Unix
native channel. Windows/macOS process/peer fields are explicitly unsupported;
network-only native WebSocket identity is unsupported. No real Windows, macOS,
WSL, production deployment or Bots consumer compatibility matrix is claimed.
The broader consumer/platform matrix remains ticket405. Loop health does not
prove input custody, readiness to accept a prompt, recovery permission or work
completion.
