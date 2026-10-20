# Issue289 restart-safe handoff

Current checkpoint: gap closure, Plan0169v19. Product acceptance is complete;
verify the closeout PR/issue readback before reporting tracker closure.
Earlier installed-control evidence is supplemented by evidence-gap-closure.json.

## Start here

1. Read Plan0169 Current State, ADR0002 and RUNBOOK Turn374. Inspect
   `evidence-gap-closure.json` and `installed-native-controls-0.18.6.json` beside this handoff.
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

## Acceptance gaps closed

One fresh real native agent enrolled100000fresh/180seconds without a per-session
grant. Actual native MCP0.18.6 reported armed33579fresh and a fresh watcher.
At49443fresh the watcher delivered the checkpoint steer; the agent stopped
verification, wrote checkpoint.md and paused its goal. REAL_DEMO_CHAT_OK completed
while paused. Final independent raw replay53313fresh matches Wake. Deadline and
generation stayed unchanged; client16792 exited. The separate installed localhost
fixture proves forced interruption; this real run proves cooperative winddown.

Historical replay independently validates raw usage arithmetic and payload hashes
for245charged responses at the false stop and345at repair. The retained stopped snapshot was608090fresh
with1391910tokens and6638.823seconds remaining; repair was1006497fresh. The cause
was native blocked-state misclassification in0.18.0, fixed by explicit known-state
classification. Cache was excluded in both snapshots. No live repair was repeated.

Both independent review axes accept closure of these evidence gaps. Durable private
raw evidence is under ~/.local/state/codex-wake/acceptance/issue289-0186-gap-closure;
the public curated artifact is evidence-gap-closure.json. Earlier /tmp locators are
retained as history, with this durable copy available after restart.

## Retained boundaries

Parent and exhausted-demo latches remain set. The parent allowance's fixed deadline
is unchanged. Product acceptance does not authorize campaign reactivation or reset.

The historical timeout's exact RPC is unrecoverable: the old receipt recorded only
TimeoutError and the retained native log has no correlated method. This remains an
explicit forensic limit. Current bounded reads and method/cause diagnostics are
verified; retrospective certainty is not claimed.

A fresh real native catalog proves installed activation. Existing connection refresh
and global reload behavior remain Plan0168/issue282 scope; this closeout does not
claim they completed. The expired refresh intents remain expired.

After closeout documentation merges and issue289 closure is read back, this lane is
complete. Future work follows a new explicit task; no campaign continuation is armed.
Memory disposition: forbidden, no reviewed destination routing. Private receipt is
under the acceptance evidence directory.
