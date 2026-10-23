# MR-04 cross-runtime A2A source and reconciliation

Work item: CW-MR-172/MR-04. Owner: primary / ecochran76.
Base36412c4; feature37f935f integrated as4407630. Shared selection4ee9c01;
Grok MCP authority correctionef8b5b4. Main integration and live acceptance separate.
State: DONE — source and isolated artifact; real TUI acceptance remains MR-06.

## Behavior and authority

Codex namespaces/actor keys, independent capability tokens, claim generations and
receipt meanings retain their existing formats. Operator `a2a enroll --thread
grok:BINDING --runtime-root ROOT` issues an independent Grok actor capability and
private frozen context sidecar. Grok namespaces are derived from the approved
executable path/digest; session IDs stay opaque and separate from Codex metadata.
A sidecar never acts as a capability. No grant or objective allowance transfers.

`messages ... --actor-runtime grok` requires that independent capability, the
operator's frozen binding digest, exact managed process/boot/start/session context,
caller process ancestry and enrolled working root. Production caller ancestry also
requires runtime-inherited GROK_SESSION_ID to match; this claim alone grants
nothing. Replaced generation, unknown context or mismatched claim refuses before
mailbox effects. Native Grok caller attestation remains not qualified. The source
implements operator delegation to one managed process, not a native provider proof.
Real inherited-context behavior must be checked in MR-06's live acceptance.

`messages send --to grok:BINDING --runtime-root ROOT` resolves exact host context
and still requires an independently enrolled recipient. Reply, explicit accepted
claim and terminal outcome reuse the existing mailbox protocol. Reading/delivery
cannot claim work; repeated accepted acknowledgments return claimed=false.

Operator `a2a bind-grok` adds a versioned Grok notification transport. Dispatch
persists the original journal claim before input and sends only a bounded pointer,
never the private message body. It revalidates current capability/lease/expiry and
runtime generation after acquiring the same user-scoped pane lock used by ordinary
Grok wakes. Original expiry and lease produce the bounded submission window.
Accepted terminal observation is explicitly separate from execution and receiver
acknowledgment. A later credentialed mailbox claim is genuine work authority.
A lost response stays uncertain across worker replacement and is never replayed.

The MCP host owns actor runtime, capability, runtime root and endpoint. Tool
arguments cannot choose those fields. A Grok host forwards its claimed session
only for comparison with frozen context and refuses native-only lifecycle/resource
or wake-control tools with native_caller_attestation_unavailable. Codex hosts retain
their existing paths. No Grok caller can select a Codex caller ID to reuse grants.

## Tests, review and retained failures

Public seams: operator enrollment, actor-scoped CLI/MCP commands, durable mailbox
claim/reply and notification dispatcher. Process/terminal adapters are deterministic
fixtures; actual bus capabilities, journal/claims and file permissions are real.
Both directions prove authenticated recipient claims before completion, correlated
replies, mismatched capability/claim refusal, non-descendant refusal and changed
process refusal. A terminal notification leaves the recipient unread until explicit
credentialed acceptance. Restart after a lost paste response performs no replay.

Independent worker `/root/mr05` reviewed authority/notification integration and
reported one concrete blocking finding: A2A and ordinary wakes lacked a shared
pane lock. Primary accepted and repaired it. A real-lock regression holds the
ordinary wake lock while a notification thread runs, requires zero paste, then
releases it and observes one submission. A lock-bypass mutation goes red on
premature paste; restored source passes. Closed-world worker readback confirms the
same key/directory, rechecks within the lock and regression evidence. No duplicate
broad review or provider probe was used.

Primary separately found the Grok MCP/native-only grant forwarding gap. The first
attempted reproducer lacked a required name and is retained as non-qualifying.
A corrected valid-input reproducer with the new guard removed fails because it
would execute; restoring the guard passes. Frozen comprehensive run1 was stopped
and retained as superseded before changing the source. It is not passing evidence.

Integrated installed controls75 PASS19.324s before the final two-line MCP guard;
final installed changed-axis controls15 PASS5.140s after that guard (plus one new
regression). Focused primary40 PASS9.295s and undefined-name lint PASS. Final wheel
and source inventories are bound in the combined machine receipt; comprehensive
result is recorded below. No live Grok/Codex conversation, production bus/grant,
service, installation, release or main ref was changed in this wave.

## Final primary reconciliation

Frozen sourceef8b5b4:1451 tests PASS in341.346s, zero errors/failures, one expected
opt-in disposable-systemd skip. Before/after source and test hashes are unchanged;
all production modules match the final non-editable wheel. The final installed
changed-axis15 checks pass5.140s, undefined-name lint and whitespace pass. Initial
worker/native environment failures and superseded full run remain retained.

MR-04 and MR-05 are DONE for source and isolated artifact. MR-06 is READY for
real visible Codex/Grok and bidirectional acceptance; no such live proof is inferred
from these fixtures. Native Grok caller attestation and Codex terminal fallback
remain not qualified, and queue/interruption explicitly refuse. No new provider
input, production grant/bus/service/installation, main merge or release occurred.
Primary accepted worker source/focused validation, inspected and repaired the
shared lock finding, and independently ran integrated/artifact/full validation.
Source packet refs are retained separately from reconciled coordinator evidence.
