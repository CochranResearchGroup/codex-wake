# Goal usage accounting seam

Public seam: `goal_usage.observe_usage(home, thread_id, original_goal_created_at,
reset_anchor=None)`. Focused sanitized 0.163-shaped fixture tests: 10 passed
(`PYTHONPATH=src pytest -q tests/test_goal_usage.py`). Red receipts observed for
missing module, inherited-child doublecount omission, reset omission, ambiguous
active creation boundary, incomplete response coverage, referenced history and
wrong goal identity; each required change reached green within two attempts.

Source basis: OpenAI codex rust-v0.163.0 core/src/session/mod.rs 1729–1742 seeds
fork counters from inherited records; state/session.rs219–251 then adds response
usage. Protocol `TokenUsageRecord` identifies original thread, response, turn,
root turn and session. Per-response `usage.total_tokens` is cached-inclusive;
no discounted goal display counters or inherited cumulative maxima are charged.

Counts exact response identities once across recursively discovered children.
Copied parent records must agree byte-semantically and belong to the discovered
ancestry. Goal-boundary creation during an active turn, absent original goal
marker, unresolved descendant spawn/rollout, missing raw-response usage,
conflicting records, unattributed root turn and malformed/truncated files hold
unknown. A first active task without a usage record also holds unknown.
Referenced/paginated history and root forks deliberately hold unknown: this
slice does not claim complete history traversal or live delegated acceptance.
Scanning is confined to the explicit host-authorized CODEX_HOME/sessions; a
malformed unrelated rollout conservatively holds because ancestry is unavailable.

`anchor` contains version1, original thread/goal epoch, original creation ISO
boundary, a complete observed response identity set and hashes. A host-authorized
allocation reset passes that fixed snapshot as reset_anchor; later observations
subtract only those exact unchanged responses. Returned anchors are snapshots,
not authority to reset. Native replacement goals do not change the original
boundary. Missing/changed anchored history holds unknown. Controller must never
replace its fixed reset baseline on every poll. Observation is sampled, not a
claim that in-flight provider spending has already been published.

Effect-free readback against owned /tmp/cw166-r immutable artifacts reproduced
source-after-goal0 and successor-after-goal90477; this is historical readback,
not a new model call or delegated live acceptance. No native/service/provider
effects or other source edits were performed.

Memory disposition: forbidden; this bounded lane authorizes source/tests/evidence
only and no external memory writes.

## Metadata-first refinement

Unrelated rollout history is no longer parsed. Inventory reads at most the first
64KiB metadata line per regular nonsymlink JSONL file, discovers root ancestry,
then loads root/descendant history only. Missing root/claimed child metadata
still holds; unrelated malformed body history does not invalidate a known graph.
Hard scan bounds:4096 directories/files,4MiB total metadata,32MiB relevant history,
2seconds monotonic cooperative processing budget. Exceeding a bound returns
unknown rather than guessing or allocating unbounded history. Synchronous local
filesystem calls cannot be preempted by this cooperative deadline; no hard wall
clock promise is made. Referenced-history support remains deliberately absent.

Regression red: unrelated ~20MB corrupt history previously produced unknown.
Green: excluded body leaves exact root40 tokens. Converted existing tests (not
duplicated) to unittest.TestCase/TemporaryDirectory so repository CI discovers
all11 tests. Validation: `PYTHONPATH=src /tmp/cw167-tools/bin/python -m unittest
discover -s tests -p test_goal_usage.py -v` =>11 passed. No provider/native effects.
