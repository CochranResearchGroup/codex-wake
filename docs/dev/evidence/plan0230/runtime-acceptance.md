# LOCAL-P230 installed native acceptance

Product source integrated via PR600(eac0d01e), PR605(45a66b19), and
PR606(17e2c3fe57592fa8f071a30c6f885a9cc48258df). Active installed version:
0.22.0.dev18, qualified wheel5e2628144087730f55e8dbcaaea199df95d66fe508a5c74e864491aae7d860de.
324payload files equal the fetched integrated product source. Five Wake entrypoints
and the exact participant notification worker use the qualified package; worker
is active with opt-in automatic tmux discovery. Original rollback snapshots and
attributable synthetic-message receipts are retained in user-scoped P230 deployment
artifacts, outside Git. Native daemon/build, goals, grants and host clocksource were
not changed. The production bus's existing compatible network-time policy remains.

## Observed real-native outcomes

| Case | Result |
| --- | --- |
| First contact to new recipient | Actor count0 before contact; no recipient mailbox poll or manual binding; admission, automatic binding, native queue submission, read, accepted claim and completion observed. |
| First client replacement | PID and binding generation refreshed automatically; narrow wrapped footer exposed composer_protected. Earlier notice exhausted3 proven-unsent attempts and remains failed; cancellation was refused as already terminal. No reset/replay. |
| Final client replacement after footer correction | A second replacement changed PID; binding generation refreshed automatically; fresh post-fix notice submitted/read/claimed/completed in approximately42s, with no manual binding. |

Both acceptance sessions were newly created real native conversations. Only their
owned diagnostic tab was opened/replaced/closed. The final receipt chain and
binding-generation observations were independently read back by the primary.
The two new diagnostic actors were retired and their one binding removed after
completion; conversations, historical failures and receipts are retained. No
business/company/customer fixture was created.

## Clock and compatibility boundary

StableTime MCP and the installed adapter returned finite qualified NTS evidence
from Cloudflare and Netnod. The earlier smoke failure used a newly created legacy
bus, while production was already network-time based. The same installed mailbox
workflow with --stable-time passed, including operator retention checks. No host
clocksource change or guest-clock guard relaxation was needed.

The optional stronger StableTime-required policy is implemented/tested, not applied
to the existing production bus: older loaded readers reject it. The existing
configured adapter already selects StableTime. A future pin activation requires
upgraded readers and a quiescent/qualified migration; it preserves checkpoints and
holds outstanding legacy work rather than reinterpreting deadlines.

## Validation and remaining loaded-connection boundary

Dev16 exact installed baseline:163focused tests PASS102.398s, plus the StableTime-
backed installed mailbox smoke. Final dev18 changed-surface selection:
test_a2a_tmux_delivery + test_a2a_delivery,26PASS4.435s. The full dispatcher-to-native-
queue regression was red explicit_not_sent before the last metadata call was fixed.
Previous parser/probe-only tests did not protect that call site; evidence is retained.
No full-suite, combined-count, Python3.11 or hosted-CI claim. Source/policy wiring
and whitespace checks pass. All source changes have remote custody on main.

Existing loaded MCP processes retain older interpreters until normal reconnect.
Fresh connections use the new entrypoint; participant delivery is already updated.
Readback found61 loaded MCP processes across earlier prefixes. Installed effective
permission marks refresh.shared approval_required. An idle-only shared refresh was
presented separately; no shared connection reload, daemon restart or goal reset was
performed. Do not claim all loaded callers have reconnected. This boundary is
separate from the verified new-session and replacement-client acceptance above.

Core P230 implementation and installed participant acceptance complete. Loaded-
connection rollout remains a separately governed maintenance action. Memory
forbidden: no external memory write authorized; machine-readable non-write receipt
retained privately.
