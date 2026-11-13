# Bot families and terminal attachments

A bot is a persistent specialist, separate from its conversations and tabs.
Codex-bots manages specialist/account/task parentage, guidance and supervision;
Wake organizes the exact per-client terminal attachments. Neither tab titles nor
family registration grants account access or input authority.

Inspect the public interface with `codex-wake tabs family --help`. The same
operations are exposed by the generated HTTP/MCP catalog. For example:

```sh
codex-wake tabs family register --bot-id chatgpt --name ChatGPT
codex-wake tabs family register --bot-id work --parent-bot-id chatgpt --name Work --scope-kind account --scope-ref work
codex-wake tabs family show --bot-id work --json
codex-wake tabs family list --root-bot-id chatgpt --json
```

Register ancestors before descendants. Bind an actual observed attachment using
`family bind` with bot/client IDs and the exact workspace/window/pane IDs from
`tabs list`. Pane process births fence replacement; another client's attachment
is separate. The configured Bots adapter does this for managed Bot conversations.

`family open` organizes the exact existing binding or opens an explicitly selected
command/profile in the background. One managed workers session is shared per
terminal server; families are contiguous. `--placement adjacent` uses the parent
attachment in the same environment. Repeated opens reuse a live primary tab;
manual movement/adoption is respected. Missing or uncertain effects hold rather
than launching duplicates. Unsupported backends retain their source attachments.

Scope labels include immediate parent and a muted stable family accent. Existing
formatting opt-out, manual decoration holds and rollback remain effective. Error
and attention styles take precedence. A missing root tab is shown separately
from durable root identity. `family focus --relation parent` or `root` navigates
only when the corresponding exact client attachment is live.

A successful result accepted by the immediate parent can close only an explicitly
temporary, unadopted, idle owned tab. Failed, unfinished, busy, pinned, unknown or
manually adopted tabs remain. Acceptance is idempotent; bot records/conversation
history remain after tab cleanup. Empty owned workers sessions are removed.
No implicit child cancellation, history deletion, resource renewal or provider grant.

Live installation is a separate operator-controlled step. This feature's local
qualification uses existing service/CLI and disposable tmux, without provider calls.
