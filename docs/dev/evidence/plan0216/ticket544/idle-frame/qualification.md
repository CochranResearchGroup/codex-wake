# Decode rows only when a monitor consumer needs them

Base61665a89 plus consumer edge dependency0abec5da (root already integrated it).
Root should cherry-pick only this packet's final observer/monitor commit.

The measured true-idle packet still failed the1% gate at1.296%. Its retained warm
profile had no inventory refresh:10ticks consumed.053s, JSON decoding53calls.043s,
monitor saves13calls.039s. baseline-profile.txt is the bounded source-profile
readback. This packet removes resource decoding from unchanged internal ticks;
it does not change the default one-second observation cadence or any threshold.

TabObserver.tick defaults to materialize=True, preserving independent public
resource arrays. Its internal materialize=False form returns metadata, revisions,
resource count and diagnostics without decoding rows. materialize_resources uses
the prepared canonical JSON to return fresh independent objects, stamped with
that same frame's observation time. No caller receives mutable canonical data,
and no lazy container or custom serialization type is introduced. Unchanged
revision preparation also returns before traversing/rehashing resource records;
source loss and expiry still invalidate the aggregate.

The existing monitor owns a same-loop ensure_resources closure. The first consumer
that actually needs rows fills the frame once; later consumers share that owned
frame. Publication calls it only when evidence/display changes or the bounded
heartbeat requires a full write. Formatting's existing callback hook calls it
only after its quiet-cache gates; its separate dependency also loads expired or
legacy frames before computing a fallback key. Routing calls it only after enabled
rules, deadline and host-owner gates. Diagnostics and inactive policy/routing paths
do not request rows. Both publisher and enabled routing reject missing arrays;
metadata-only frames are never serialized as full inventory.

## Focused source checks

Public regressions against the base fail because the explicit deferred-frame and
publisher-loader APIs are absent (public-red.txt). The existing CPU hard-gate
failure remains the performance red; API tests are not described as a CPU proof.
Final selection/identities/counts are retained in python311.json/python312.json.
Checks exercise:

- Default public tick arrays and deferred decoding preserve nested caller mutation
isolation and source-loss state.
- Quiet publication never invokes its row loader; evidence change and heartbeat
invoke it exactly once, and a missing loader cannot overwrite full persisted data.
- A real private daemon with enabled routing moves a newly created owned tab and
persists all3resource rows in a fresh snapshot. Existing automatic formatting and
cached/expired-key callback tests protect the other consumer path.
- Existing retained control-size, human uncertainty and monitor lifecycle behavior
remain covered. No close/process/ownership token behavior was changed.

Ruff F821/F822/F823 and whitespace checks pass. New exact installed resource
qualification is still required after combining root's batching and formatter
packets. No CPU pass is claimed here. No provider turn or production effect occurred.

Memory disposition: forbidden; no explicit memory-write request.
