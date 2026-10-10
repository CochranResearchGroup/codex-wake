# Legacy path inventory before retirement

Source: feat/native-workflows, baseline5175f5f. Structural evidence from the
worktree CodeGraph index and current delivery sources. This is inventory, not
acceptance of migration or release.

| Path | Caller / persisted contract | Replacement and disposition |
| --- | --- | --- |
| Implicit tmux time/file registration | cli.create_record → target_for_args → capture_tmux_target; schema1 or network-time schema3 | Native basic time/file acceptance0128–0131 qualifies replacement; retire implicit selection, retain explicit --legacy-tmux and existing-record dispatch |
| Classic changed/process liveness | cli.create_changed/create_pid → create_record → tmux capture; schema1 file_changed/process_done | Native parity unqualified; preserve these existing compatibility interfaces and readers |
| Explicit app-server registration | target_for_args --app-server-thread-id; schema1/3; injector → dispatch_app_server_record | Native uses shared daemon exact thread; retain explicit compatibility for existing callers and saved state |
| tmux delivery engine | injector exact binding/pane lock/composer guards; schema1/2/3 | Retain for explicitly selected legacy records, advanced predicates and recovery; no implicit fallback from native |
| Signal source registration/authority | filesystem/process/systemd/GitHub/HTTP sources; schema2 SQLite arms and lifecycle projection | Native replacement parity not qualified; retain without conversion |
| Tracked mailbox notification | TmuxBinding, exact recipient and bus capability; SQLite messages/outbox/receipts | Ordinary native messaging does not replace tracked receipt contract; retain explicitly tracked workflows and readers |
| OpenClaw gateway/plugin | separate gateway targets/plugin and persisted records | Outside scope; preserve unchanged |
| Candidate native records | native create/dispatch/reconcile; earlier schema1 target.transport=native | Promote explicitly to schema4 with no delivery or status change; qualify old-reader hold and restored-reader recovery |

Network-time policy remains an explicit classic compatibility option. Native
clock behavior is not upgraded or claimed equivalent by this retirement.
