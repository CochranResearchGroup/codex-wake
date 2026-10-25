# Native dependency for issue318

`318-thread-scoped-mcp.patch` is a reviewable native Codex proposal based on
commit `bdd282f3bbd55df3a869a5438519cd948c134d4d`. Apply it at the native repository
root with `git apply PATH/318-thread-scoped-mcp.patch`, then build the app-server
or CLI through that repository's normal workflow. This is not an upstream merge,
official native release, or automatic daemon upgrade.

It adds exact loaded-thread MCP reload with a non-mutating `dryRun` scope probe,
and `runtimeOnly` catalog inspection of that loaded manager. Default legacy
configuration inspection remains unchanged. Explicit scoped operations apply an
admitted pending refresh without requiring a model turn. The response acknowledges
admission; actual resource/goal proof remains mandatory.

Wake0.21.2 uses profile mode `thread_mcp_idle` and permission `refresh.connection`.
A successful native scope probe is required before support or admission. An older
running daemon remains unsupported even after installing the Wake wheel. There
is no shared reload, guessed client, new-thread or daemon-restart fallback.

Behavior revision `a50f43518c10e5cb94271dc484c97a973067311e` passes the native
protocol254 tests, seven affected app-server cases including the new two-thread
regression and existing executor behavior, and the isolated installed-native/Wake
workflow. Its selected Wake process upgrades0.21.1→0.21.2 while the peer stays on
0.21.1, both goals remain unchanged, and zero model turns occur. See the canonical
[evidence](../../docs/dev/evidence/hf06/318-scoped-refresh.md).

The broader native run is not green: hook startup and safety-check notification
cases remain unclassified after serial reruns. Do not treat scoped qualification
as whole-native release qualification. Current production daemon activation and
refresh of the requesting session remain outstanding. Local development binaries
are staged separately and do not replace the shared native daemon.

Final formatting revision: `6115475dd95f6ffd525992bd5f98051d543a4c68`.
Scoped Clippy fix/check and final formatter pass. Behavioral tests ran before
those final formatting steps, as required by the native repository workflow.
