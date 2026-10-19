# Issue289 restart-safe handoff

Current checkpoint: 2026-10-19, Plan0169v18. This replaces the obsolete startup
instructions preserved in Git at a710405. Issue289 remains OPEN.

## Start here

1. Read Plan0169 Current State, ADR0002 and RUNBOOK Turn373. Inspect
   `installed-native-controls-0.18.6.json` beside this handoff.
2. Check Git status/HEAD in the allocation-control worktree and fetch origin.
   Reconcile the documentation PR before editing. Preserve the separate main
   checkout and unrelated work. Source release is main a710405107feb0baeeec978d78ac6c8b9d7d90ec.
3. Read current private controller, parent receipt and allocation; compare their
   identities, latch, deadline and cumulative fresh charges with the evidence.
   MCP calls use the actual invoking UUID, never a claimed parent identity.
4. Continue only authorized operator diagnosis. The user explicitly requires
   the parent timeout latch retained. Campaign remains paused; source delivery
   and successful tests do not authorize clearing it or renewing resources.

## Authority and resource state

The parent native thread is 01a14f45-25a2-7ef1-bcce-1205f176cc73. Its allocation
is issue289-renewal-5a0f1b65a081423fa6cbd3fa3c5a3981: 2M fresh input+output,
cache excluded, immutable deadline 2026-10-20T03:55:35.869783Z. At installed
readback it used 755,885 fresh; refresh that value. Native goal remains paused.
Stop reason observation_unavailable/TimeoutError is a qualification failure,
not quota exhaustion. Preserve its latch, generation, response history and clock.

Private policy: ~/.config/codex-wake/goal-limits.json. Private state root:
~/.local/state/codex-wake/goal-limits. Parent receipt basename:
2b7b05f803a4519e764916ab6e93f3003389faa62df0db3892c57aadf848561c.json.
Parent allocation basename:f7f183830d2363232e4b4da3925cfaa13ea5c5c4f7ae40f52841e5d3146bf5f5.json.
Host-wide self_enrollment ceiling is enabled; named/legacy grants remain,
with no default allocation attaching unrelated conversations to this campaign.

## Delivered and verified

PR294 first native allocation creation, PR295 immutable renewal partition and
transfer-aware peers, PR296 bounded native observation are merged. Required
Python 3.11 / 3.12 CI passed their exact PR heads. 0.18.6 release includes all fixes.
Installed prefix: ~/.local/share/codex-wake/releases/0.18.6-a710405.112modules
match source; five stable links and both real skill directories adopted.
Goal controller PID 91299 was fresh at readback. Re-observe current PID/prefix.
Shared native daemon 9802/start 10894 was preserved throughout; it must remain.
New isolated stdio initialization verifies MCP 0.18.6. Existing native client
connections were not refreshed by this evidence.

The one permitted native-control fixture passed in 31.853 seconds with 4 localhost
Responses requests, 0 external provider calls. Actual native checkpoint steer,
quota interrupt/pause and an operator turn completing while paused are proven.
Usage was injected, so this is control evidence, not billing evidence. Owned
native 94844 and watcher 95019 exited; fresh process census found no remaining
owned matches. Full receipts: /tmp/cw289-native0186-control-fixture/result.json
and cleanup-readback.json. No rerun is needed for this source.

Original real demo at /tmp/codex-wake-native-0184-demo-26srmszp created a stable
allocation without per-session provisioning, but setup had already consumed
39,194 fresh against 12,000. Admission held; quota pause/operator reply proven.
Raw dedup 41,754 fresh matches Wake. Its exhausted latch remains; its client exited.
This does not prove below-cap armed admission or an agent-written checkpoint.

## Remaining gates and next bounded packet

Preserve both live latches and the fixed deadline. A new real acceptance campaign
requires an explicitly qualified allowance; keep it distinct from resetting the
exhausted demo. Original early-stop accounting replay remains open. The exact
historical native timeout RPC is unknown; future failures now retain method/cause.
Do not infer that avoiding 4.9 MB history hydration eliminates all timeout causes.

Current bounded packet ends with installed native-control acceptance and this
handoff. Further campaign activation is outside the explicit latch-preservation
instruction. Existing expired shared-refresh intents remain expired. The owned
qualification completion wake was cancelled after its result was inspected;
no campaign continuation is armed. Documentation-only CI may finish publishing
this checkpoint.

Memory disposition: forbidden, no reviewed destination routing. Private no-write
receipt and operational checkpoint: /tmp/cw289-native0186-control-run/.
