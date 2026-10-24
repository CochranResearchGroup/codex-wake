# Managed conversation inventory

Managed inventory tracks one exact provider conversation independently of its
current process and terminal attachment. Inventory membership grants no lifecycle
operation, mailbox claim or resource allowance. Successor conversations get new
managed IDs and may link their predecessor's task/allocation references; those
references do not issue or renew allocations.

The private version-1 inventory lives under the configured Wake root in
`managed-inventory/inventory.json`. A file lock serializes policy and identity
transitions, and atomic replacement publishes a complete state. Unknown versions
or malformed/private-path failures hold without rewriting the document.

## Enrollment and operator controls

`agents enroll --runtime codex --conversation-id ID` uses the default
`self_enrollment` policy when called with trusted host-native metadata. The
claimed ID is checked against the private native MCP context, native thread
metadata and observed process generation. Missing sources, ambiguous clients or
unavailable process generations do not enroll a guessed conversation.

The local CLI's explicit `--operator` represents the existing local OS-user trust
domain. It is not an MCP argument and is not isolation against hostile same-UID
code. Operator actions can adopt a selected qualified conversation, configure
policy, suppress enrollment or re-enable it:

```text
codex-wake --wake-root ROOT agents configure --mode self_enrollment --operator
codex-wake --wake-root ROOT agents configure --mode operator_only --operator
codex-wake --wake-root ROOT agents enroll --conversation-id ID --operator
codex-wake --wake-root ROOT agents unenroll --managed-agent-id AGENT --operator
codex-wake --wake-root ROOT agents reenable --managed-agent-id AGENT --operator
codex-wake --wake-root ROOT agents list --json
codex-wake --wake-root ROOT agents show --managed-agent-id AGENT --json
```

`operator_selected` permits self-enrollment only for exact runtime/namespace/
conversation triples in the operator's `--selected-json` list. `operator_only`
requires an operator action. Explicit unenrollment persists suppression for the
exact conversation across process/controller restarts and policy changes;
even an operator enrollment call does not implicitly clear it. Use `reenable`.

A direct CLI self-call without trusted native metadata cannot authenticate itself
by setting `CODEX_THREAD_ID`. Use its host-native MCP integration or the explicit
local operator action. No per-thread configuration registry is needed to enable
default verified self-enrollment.

## Read and recovery semantics

`enroll` is idempotent by exact runtime namespace/conversation identity and keeps
the managed ID across a verified new process or moved attachment. `reconcile`
requires both that identity and its managed ID; it can record unavailable or
ambiguous observations without substituting another conversation. Observations
older than 30 seconds project as `stale`, and `binding_current` is false for stale,
unavailable, ambiguous or suppressed agents. `ready` means the inventory binding
was recently verified; it is not a claim that the TUI composer is idle or can be
interrupted. `grants_operations` is always false.

Read projections contain public attachment metadata and verified process
identity, plus source provenance and conservative operation capabilities. They
do not contain terminal frames, private socket endpoints, prompts or credentials.

## Grok caller evidence

Grok uses its existing host-bound managed-launch profile, exact process generation
and inherited caller ancestry, plus its independently issued mailbox actor
capability. The inventory does not promote terminal identity text into native
caller attestation. Runtime provenance remains `host_bound_runtime`.

Operator Grok adoption uses an existing frozen binding; it does not create or
refresh terminal identity, send keystrokes, launch Grok or change credentials.
Agent Grok calls use the host-selected private runtime actor profile and cannot
substitute a binding path from model arguments.

## Integration interface

Both callers use `managed_inventory_commands.execute(action, arguments, root,
native_context=..., observer=..., operator=False)`. Trusted caller metadata and
the observer are host inputs, not agent arguments. Production observers are
`RuntimeObserver`; tests inject the same observation seam over disposable roots.
`register_parser(subparsers)` registers the CLI group, and `run(args, root)` emits
JSON and stable held errors. The top-level CLI and MCP hubs are integrated by the
primary owner of Plan0173.

#310 owns default own-session lifecycle policy. Inventory consumes its established
caller-evidence contract and does not repair host refresh permissions. There are
no provider, installation, deployment or real-terminal effects in the source
qualification for this ticket.
