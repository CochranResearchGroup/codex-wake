# Visible wake restoration: #668

Status: **acceptance incomplete; keep issue open**. Plan 0241 / issue #663
owns the contract. This bounded lane starts from source
`882aae8007e71cc2641c66a742e340e6cf007310` and changes only an opt-in
probe plus this evidence/proposal document.

## Observed boundary

The probe used the installed `0.22.0.dev28-1fb9180` Python and deployed
protected HTTPS OAuth/MCP endpoint. Three disposable setup attempts failed
before public authorization or schedule registration. Attempt 1 reached a real
remote Codex TUI folder-trust prompt, but no native metadata-matched attachment
was verified. Attempts 2 and 3 failed on native `thread/read` during setup
(shared reader, then direct native request). These are failed setup observations,
not due-wake refusals or proof of visible restoration. No fourth fresh attempt
was made. The final script adds explicit opt-in, unique session names, preserved
receipt paths, stage reporting and cancellation cleanup; those final changes
were checked locally but were not rerun live.

Private contemporaneous receipts and logs are in the user-scoped
`connector-acceptance-spec` state directory: `visible-wake-attempt1.json`,
`visible-wake-attempt2.json`, `visible-wake-live.json`, and
`visible-wake-probe{,2,3}.log`. The early receipts did not retain thread IDs;
there is no reconstructed identity claim. Each reports own session absent and
own thread archived. All attempts stopped before grant/schedule creation.
Final terminal inventory contained only the existing `default` session.
No operator terminal, native daemon, account authentication or permission policy
was changed. No restoration config was written.

## Installed configuration gate

Readback of the connector's configured controller root found:

- `wake-live-restore.json`: absent.
- `controller-tabs.json`: absent.
- Managed inventory: zero agents; `self_enrollment`, empty selected list.
- Common permission policy: inactive; no policy/routing/adoption files.

`LiveWakeRestorer._configuration` needs an exact conversation binding to a
host-owned named profile and managed agent. `_restore` verifies saved native cwd,
profile cwd and managed root agree. `AgentResume._permission` additionally
requires active common policy. Adding only disposable binding/profile files
cannot satisfy that gate. Reattaching a frontend directly is useful setup but
is not a substitute for qualifying the scheduled restore owner.

## Reviewable restrictive adoption proposal (not applied)

This is a proposed input to the existing `PermissionStore.configure` owner,
not a hand-written policy journal. Replace `OWN_THREAD_UUID` with the verified
disposable conversation and set its exact profile binding separately:

```json
{
  "version": 1,
  "global": {"default": "deny"},
  "sessions": {
    "OWN_THREAD_UUID": {
      "actions": {
        "session.inspect": {"decision": "allow", "relationships": ["self"], "targets": ["OWN_THREAD_UUID"]},
        "wake.existing_tab": {"decision": "allow", "relationships": ["self"], "targets": ["OWN_THREAD_UUID"]},
        "wake.new_tab": {"decision": "allow", "relationships": ["self"], "targets": ["OWN_THREAD_UUID"]},
        "resume.self": {"decision": "allow", "relationships": ["self"], "targets": ["OWN_THREAD_UUID"]}
      }
    }
  }
}
```

The supported owner requires an operator principal and expected revision zero;
it creates `session-permissions/policy.json` and `adopted.json` with revision,
issuer and history. No OAuth grant is broadened by this proposed document.
However, activation selects the common resolver for the entire controller root.
The restrictive default would deny other root consumers, and merely selecting
one session does not isolate adoption to that profile. Existing unrelated
controller consumers must be inventoried and their explicit policy decision
reviewed before activation. A default-permissive policy is not proposed.
Removing adoption afterward is not a demonstrated rollback mechanism.

Other required host-owned setup would be an exclusive-created private profile
file (`version`, `profiles`, optional exact `callers`), a matching
`wake-live-restore.json` binding (`version:1`, `bindings[UUID]` containing
`profiles`, `managed_agent_id`, `profile`), and qualified terminal-server
configuration when creating an absent session. These must come from actual
native metadata/attachment observation and the real trusted executable/home;
no fake ready observation, copied credential or fabricated identity is valid.
Any temporary file must have recorded ownership/hash and be removed only if
unchanged. This proposal supplies no activation authority.

## Validation and remaining criteria

Focused local checks: `python -m py_compile
scripts/connector_visible_wake_acceptance.py` passed; installed Python
`--help` passed. No hosted GitHub Actions were used under the CI cost policy.
These checks validate script syntax/CLI only. No product code changed, no
fixture platform was added and no provider-free test is represented as live
acceptance.

Required remaining proof: explicit persisted policies, real recipient tab
closure, actual due wake visibly restoring that same conversation with the last
verified harness/cwd, one correlated native delivery and completed result, and
exact schedule/tab/process/grant cleanup. The probe deliberately cannot mark
acceptance passed from message count alone.

Memory disposition: `forbidden`; no explicit memory write was requested.
