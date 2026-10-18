# Shared native-home accounting locator repair | F2

The4096-file fallback cannot serve the normal shared home (>4748 rollout files).
Raising inventory limits alone still exhausted the2second processing budget.
Native0.163 owned fixture schema establishes `threads(id,rollout_path,source)`
and `thread_spawn_edges(parent_thread_id,child_thread_id,status)`.

Read-only fast path opens state_5.sqlite with URI mode=ro, query_only,0.2second
busy timeout and SQLite progress deadline. It deliberately does NOT use immutable
because committed WAL rows must remain visible. Native shared-home state database
and sessions directory aliases are supported through canonical owned DB and
approved resolved sessions root. No database writes, checkpointing, native calls,
credential reads or unrelated conversation-body reads occur.

Only bounded id/path/source ancestry metadata is selected (65536rows/64MiB cap;
spawn edges also capped). Recursive descendants are selected, canonical metadata
of ONLYroot+descendants is read, then existing bounded history validation runs.
Index metadata cannot establish spending: canonical ID/source/parent must match,
all paths resolve beneath approved sessions, canonical spawn claims must have
actual discovered children, and response accounting remains unchanged. Native
index is a locator, never permission to substitute counters or assume zero.
Missing/incompatible index schema falls back to bounded metadata scan. Present
corrupt/unavailable query, missing indexed root/child, inconsistent canonical
metadata, unsafe path or incomplete descendant coverage returns unknown.

All existing resource bounds remain:4096relevant descendants,4MiBcanonical
metadata,32MiBrelevant history,2second cooperative processing deadline. Metadata
SQL rows are bounded separately. Slow synchronous filesystem operations still
cannot be forcibly preempted; no universal wallclock ceiling is claimed.

Regression: indexed4100unrelatedcorruptbodyrollouts+root40/child20 initially
failed usage_inventory_file_limit; now qualified60. Fixture leaves committed
native-index rows in a live WAL; mode=ro sees them. Deleting a required indexed
child and redirecting root path outside sessions each hold unknown. Existing11
unittest checks remain; requested focused command passes12 tests:
`PYTHONPATH=src /tmp/cw167-tools/bin/python -m unittest discover -s tests -p test_goal_usage.py -q`.

Authorized real-home metadata/stat qualification: current root is indexed and
rollout size19,741,542bytes (~18.83MiB), below unchanged32MiB. Initial stricter
index-symlink guard held in0.0002s; native home actually aliases state_5.sqlite
and sessions under its shared directory. After canonical alias support, requested
root/goal_created_at=0 observation reaches goal_start_missing in0.9783seconds,
instead of inventory/time limit. This does NOT assert that an actual currentgoal
is qualified or enroll/reset any allocation. Only requested root/ancestry metadata
was reported; no private conversation data is included here. Existing owned
native delegate fixture still qualifies90 via index in0.0063seconds.

Memory disposition forbidden: bounded source/tests/evidence lane only.
