# Common session permissions

The common policy is selected explicitly by an operator. New verified sessions
inherit its defaults without UUID enrollment. Identity, action permission,
runtime capability and readiness are separate checks: allowing a refresh does
not make a connection-scoped refresh available.

## Configure or adopt

Use the existing operator bus capability. Keep policy files owner-only. Preview
legacy mapping before adopting a host with existing grants or pending work:

```sh
codex-wake --wake-root ROOT permissions adoption-plan --bus-root BUS \
  --operator-capability OPERATOR_CAPABILITY --file POLICY.json \
  --legacy-profiles LIFECYCLE_PROFILES.json --json
codex-wake --wake-root ROOT permissions adopt --bus-root BUS \
  --operator-capability OPERATOR_CAPABILITY --file POLICY.json \
  --legacy-profiles LIFECYCLE_PROFILES.json --expected-revision 0 --json
```

The preview writes no operation records. Unmapped entries refuse adoption.
Existing explicit caller denials and profile restrictions become retained
ceilings; absent UUID entries still inherit defaults. A legacy experimental
`session_permissions.self_access` flag requires explicit mapping, rather than
silently becoming a second policy system.

An old pending wake has no common-policy caller provenance. Finish/reconcile it
before adoption, or explicitly use `--hold-legacy-pending` with `adopt`. Holding
preserves its original record, routes, due time, expiry and uncertain history;
it does not create permission for resubmission. A retained uncertain submission
can still be reconciled read-only. The same migration review lists unqualified
pending lifecycle operations. No source fixture qualifies an installed runtime.

For a fresh root, `permissions configure` accepts the same operator capability,
file and expected revision. It refuses silent first adoption over pending legacy
work. Policy changes compare revisions and retain history. Missing adopted policy
fails closed instead of returning to legacy behavior. Replacing a policy without
an adoption section preserves its existing legacy ceilings; changing those
ceilings requires an explicit operator revision.

One root can serve several execution journals. Bind each extra journal explicitly:

```sh
codex-wake --wake-root COMMON_ROOT permissions bind-domain --bus-root BUS \
  --operator-capability OPERATOR_CAPABILITY --domain-root LIFECYCLE_ROOT --json
```

The link pins one canonical common policy, not a copy. Existing conflicting
bindings/local policy require migration. Policy configuration also binds the
operator's bus; additional buses use `a2a permissions`. An actor cannot choose a
different message-policy root through wake arguments.

## Policy rules

A minimal file is `{"version":1}`. Its permissive profile allows self-inspection,
refresh/handoff/resume, enforcement enrollment, managed A2A and task/recipient-
authorized wake routes. Shared reload requires standing approval. Increasing an
allowance, disabling enforcement and recovering an observation-fault stop require
their own authority. Recovery/disable execution remains unsupported where the
runtime has no qualified implementation; permission checks never clear latches.

The optional `global`, named `profiles`, `sessions` and task `assignments` layers
have `default` and `actions` fields. Decisions are `allow`, `deny`,
`approval_required`, or `inherit`. An exact action replaces its layer's fallback;
layers apply global, profile, session, assignment. `mandatory` is a list of
non-overridable action prohibitions. A rule may constrain `relationships`,
`targets` and `tasks`; a task claim must come from verified task/assignment scope.

Example restricted profile and one session override:

```json
{
  "version": 1,
  "global": {"authorized_profiles": ["permissive", "review"]},
  "profiles": {
    "review": {"default": "deny", "actions": {"session.inspect": "allow"}}
  },
  "mandatory": ["enforcement.disable"],
  "sessions": {"EXACT_SESSION_ID": {"actions": {"handoff.self": "deny"}}}
}
```

Agents may restrict themselves or select preauthorized profiles using
`wake_permissions_update`; they cannot assign themselves a role. Host-owned
`delegations` grant controllers explicit `actions` and `sessions` scope.
An operator is required for full policy configuration. Fresh actions added by
an upgrade require approval unless `future_actions_inherit` was explicitly set.
A configured rule for that action is already an operator decision.

Approvals identify action, subject, issuer and scope (`operation`, `task`,
`standing`). Bounded approvals include task and expiry; operation approval IDs
match the admitted operation intent. Task approvals follow verified same-task
successor lineage by default; `successors:false` makes them original-session-only.
Completion or expiry ends them without renewing resources. Shared reload needs
standing scope approval in both policy and the provisioned host profile.

Inspect using `wake_permissions_show`, or authenticated `permissions show`.
The result distinguishes the deciding permission rule/revision from capability
and readiness. Optional `launch_profile` explains migrated profile ceilings.
The action catalog covers session inspection, the three refresh scopes, self
handoff/resume, enrollment/increase/disable/recovery, A2A send/receive/claim/reply,
and background/existing-tab/new-tab/fresh-task wake routes.

## Automation and delivery

Configured automatic handoff triggers are `context_limit`, `update` and
`resource_warning`; `manual` needs no automatic-trigger entry. The existing host
continuation's `handoff_triggers` selects them. The same task, approval expiry,
original counters and deadline continue through the verified successor.

Wakes may freeze an ordered `routes` list: `background`, `existing_tab`,
`new_tab`, `fresh_task`. Every route must be permitted and supported. Fallback
requires definitive evidence no submission I/O occurred. Uncertain outcomes
remain on the original route for reconciliation. Fresh-task launch additionally
needs declared, verified task authority. Unsupported startup never substitutes a
different conversation or wider scope. Old compatible readers hold new policy
records rather than interpreting the new routes as old semantics.

#318 tracks missing current-connection/client refresh capability. #319 tracks
recovery from transient observation stops. Neither is repaired by a permission
allow, fresh process, heartbeat, ordinary native goal resume or resource renewal.
