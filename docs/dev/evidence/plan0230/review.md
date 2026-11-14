# LOCAL-P230 review

Frozen base e8c79a79da0b0482e2403e634394c70f5c66e333; working patch and new P230
artifacts reviewed serially by primary. Scope: LOCAL-P230. Standards: AGENTS.md,
docs/agents/codex-stack.md, architecture guardrails, runtime proof, testing and
Git/release policies. No CONTRIBUTING.md or CODING_STANDARDS.md found.

## Standards

No accepted violation. Existing native runtime, message admission and delivery
seams are reused. The host provisioning helper is private launch context, not
an actor-selectable MCP credential escape. New automatic binding is explicit
operator opt-in. No unrelated model/native-daemon/provisioning changes.

## Spec

One accepted blocker: SharedSourceError/SelectionError from native recipient
lookup escaped NotificationDispatcher.tick, stopping the worker instead of holding
one notification. Regression reproduced SharedSourceError. Handler now returns
runtime_unavailable and defers, avoiding accidental saved-recipient reopening.
Regression green. No remaining accepted blocker in frozen scope.

The historical intermittent composer_protected refusal remains unproven and its
safeguard is unchanged. Working-host installation must still verify new-session
first contact and reconnect; source tests alone do not prove activation.

Review summary: Standards 0 accepted; Spec 1 accepted (resolved).

## StableTime closed-world extension

Operator-selected StableTime is the time authority. Existing production network
mode and fresh smoke legacy mode were distinguished explicitly. The optional
provider pin preserves history, denies unsafe migration/downgrade/fallback, and
older readers fail closed. One new accepted Spec finding (stale in-memory policy)
was reproduced and resolved under the transaction lock; final installed163 pass
includes it. No new broad discovery review; cumulative accepted Spec findings2,
both resolved. Standards remains0 accepted. Real native rollout is still separate.
