# #774 normal Windows and WSL owner qualification

Source commit `175bfde33b0cb2bc1b2f9ac926c20ca70184d866`. Qualification
ran on Cooper using a private native Windows fixture and an isolated WSL
owner root. Native Python 3.14.3 reported `IsUserAnAdmin() == 0`.
PostgreSQL reported `17.10 on x86_64-windows, compiled by msvc-19.44.35226,
64-bit` and listened on fixture loopback port 57474. Ubuntu WSL used mirrored
networking to the same port. Both owners used the existing StableTime client
for eligibility and expiry. Owning effect adapters were test doubles.

| Public observation | Result |
| --- | --- |
| Native PowerShell runner with the isolated native database ready | Exit 0 and `{"shared_ingress":true,"status":"ready"}` |
| Native PowerShell runner with a missing named Windows database service | Exit 3 and `waiting_for_native_database_service` |
| Native PowerShell runner after stopping the disposable database | Exit 3 and `waiting_for_database` |
| Windows to WSL with WSL owner stopped and optional activation disabled | Source reported `waiting_for_wsl`. No peer worker or transport effect existed until WSL handled the message. Original ID `f013d7ea-3770-4ac8-8721-04b0ba5e7fd3` had one owner receipt. |
| WSL to Windows with Windows owner unpolled | Source reported `waiting_for_windows`. Windows recorded one owner receipt for `27665f1c-3281-4a5d-83ae-b6f0b3442302`. PostgreSQL preserved the exact expiry and reply link to the preceding WSL-bound ID. |
| Windows to WSL with optional activation enabled | Native `wsl.exe` started exactly one previously absent fixture owner process in the existing Ubuntu distribution. Original ID `a9d074bb-412d-4718-81d1-6ade132eab99` had one owner receipt. |
| Local continuity during native PostgreSQL outage | WSL committed owner DND revision 2. The existing isolated WSL-only mailbox also dispatched message `msg_8a956195e3ab4038a53cc1362e8981c8` exactly once without the shared store. |
| Native `pg_dump`, stop/start and `pg_restore` of a stale image | SQL confirmed the original shared row was absent after restore. The Windows local journal restored uncertain message `914fcf54-ab25-4c75-930c-8b9cb7b78f67` under attempt `95c7d90a-cd65-4563-997c-10247a322d27`. The owned adapter log still had one effect. |
| Outage queue after native database recovery | A remote edit based on revision 1 returned `revision_conflict` with owner revision 2 and DND still on. A separate queued message returned `expired` with no adapter call. |

The Windows interop process used to start the restored native database kept its
output capture open beyond the fixture timeout. Native PostgreSQL startup
logs and a direct SQL query confirmed the server had already started. The
qualification then continued through the actual restore and readback.

Native Windows cold boot with WSL absent, boot without desktop login,
installed service registration and real Codex harness effects remain separate
runtime acceptance gates. The tested activation launched the isolated owner
inside an already running WSL distribution. Existing scopes that opt into
the earlier shared-store cutover retain their PostgreSQL dispatch dependency.

The disposable PostgreSQL regression command ran 36 tests.

```sh
PYTHONPATH=src:tests python -m unittest test_message_owner test_controller_hosts \
  test_postgres_message_delivery test_message_cutover test_a2a_delivery \
  test_native_protocol_large_response -q
```

Set `CODEX_WAKE_TEST_MESSAGE_DB_DSN` in the process environment to the
disposable test database. Ruff 0.14.2 passed the local undefined-name checks.
No hosted CI was used.
