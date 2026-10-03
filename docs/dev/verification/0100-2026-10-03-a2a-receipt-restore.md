# Plan 0107 receipt restore verification

Parent: Plan 0101 / issue #181
Branch: feat/p63-receipt-restore
Baseline: 24ddf11224a06c2b11764b66b8031be6242364c6
Outcome: exact restore and guarded no-dispatch publication accepted.

Receipt arms carry a nonsecret exact bus/root/message/actor-generation descriptor.
Restore uses separately supplied authority; descriptors do not open paths,
load capabilities or enroll actors. Mismatches are refused. Older descriptor-free
arms stay held. The source reconstruction registration requires an explicit
authority resolver and is not automatically in the production catalogue.

The daemon now requires an A2A source guard before publication. Loading the actual
old evaluator function body from the baseline commit reproduced the regression:
revoked cached receipts fired once instead of zero. The new guard keeps them
pending with or without a runner. This expected baseline failure is defect
evidence, not a flaky suite retry. Reopening the journal and reconstructing via
the source registry publishes one firing record; another poll adds none.

Focused: 50 receipt/registry/daemon tests passed in 2.944s; the additional denied
resolver fixture then passed in the nine-test receipt selection. Final full
suite: 824 tests in 48.520s, no failures or retries. Planning audit and diff check
passed. Isolated installed Python 3.12 receipt tests: nine passed in 1.134s,
module path verified in /tmp/codex-wake-p63-receipt-venv/site-packages.

Initial resource census: descriptors 4 -> 5, children 0 -> 0. Inspection found
the added descriptor was /dev/urandom. With imports/os.urandom initialized before
baseline, nine installed tests passed in 1.127s: descriptors 5 -> 5, children
0 -> 0. Preserve both samples; this is bounded fixture evidence, not a soak.
All bodies/actors/roots are synthetic; dispatch disabled, no service effects.

Remaining: production authority resolver/configuration, long-suspension CLI and
installed process restart; safe notification, named agents, lifecycle/multiroot
resource soak, supervisor, migrations/rollback and release. Memory disposition
unavailable; no authorized healthy Graphiti write path.
