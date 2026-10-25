# Extend or reset an external goal budget

These commands are source capabilities until the goal-limit UX integration is
installed and its native/frontend acceptance is recorded. They do not change
native usage counters. A stock native `/goal resume` does not renew external
resource authority.

`extend` accepts a new **absolute token ceiling** and either an absolute UTC epoch
`--deadline` or an explicit `--remaining-seconds` grant. For 100,000 consumed of
100,000, use a new ceiling of 150,000 to add 50,000 tokens. Extension retains the
window generation and usage, increasing its budget revision. `reset` creates a
new generation and qualified response anchor; the current window starts at zero
while lifetime usage, prior charges and stop episodes remain retained.

The exact enrolled goal must be paused, with no captured campaign work still active.
A later operator reply may remain active only on the native MCP path: the private
host metadata must attest its exact current turn, the original campaign stop must
be proved, the native goal identity must be unchanged, and that reply cannot be
any historical captured campaign turn. Other active turns and busy shared peers
continue to hold. CLI callers do not gain this exception by naming a turn.
The configured independent watcher, original history, boot/clock and all shared
members must qualify. Recovery from an observation or accounting fault is a
separate operation; more resource authority cannot repair that fault.

An authenticated operator can preview a proposal:

```sh
codex-wake --wake-root "$WAKE_ROOT" goal-limits extend \
  --policy "$GOAL_POLICY" --caller-thread-id "$THREAD_ID" \
  --bus-root "$BUS_ROOT" --operator-capability "$OPERATOR_CAPABILITY" \
  --operation-id operator-extension-1 --token-limit 150000 \
  --remaining-seconds 3600 --json
```

The response shows exact members, old/new totals, deadline, generation/revision,
expiry and whether resume was requested. Its `proposal_id` and `fingerprint`
identify one immutable proposal. Add `--shared` only for an explicitly authorized
shared-allocation change. Use `reset` instead of `extend` for an explicitly
requested new window. The configured policy path is read; users do not hand-edit
host JSON to renew a budget.

For an already explicit exact operator directive, append `--apply`. This records
and consumes the matching response in the **common attention queue**, applying
without asking the same approval question again. Without `--apply`, an operator
may accept the retained request through `attention respond` or apply the exact
preview explicitly:

```sh
codex-wake --wake-root "$WAKE_ROOT" goal-limits apply-renewal \
  --policy "$GOAL_POLICY" --caller-thread-id "$THREAD_ID" \
  --bus-root "$BUS_ROOT" --operator-capability "$OPERATOR_CAPABILITY" \
  --proposal-id "$PROPOSAL_ID" --fingerprint "$FINGERPRINT" --approve --json
```

Apply-only leaves the native goal paused. Add `--resume` to the original proposal
only when resume is also authorized. Application invalidates the earlier poll
acknowledgement; resume waits for the configured watcher's first qualified poll
of the new revision. Reapply the same approved proposal after that poll without
`--approve`; it uses the retained authority. An uncertain native resume is inspected
and never blindly sent a second time. A pending result is not proof of resume.

Native MCP exposes `wake_goal_limits_extend`, `wake_goal_limits_reset`, and
`wake_goal_limits_apply_renewal`. The first two only propose. The last consumes an
already authenticated exact operator response; model arguments cannot assign
operator identity, accept their own increase or use old approvals. In a common
policy with task-scoped attention, supply the verified task/assignment to the MCP
proposal rather than inventing task authority.

Duplicate operation IDs reconcile the same intent. Changed goal identity,
allocation, member set, revision, policy or expiry refuses before authority
changes. An interrupted filesystem application retains a journal and pending
fences; retry the same proposal to reconcile. Never try a new operation identity
to escape a pending transaction. Allocations containing finalized departed members
currently hold for explicit reconciliation; this implementation does not silently
rewrite their custody.
