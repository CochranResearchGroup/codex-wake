# Managed Grok mailbox and delivery policies

This is candidate source guidance. Production installation and real bidirectional
TUI acceptance are separate MR-06 gates. The supported Grok terminal route is
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
wake operations; native-only tool calls refuse. Real inherited session context and
MCP launch behavior still require MR-06 live qualification.

Wake registration accepts `--busy-policy wait|queue|interrupt`. Wait is the default;
queue/interrupt currently return busy_policy_unsupported before retention/input.
A new operator binding may opt into `--allow-terminal-fallback` alongside explicit
terminal-input approval. Only definite native-unavailable proof before submission
I/O permits that fallback. Accepted, uncertain or absent evidence cannot switch
methods. Protected composer, process/session, version and original deadline checks
still apply. Terminal observation is weaker than native or mailbox work receipts.
