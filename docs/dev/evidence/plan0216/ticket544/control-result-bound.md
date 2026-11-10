# Bounded monitor mutation acknowledgements

The public100tab retained-result regression proves the stop uncertainty cause.
A real disposable100window tmux observation produced a414476byte full status
payload, above ControllerRuntime's unchanged262144byte effect-result limit.
Before this fix, public `tabs monitor-stop --json` on that cached inventory exited3
with operation.phase=uncertain, execution=unknown, reason=effect_uncertain and
result=null, even though the already-stopped effect was harmless/completed.
The normal active-stop path returned the same oversized full status structure.

Start, already-running start, stop and already-stopped stop now acknowledge with
bounded monitor status/process/generation/settings/last_error/capabilities plus
the original control booleans. Inventory and large per-workspace diagnostics stay
in monitor-status/refresh reads. The global journal limit and authorization,
service ownership, target pinning and exit-status implementation are unchanged.
Human control output reports the actual monitor state and tiers, with an explicit
monitor-status inspection command; it does not invent a zero tab count when no
inventory was included.

## Public qualification

The new public CLI/journal test seeds only a genuine disposable100tab observation,
asserts full status exceeds the retained boundary, and executes all five paths:
already-stopped, start, already-running start, active stop, already-stopped again.
Each result must be terminal/completed, retain exact monitor process identity and
settings, preserve its control boolean, omit inventory, and fit the unchanged
bound. Status still exposes all100cached resources after the first control. The
service ownership cases use an empty private terminal configuration so they
perform no formatting effects. All fixture clients and server processes are
cleaned by the test. The same retained stop request is read as human output to
verify truthful bounded-summary presentation without replaying the effect.

Python3.12.13 measured control replies433–614bytes; Python3.11.15 also passes.
Machine receipts control-bound-python311.json and control-bound-python312.json
record exact payload sizes. Selected existing monitor lifecycle and uncertainty
presentation checks pass; ruff F821/F822/F823 and git diff --check pass. These are
focused source checks, not a substitute for ticket547's exact installed gate.

## Native close profile clarification

The actual monitor profiles contain exactly one NativeStatusFeed.close call each:
monitor-json-owner.prof own.000297s/cumulative25.005s in a25.080s profile;
format-cost-owner.prof own.000262s/cumulative23.502s in a23.585s profile. These
signal/thread profile cumulative values are not a measured wall-clock close
latency or evidence of repeated close churn. Cleanup was reported prompt by the
qualification owner. No close change is made without a wall-clock reproducer.

Memory disposition: forbidden; no explicit memory-write request.
