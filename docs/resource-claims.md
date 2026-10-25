# Cooperative resource custody

`resources claim` gives one managed agent exclusive cooperative custody of an
existing canonical directory tree. Supported kinds are `worktree`, `build_prefix`
and `install_prefix`. Ancestor and descendant paths conflict in either order,
even across kinds. Symlink aliases are refused. This is a prerequisite for
participating Wake mutations, not an operating-system access grant or an attempt
to intercept arbitrary same-user filesystem writes.

The enrolled managed conversation and its fresh host-verified process generation
identify the owner. Worker claims stay within that conversation's workspace. The
local operator may allocate a prefix outside it explicitly; custody does not grant
filesystem, execution or task permission. Inventory membership alone grants none.

```sh
codex-wake --wake-root /owned/wake resources claim --operator \
  --managed-agent-id agent_0123456789abcdef0123456789abcdef \
  --kind worktree --path /owned/existing-worktree
codex-wake --wake-root /owned/wake resources show --claim-id claim_0123456789abcdef0123456789abcdef
codex-wake --wake-root /owned/wake resources release --operator \
  --claim-id claim_0123456789abcdef0123456789abcdef --generation 1 \
  --reason 'Owner disappeared; pending effects reviewed and retained'
```

`list` and `show` inspect retained ownership and history. `claim` returns the exact
claim ID and generation. Retrying the same active exact owner/resource returns the
same claim. `check` verifies that token against fresh caller evidence and returns
`point_in_time_only: true`: its success cannot authorize a later unguarded effect.
A verified current owner may `release` its exact generation. `transfer` requires an
explicit local operator, expected generation, reason and currently qualified target
managed agent. Release and transfer increment generation; prior tokens remain
fenced. No operator/role argument is exposed to model tools.

A disappeared controller, stale observation, dead process or changed process
generation never releases a resource. The claim remains active and competing
acquisition is refused. An operator must inspect pending effects and explicitly
release or transfer it, preserving the attributable history. Changed directory
identity also holds; release the old identity explicitly before claiming its
replacement. No command deletes the resource or rewrites unrelated claims.

The public `ResourceClaims.guard(claim_id, generation, claimant)` context manager
checks active custody, owner generation, fresh evidence and directory identity,
and holds the claim serialization lock through the caller's mutation. Consumers
must keep their actual effect inside that context; HF-05 consumes this interface
for guarded interactions. Contending admission, transfer or release returns
`resource_busy`; retry only after the original effect is reconciled. Existing pane
and lifecycle locks remain in place and have a different short-lived purpose.

Version-1 private metadata lives under `resource-claims` beneath the selected Wake
root. State changes use a private lock and atomic publication with directory sync.
The initialized marker prevents missing authority from becoming an empty new claim
set. Unsupported/malformed state is retained and held, never auto-migrated. History
has a bounded total size and is never pruned to make an admission succeed.

CLI native worker calls need a host-supplied native caller context; an ordinary
shell uses explicit `--operator` for operator actions. MCP gets native metadata
from its host, not tool arguments. Grok uses the existing host-bound runtime actor
context, not inferred native attestation. Runtime observations in deterministic
tests are injected; no provider turns or installed production behavior are implied.
