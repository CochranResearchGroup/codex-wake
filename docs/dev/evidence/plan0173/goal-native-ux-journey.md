# Real native, installed Wake and stock TUI journey qualification

State: OPEN; actual native accounting compatibility is not qualified.
Worker: /root/ticket346, successor branch test/346-native-ux-acceptance.
Script: scripts/goal_limit_native_ux_acceptance.py, initially committed33f8777.
Wake package source:3c9230d; all installed package Python bytes matched that source.
Isolated prefix and receipts live outside Git under
`~/.local/state/codex-wake/goal-limit-ux/346-native-journey-20261025T045000Z/`.

## Frozen run contract

The script requires explicit installed prefix, source checkout, pinned app-server
path plus SHA256 and stock TUI path. It creates only owned private CODEX_HOME,
workspace, policy, common queue, watcher, tmux server and localhost Responses
fixture. Bound:180seconds/run, six localhost POSTs, original goal30seconds with an
explicit five-second checkpoint reserve. Credentials are removed from subprocess
environment. Shared native daemon, watcher mask and production policies stay intact.

Intended checks: nonzero original native history; verified first-poll startup and
actual stock-TUI card; active local model stream; time exhaustion with exact native
pause/interrupt and visible durable stop; reconnect renders the same notice once;
later operator reply stays usable; authenticated common-queue CLI extension retains
usage; explicit reset creates0current-window/nonzero lifetime and remains paused;
new revision/window cards render; unrelated real-native peer unchanged. Final OS
process-group census and owned process identities are retained.

## Actual observed evidence

Pinned development app-server71620df88c3267760064af171bfd66f1264dfaaf:
SHA256c4df73c2addf84762cf07c179f32993352721693936d0152f74e55a1c0cc15bc.
Stock frontend0.164.0 at the installed `codex` executable. The server physical
Unix socket was resolved and verified by SO_PEERCRED against the exact owned PID.
No intermediate build binary was used.

Attempt1 failed before any model request because the script looked for a lower-case
model label while stock TUI rendered `GPT-5.4-Mini`. The capture proves actual
attachment; the predicate was corrected. Receipt retained in attempt1/receipt.json.
Native exit0, no watcher started, final owned process census empty.

Attempt2 attached the real stock TUI and completed one localhost response through
the real app-server. Native rollout contained task_started, token_count with
20input/10cached/0output and task_complete. It contained **no token_usage_record**.
Installed Wake correctly held enrollment with accounting state unknown and reason
first_usage_unavailable. Native cumulative counters alone do not meet the existing
per-response identity/hash/descendant accounting contract. No usage rows were
synthesized and no reset/recovery was attempted to escape the hold.

Receipt: attempt2/receipt.json. The exact owned native thread is
01a17164-5df3-7a61-9c31-5a8e3897c115; its canonical rollout remains under the
attempt's private home/sessions directory. One localhost POST, zero external
provider requests; native and watcher both exit0 with absent after-identities;
final owned process census is empty.

A bounded literal search of the native source core/protocol/app-server found no
writer for token_usage_record, TokenUsageRecord or raw_response_completed. This
supports a missing development-runtime accounting capability; it is not proof of
stock-runtime equivalence or a reason to weaken accounting. The native owner is
investigating whether a supported extension/runtime writer can qualify it.

## Acceptance status

The earlier installed CLI/MCP test with injected native protocol passed and remains
valid for its stated boundary (goal-renewal-installed.md). This real-native run did
not reach startup engagement, watcher-triggered stop, real renewal or reset. Those
criteria remain unproven. The stock-TUI direct native notice acceptance owned by
#345 is separate and cannot substitute for the combined watcher/accounting journey.

Next action: qualify a real per-response writer in an explicitly pinned native
build, then rerun this unchanged journey with a fresh owned output directory.
Do not advertise the present dev-native build as enforcement-ready or close #346
from the injected protocol receipt alone. No broad review was run by this worker.
Memory disposition: forbidden; no memory write was requested.
