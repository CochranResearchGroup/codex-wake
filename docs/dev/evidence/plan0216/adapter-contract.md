# P216 shared source contract (integration-owned)

One event adapter per exact source, never pertab. NativeStatusFeed in
`tab_native_feed.py`, TmuxMetadataFeed in `tab_tmux_feed.py`.

Constructors:
`NativeStatusFeed(endpoint, *, clock=time.time, monotonic=time.monotonic, timeout=2, connector=None)`
`TmuxMetadataFeed(socket_path, session_id, *, clock=time.time, monotonic=time.monotonic, timeout=2)`
Optional system-boundary injection may add keyword args, not remove these.

Both expose `poll(timeout=0.0) -> list[dict]`, `status() -> dict`, `close()`.
Poll is bounded by timeout after initial bounded connection/bootstrap (startup
reported separately); allowlist metadata only, no provider/model/clientownership.
Close only owned connection/controlchild and reap it; never killserver/agent.

Events: `{source_id:str, source_kind:'native'|'tmux', epoch:str, sequence:int,
kind:'baseline'|'update'|'unavailable', observed_at:wall_seconds,
data:dict}`. Epoch random/new on connection or server generation replacement;
sequence strictly increases within epoch. First valid event is complete bounded
baseline. Gap/disconnect yields unavailable with reason; no fabricated freshness.
Do not retain raw terminal/chat content. Bounded queue/eventcount and readtimeouts.

Native baseline data: `{threads:[{id,cwd,modelProvider,status,...metadataOnly}],
server:{codexHome,userAgent,...}, peer:{pid,start_ticks,boot_id,...}}`.
Update data: `{thread_id:str,status:dict}` from thread/status/changed only.
Native identity may include validated metadata fields, never turns/items/messages.
Full thread events/subscriptions are not needed. Ignore unsupported notifications;
do not respond to server approval/input requests. Verify same-user Unix peer.

Tmux baseline/update data: `{snapshot:...}` matching existing TmuxTransport.snapshot
server/session_id/socket_identity/windows/panes fields. Metadata commands via
control connection; no-output/ignore-size/explicit session, noresize/detach/input.
If epoch invalidation, startupbaseline must precede changes; row identities include
pane PID/process birth wherever existing snapshot owner supplies it. Preserve
literal/untrusted names (do not parse shell commands from labels).

Root ticket1 owns cached public inventory; ticket4 integrates these adapters into
persistent monitor and lifecycle. Producers own framing/reconnect/cleanup, owner
owns qualified resource bindings, cache, projection and tier scheduling. No worker
may change this shared contract without messaging primary and receiving a recorded
revision. Integration primary may adapt ergonomics causally with focused checks.
