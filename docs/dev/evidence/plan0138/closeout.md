# Plan0138 completion audit — 2026-10-10

State transition RELEASE_PREPARATION→COMPLETE; acceptance_state ACCEPTED;
progress_classification outcome_progress. No material blocker remains for the
approved saved-recipient scope. Wider Plan0101/0119 remain OPEN.

| Criterion | Observed evidence |
| --- | --- |
| Original saved native conversation completes after its initiating turn ends | native-acceptance.md; exact original native wake/thread/turn, preserved seed |
| Default closed-recipient messages wait | installed-exchange-checkpoint.md; original default control deferred offline without a dispatch |
| Explicit choice persists with original authority across restart | message-authority-checkpoint.md, installed-exchange-checkpoint.md; original message ID/digest/actor generations/root survive owned worker restart and old-reader paused rollback |
| Only original saved recipient reopens and completes | installed-acceptance.md; native_saved_recipient_v1, original recipient seed/history and completed request turn |
| Unattended request/reply completes in both original conversations | installed-acceptance.md; one request dispatch, one correlated reply dispatch, completed recipient and sender turns; exact result body |
| Busy/draft/changed/unavailable/cancel/expiry/uncertainty safeguards retained | source-review.md, final-review.md and installed focused95 controls; no automatic ambiguous resend |
| Serial Standards and Spec review | final-review.md; no blocking findings, two baseline limitations explicitly retained |
| Owned cleanup and preserved unrelated sessions | cleanup.md; both test panes absent and owned process readback clear; original histories and failed receipts retained |
| Source/release/installed identity | activation.json and release asset/parity readbacks below |
| Integration and checkout custody | PR232 merge79c8c29; source0842532 retained on matching remote branch; clean feature worktree removed normally |

Source/integration/tag commit:79c8c29185c48e3d01eb125a91284f4373cdf999.
PR:https://github.com/CochranResearchGroup/codex-wake/pull/232.
Release:https://github.com/CochranResearchGroup/codex-wake/releases/tag/v0.11.0.
Immutable installation:~/.local/share/codex-wake/releases/0.11.0-79c8c29.

Downloaded released assets match build artifacts:

- codex_wake-0.11.0-py3-none-any.whl:
  8372f1468c6cb760a7a52fd16b99eb664d05ec3edaf77d0f10db497092f3690b
- codex_wake-0.11.0.tar.gz:
  0774a6572777dff7ee44d794bb6db3188167f7eb7ff9b8b858eab76d4deb7ca1

All80 package files were compared byte-for-byte across tracked merged source,
wheel, sdist, final installation and the installed acceptance candidate. Private
release-parity.json retains individual SHA256 values. The byte-identical candidate
passed focused installed95tests49.942s; no redundant comprehensive-suite pass is
claimed. Final CLI version0.11.0 and public send/reply --resume-missing help were
read back after activation. Four global CLI links now resolve to the release
prefix. All13 service PID/state snapshots match before/after, including LitScout
PID24465 and ordinary global supervisor48816. Existing running workers retain
their old immutable prefixes; no unrelated restart or Codex daemon patch occurred.
HostedCI waiting was waived by the user; no hostedCI result is acceptance evidence.

Retained limitations: the sender reported the result but terminal ack failed
claim_required; reply state is received, not completed. Public tab-close inventory
reported inventory_unavailable; explicit owned idle-pane cleanup used public force
and retained its warning. Neither failed sample was erased, manually completed or
resent. Further consumption/inventory repair belongs to a separately bounded
follow-up, not a false claim that the wider A2A program is complete.

Source branch feat/saved-recipient-reopening remains published at
0842532e3bbfa14f6cabf304844fd27f39c991a0. Fresh /proc CWD inspection found no
owner of its checkout before normal removal; post-removal worktree inventory
contains root main and the older plan127 checkout. The latter retains live CWD
owners and was preserved. Private runtime receipts remain under
~/.local/state/codex-wake/plan0138 with restrictive permissions.

Memory disposition: unavailable — no reviewed Codex Wake Graphiti group is
available for this durable source-anchored result. Machine-readable non-write
receipt retained privately; no memory-folder or Graphiti write attempted.
