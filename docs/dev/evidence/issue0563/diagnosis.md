# Stable tab operation identities — #563

Existing installed probes went red on title-only updates: reorder rejected a
valid plan; relocation held with unchanged pane/PID roster. Hypotheses were raw
pane metadata fingerprints (prediction: strip only observation hints), changing
ordering criteria (prediction: relevant trait changes still refuse), and native
layout/process changes (prediction: unchanged births/layout should move safely).
The first was confirmed; the other two remain enforced as negative controls.

Public seams and vertical evidence:
1. Real tmux trait-grouping preview/apply/undo: title-only change red, then green.
2. Real multi-pane transfer and undo: title red/held and undo red/skipped, then
   green. Expanded original scenario changes real cwd and foreground command
   using only a private POSIX shell; roots/panes survive. Lost-reply regression
   changes a title after the actual move and still reconciles without resending.
3. Real populated session deletion with a native title update on every adapter
   snapshot: red partial/uncertain/stale_target, then green through ordinary
   lifecycle dispatch, preserving peer processes.

The small tab_identity module omits only pane_title, pane_current_path and
pane_current_command from comparison copies. Unknown fields, births, bindings,
TTYS, window roster/names/index/focus, pins and selected ordering facts remain.
Original snapshots/fingerprints are retained; plan fingerprint integrity checked
before semantic comparison. Legacy full-pane receipts are normalized only while
comparing, never rewritten. Uncertain effects remain non-replayable.

Lifecycle gets a stable pin, exposed as lifecycle_target in public inventory.
The original target remains strict for input/capture; the lifecycle owner accepts
fresh old-style full pins too. Populated deletion uses lifecycle_target. Source
regressions prove unchanged strict target changes on title updates while stable
pin persists, and a respawned process still refuses before close. Reorder activity
changes and process replacement still refuse. No agent/provider/live layout work.

Commands/logs are adjacent. First red results preserved. 117affected checks PASS
on Python3.11/3.12 (49.685s/49.770s), new negative guard PASSboth;32guard/routing/
delete tests PASS3.12 in23.109s. Additional callers and exact installed qualification
pending. Each focused command has180second budget, no retries. HostedCIzero.

No broad redesign of input authority or terminal backends. Saved-group placement
semantics are a pending independent operator choice, not needed to repair these
reproduced failures. Source and installed acceptance remain separate boundaries.
