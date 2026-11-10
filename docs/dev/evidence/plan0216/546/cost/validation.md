# Formatter cost repair: qualified functional change, resource gate remains open

Base source `4c15717dfa780259362584cd10431516d26a68e9`. This bounded repair
responds to actual public TabMonitor.serve measurements under UID1017 with all
observation tiers enabled, Slate formatting and 100 real private tmux panes. No
production monitor, tabs, provider calls or formatting settings were changed.

The initial actual-serve profile identified 66 formatting state saves in about
23 cycles, consuming 6.129 seconds under profiling. Python json.dump generated
3.3 million TextIOWrapper.write calls, with 5.794 seconds in the streaming JSON
path. Session formatting read/write operations also launched native processes per
option rather than per finite metadata operation.

Changes:

- Serialize the same private state through C-backed json.dumps and one write,
  retaining flush/fsync plus atomic replacement.
- Save new original baselines before their first native effect. Existing durable
  baselines need no redundant pre-write checkpoint when no window writes occur;
  settled refreshes checkpoint once instead of three times.
- Batch the existing finite managed session option writes and complete explicit/
  effective readbacks through the native metadata batch boundary. Quiet missing
  options retain absent/inherited semantics, with no new native command surface.
- Retain one small formatting result on the existing host owner. Semantic trait,
  source availability/epoch, physical target/window and backend changes project
  immediately. Sample timestamps do not trigger redundant native work. Any
  formatting state-file replacement invalidates pause/rollback/policy/resume
  immediately. A five-second forced refresh renews the existing 20-second shared
  lease and continues bounded native custody audits. Failures are never cached.

Red/green evidence at public boundaries:

- Recreated/settled host refresh initially started seven native processes; the
  finite metadata budget test failed before batching. The repaired public path
  uses at most six processes and one durable flush, including current physical
  qualification and complete readback. A recreated public owner ensures the
  semantic memo cannot hide the lease-renewal cost in this test.
- A repeated event tick with only sample time changed initially started three
  native processes; the new public regression failed before semantic memoization.
  It now makes zero native calls. The same test checks immediate running-status
  and source-loss projection and immediate external rollback recognition.
- A separate clock-boundary test proves renewal resumes after five seconds and
  the native shared lease remains valid. Native wall clocks and transport
  deadlines remain real in this test.
- The three focused resource/renewal tests pass on Python 3.11 (0.628s) and Python
  3.12 (1.133s). A 57-test formatting selection passed Python 3.12 in 20.779s
  before the final lease-boundary test was added. The parent owns the final
  affected selection after the combined resource candidate is stable.
- Undefined-name lint and git diff --check passed. Hosted CI was skipped under
  the repository cost policy.

Measured partial gains, not gate acceptance:

A source-override diagnostic after serialization/checkpoint/batching changes
measured idle 6.694% and active 7.295% of one core over ten seconds each. A fresh
same-source profile confirmed state saves dropped from 66/6.129s to 33/0.226s;
remaining formatter refresh 23/3.722s and 545 total native subprocesses motivated
the semantic-dirty change rather than another speculative serialization change.

The second source-override diagnostic, adding the semantic memo while retaining
original cache code, measured idle 4.797% and active 8.390%. Both **fail** the
unchanged 1%/5% resource caps. All 20 active events projected, aggregate RSS peaked
at 45.05MB and no owned control processes remained. The 1Hz publication sampler
can alias the 1Hz daemon, so its roughly two-second latency upper bound is not a
precise receive-to-projection latency measurement. The final helper must sample
publication more frequently without changing daemon cadence.

The selected raw measurement fields are retained in the two diagnostic JSON
receipts. These source-override, ten-second runs are neither immutable installed
package acceptance nor the required 60-second gates. The ticket remains open
pending parent cache/scheduler integration and the actual installed full gates.
No threshold was relaxed. No broad review, tracker closure, merge or deployment
was performed. The primary owns the final memory disposition.
