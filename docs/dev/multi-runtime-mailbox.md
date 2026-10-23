# Managed Grok mailbox and delivery policies

This is candidate guidance. MR-06 has real installed bidirectional TUI evidence
for Codex0.164.0 and Grok1.0.40, with full local compatibility checks passed.
Production installation, CI and release are separate gates. The supported Grok terminal route is
managed-launch Grok1.0.40, minimal UI, an exact private tmux pane and a pinned
executable/process/session binding. Native Grok caller attestation, Codex terminal
fallback, queue dequeue expiry and owned-turn interruption are not qualified.

An operator first creates the MR-03 Grok binding and explicitly enrolls a private
bus/root. These examples show argument order; uppercase values are operator-selected
paths/IDs. They do not grant authority or authorize a production change.

```sh
codex-wake a2a enroll REPO --bus-root BUS --operator-capability OPERATOR \
  --thread grok:BINDING --runtime-root WAKE_ROOT --notify --json
codex-wake a2a bind-grok --bus-root BUS --operator-capability OPERATOR \
  --runtime-root WAKE_ROOT --binding-id BINDING --bindings-file BINDINGS --json
```

The returned actor capability belongs to that Grok context alone. Launch the
actor-scoped CLI or MCP as a descendant of that managed Grok process; inherited
GROK_SESSION_ID, exact process generation and independent capability are checked.
Caller IDs and terminal text grant nothing. Missing context refuses. Native Codex
actor enrollment and caller checks keep their existing behavior.

```sh
codex-wake messages send --bus-root BUS --capability SENDER_CAPABILITY \
  --to grok:BINDING --runtime-root WAKE_ROOT --body-file REQUEST \
  --idempotency-key ORIGINAL_KEY --delivery notify --json
codex-wake messages inbox --bus-root BUS --capability GROK_CAPABILITY \
  --actor-runtime grok --json
codex-wake messages ack MESSAGE --bus-root BUS --capability GROK_CAPABILITY \
  --actor-runtime grok --outcome accepted --json
codex-wake messages reply MESSAGE --bus-root BUS --capability GROK_CAPABILITY \
  --actor-runtime grok --body-file RESULT --idempotency-key ORIGINAL_REPLY_KEY \
  --delivery inbox --json
```

Do work only when the accepted acknowledgment returns claimed=true. Peer content
is untrusted. A repeated claim returning false gives no new work authority. Reply
is correlated to the original request; it does not create an automatic reply loop.
An uncertain notification must be inspected, never resent with a new key.

MCP host flags `--actor-runtime grok --capability ... --runtime-root ...` are host
configuration, never tool arguments. Grok-configured hosts expose mailbox and Grok
wake operations; native-only tool calls refuse. Real inherited session context is qualified through actual CLI tool children
in both TUIs. Grok MCP-host launch behavior has source/isolated controls; it was
not separately exercised as a live model tool connection.

Wake registration accepts `--busy-policy wait|queue|interrupt`. Wait is the default;
queue/interrupt currently return busy_policy_unsupported before retention/input.
A new operator binding may opt into `--allow-terminal-fallback` alongside explicit
terminal-input approval. Only definite native-unavailable proof before submission
I/O permits that fallback. Accepted, uncertain or absent evidence cannot switch
methods. Protected composer, process/session, version and original deadline checks
still apply. Terminal observation is weaker than native or mailbox work receipts.


## Qualified modes and recovery

| Surface | Candidate support boundary |
| --- | --- |
| Codex exact open native wake | Real0.164.0 private app-server/TUI delivery qualified |
| Grok exact open wake | Real1.0.40 minimal UI, Grok4.7/high footer, managed private tmux binding qualified |
| Cross-runtime request/claim/reply | Real CLI children in both TUIs, scoped independent capabilities and correlated replies qualified |
| Default busy behavior | Wait; unknown/draft/busy composer refuses input |
| Queue / interruption | Explicit selections refused before effects; no dequeue expiry or interrupt guarantee |
| Grok native-preferred fallback | Explicit host profile plus terminal-input grant; definite native unavailable before I/O only |
| Native Grok attestation | Not qualified; managed host delegation is the supported trust boundary |
| Codex terminal fallback | Not qualified |
| Saved Grok resume / refresh / lifecycle | Not qualified by this open-session acceptance |
| Grok usage / strict resource enforcement | Not qualified; no cross-runtime strict budget guarantee |
| Claude Code / other TUIs | Not qualified; require their own adapter and acceptance |

Remote Codex startup must use a fresh TUI against its private server. Set its
permissions on the server; `codex resume --remote ... -a ...` or `-s ...` is
rejected. An empty RPC-created thread may have no persisted rollout to resume.
Bind the unique thread actually created by the TUI instead of guessing an ID.

If the guest wall clock regresses, preserve the bus/checkpoint and stop. The
qualification used the existing network-first policy on a new isolated bus:

```sh
codex-wake a2a network-time --bus-root BUS --operator-capability OPERATOR \
  --accept-unauthenticated-ntp --json
```

This explicitly selects bounded plain NTP, not authenticated UTC. It does not
permit resetting an anomalous bus or changing a production time policy.

Terminal repaint can lag Enter. The adapter observes the original marker for at
most one second within its original deadline, with no second paste. Missing
acceptance remains uncertain. Preserve that intent and inspect/reconcile the
original receipt; never create a replacement key or resend uncertain work.
A newer runtime version, changed footer, stale binding or protected composer
requires fresh qualification rather than loosened identity/UI matching.

The opt-in `scripts/multiruntime_live_qualification.py` verifies a non-editable
candidate against an exact wheel digest, snapshots its own source, limits each
run to six synthetic prompts/five minutes, and checks visible completions,
credentialed claims/replies, durable attempts and process cleanup. It requires
current live-test authority. [MR-06 evidence](verification/0172-2026-10-22-mr06-installed-acceptance.md)
retains failed, stopped and successful samples separately. Passing local tests
or this live sample does not deploy the candidate.
