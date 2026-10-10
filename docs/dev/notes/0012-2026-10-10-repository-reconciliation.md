# Repository reconciliation — 2026-10-10

Root main retains policy commit86f18ba and merges released origin/main38c74f3
plus native time planningf845e39. The five previously untracked notes were committed
byte-for-byte as historical snapshots; their current-state statements are historical,
and ROADMAP/current plans govern. Source and tests are unchanged from released main.

| Checkout | Exact preserved tip | Disposition |
| --- | --- | --- |
| app-server-lifecycle | 4bc47187aee17732e9b3aa9c1a9d6015a83c6c5a | Closed, paused unmerged transport; outstanding review/CI and installed acceptance |
| native-session-prototype | 4c1907eec19e3af25023257e8dfb65968421d1db | Closed, superseded prototype; raw evidence archived |
| plan122-integration | 6b822fad50209e217c79c6ab796b141c9f5258b2 | Closed, integrated ancestor of released main |
| time-prototype | e4f742b14f4eb7302e227f330e6cc623a6979610 | Closed, released successor supersedes snapshot; no stale merge |
| plan127 | f845e392f04b2032c706b208d10d52ec1ed96fec | Planning merged; checkout retained because live processes use its directory |

Each exact tip has matching local/remote archive/reconcile-20261010-* custody:
app-server-paused, native-prototype, plan122-integrated, time-prototype,
plan133-planning. Root policy has root-policy archive custody. Original named
branches are retained. No forced removal, branch deletion, process termination,
clock operation, runtime migration or package/service change occurred.

The Plan0127 checkout can be removed normally after its owning sessions/processes
leave it. Do not kill those processes solely to finish repository tidying.
Plan0133 remains PLANNED; only ticket0134 is ready. P63 stays OPEN.
