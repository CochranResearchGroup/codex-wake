# Runtime delivery contract, version 1

Authority: [Plan0172](../0172-2026-10-22-multi-runtime-wake.md),
[MR-02](0002-2026-10-22-codex-runtime-seam.md).

`RuntimeAdapter` is a built-in, injected Python interface. It is not a plugin
loader or a new command. The public `dispatch_firing_record` caller selects the
existing Codex adapter by default; the schema6 native-intent path forwards the
same dependency through its trusted-clock and lifecycle gates.

| Operation | Responsibility | Result |
| --- | --- | --- |
| `resolve(target)` | Interpret runtime-specific binding without changing identity | `RuntimeRecipient(runtime, session_id, binding, version=1)` |
| `observe(recipient)` | Read current readiness; perform only explicitly authorized same-thread resume | `RuntimeObservation(state, reason, capabilities, resumed)` |
| `submit(recipient, prompt)` | Deliver once and interpret runtime acceptance evidence | `RuntimeSubmission(state, receipt_id, evidence_kind, …)` |
| `reconcile(recipient, prompt)` | Observe the original effect without replay | `RuntimeReconciliation(evidence, reason)` |

The core owns lifecycle locks, cancellation admission, trusted-clock gates,
expiry, scheduling/retry timestamps, submission UUID, exact prompt hash, durable
attempt count and the uncertain write before delivery. The adapter owns Codex
thread status/resume protocol, queue CLI/environment, exact receipt parsing,
bounded queue/turn evidence lookup and sanitized subprocess diagnostics. A lost
response stays uncertain. Neither a restart nor an observation failure permits
another delivery attempt. `not_sent` is conservative uncertainty in this initial
Codex core; it grants no retry authority.

Version 1 is an in-memory envelope. The opaque binding is excluded from its
representation and observation projection; the Codex implementation copies its
binding into a read-only mapping. Only runtime/session identity, readiness,
reason and capability states appear in additive `runtime_observation` metadata.
No endpoint, executable path, prompt body or raw subprocess output is added to
that projection.

Capabilities distinguish `supported`, `unsupported`, `not_qualified` and
`unavailable`. Current readiness is independent: a supported delivery method can
have an unavailable or busy recipient. Busy Codex recipients wait; enqueueing
behind an active turn has not qualified dequeue-deadline enforcement. Interrupt,
terminal input and authenticated receiver acknowledgment are not implied by
queue acceptance. Explicit same-thread resume preserves exact identity.

There is no persisted record schema bump or migration in MR-02. Existing native
records keep their Codex meaning and existing transports retain their own paths.
Omitted `runtime` means Codex on the existing native target. The legacy
`native_evidence` entrypoint still accepts its historical endpoint/executable/
thread context without a transport field; it supplies native transport before
calling the adapter. This compatibility normalization is not a new durable
record reader. An explicit unknown
runtime, unknown envelope version, changed resolved identity, unknown thread
status or failed observation holds before submission without consuming an
attempt. Existing record classification continues to hold unknown/malformed
record versions and transports; this seam does not reinterpret them.

The initial core admits only the existing Codex native target and version1
recipient. Acceptance requires a valid UUID and `native_queue_acceptance`.
Reconciliation requires native queue or turn identities and execution evidence.
Terminal observation cannot be promoted to native acceptance, execution or a
receiver acknowledgment. MR-03 must add a Grok target and its distinct evidence
meaning, classify/version any new durable shape against its integration base,
and preserve these controls. MR-04 owns authenticated cross-runtime exchanges;
MR-05 owns selectable busy modes and broader terminal qualification.

MR-02 qualifies source behavior through public dispatcher/record tests and the
existing subprocess/protocol tests. It does not install a release, change a
service, grant provider authority or establish Grok durable delivery.
