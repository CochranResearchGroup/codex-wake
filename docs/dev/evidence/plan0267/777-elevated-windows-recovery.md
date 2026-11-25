# #777 elevated Windows recovery qualification

The Cooper run used the existing normal and elevated SSH execution routes,
two private Windows owner roots, PSMux 3.4, native stock Codex 0.169.1,
and disposable PostgreSQL. The stock app servers used local inference
fixtures and the owner adapters used an injected test clock. No installed
service configuration or unrelated sessions were changed.

| Check | Observation |
| --- | --- |
| Identify both scopes with the public console entry point from staged source | The two Windows tokens had the same account SID. The normal route returned `elevated: false` and the elevated route returned `elevated: true`. |
| Enroll identical tab names and positions | Both independent namespaces had a `same-name` tab in slot 2. They initially even used the same local window ID `@3`, with different server generations and conversation IDs. |
| Ask either scope to restore the other's binding | Both returned `windows_execution_scope_changed`. The lower-integrity Windows token was also denied writable access to the elevated activation file and read access to the elevated app-server token. |
| Close the elevated tab while its executor is disabled | The elevated route returned `executor_disabled` without adopting the message. Its presentation command returned `restore_elevated_executor_disabled`. The normal owner's tab and owner remained available. |
| Re-enable the elevated executor against the original retained message | The elevated slot reopened under the same Windows account and high-integrity token, with a new local window and the original conversation. The owning transport and the sender reported the same confirmed receipt. |

Both attempts restored elevated thread `01a21154-01e3-7241-aff1-e06e85fb40b5`.
The normal thread `01a21153-fdfa-7ef0-9f7e-63e450a5d4a6` and its tab
remained in their original placement across both attempts.

| Original Message | Restored tab | Native receipt | Completed turns |
| --- | --- | --- | --- |
| Immediate `a4e4ea08-2f3f-4ca2-bace-a4cfdeea69a0` | `@4` | `01a2115b-2c3a-7d12-b4c8-1b5c07ef7472` | One, `01a2115b-2c47-7f41-a798-130e30461b92` |
| Timed `34cdedcf-0d90-469e-b368-f1536fbdf918` | `@5` | `01a21160-cc1b-7643-84e3-d035ae76a8d2` | One, `01a21160-cc1c-77e0-aea2-85046d1c5e65` |

PostgreSQL contained one submitted attempt per original Message and distinct
source and destination scopes. The timed case preserved its original due time
`1795587732004829` and expiry `1795588930004829` in UTC microseconds.

Local validation used Python 3.12 and a disposable PostgreSQL database.

```sh
PYTHONPATH=src:tests python -m unittest test_controller_hosts test_message_owner \
  test_a2a_permissions test_native_protocol_large_response \
  test_postgres_message_delivery test_tab_psmux
python -m compileall -q src/codex_wake tests/test_controller_hosts.py
python scripts/check_policy_wiring.py
python scripts/check_native_expiry_artifact.py
```

All 38 tests and the listed checks passed. Ruff 0.14.2 reported no
`F821`, `F822`, or `F823` findings in touched Python files. Hosted CI
was skipped.
