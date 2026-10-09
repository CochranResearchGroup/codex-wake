# A2A readiness reconciliation — 2026-10-08

## Question and bound

What is already accepted, what is installed now, and what remains before the new network-time path supports live A2A? Primary sources: checked-in acceptance records/plans, candidate receipts and read-only installed-command/service readbacks. Stop after reconciling these three boundaries. No message send, private body read, guard reset, migration, installation, service change or new live acceptance is authorized by this research pass.

## Finding

A2A is an existing released feature with accepted automatic exchanges. The network-time successor is a tested isolated candidate, not the installed runtime. Neither statement establishes that a particular pair of agents is enrolled, bound, running a notification worker and currently able to exchange messages.

## Evidence

| Boundary | Evidence | Meaning |
| --- | --- | --- |
| Historical live A2A acceptance | [Verification0122](../verification/0122-2026-10-05-remaining-gates-and-native-soak-acceptance.md), requirement audit and native soak | Cancellation, automatic reconnect return, normal worker restart, released v0.7.1 exchange, cross-root enrollment/denial and full 1800.32296-second soak passed. Earlier failures remain preserved. |
| Retained A2A obligations | [Plan0119 current reconciled state](../plans/0119-2026-10-04-usable-live-a2a-successor.md) | Server-unloaded recipient and broader held-recovery cases remain open. The already accepted happy path does not need to be reimplemented. |
| Installed command identity now | `command -v codex-wake`, `readlink -f /home/ecochran76/.local/bin/codex-wake`, `codex-wake --version` | Stable user command resolves to `/home/ecochran76/.local/share/uv/tools/codex-wake/bin/codex-wake`; reports 0.7.1. Its Python package is under that tool's Python3.12 site-packages. |
| Installed capability now | `codex-wake a2a --help`, `codex-wake messages --help`, `codex-wake time --help` | A2A/message verbs exist. `time` is rejected (exit2), and `a2a` has no `network-time` verb. The new time path is not installed. |
| Candidate | [Plan0122](../plans/0122-2026-10-08-network-first-time-provider.md), [acceptance review](../evidence/plan0126/acceptance-review.md), [validation](../evidence/plan0126/validation.json) | Feature branch `feature/network-time-consensus` at 53ffcfc; 0.8.0 candidate, 950 regression tests, isolated installed workflow and three Windows cache controls passed. Plans0123–0126 are complete within isolated scope. |
| Current services | `systemctl --user list-units --all 'codex-wake*' --no-pager`; `systemctl --user show codex-wake-supervisor.service -p MainPID -p ExecStart -p ActiveState` | Supervisor active, PID21521 at observation, using stable user CLI. Several repository wake daemons run. No A2A/Plan119-named worker appeared in the unit readback. This does not exclude an independently launched worker and is not proof of mailbox readiness. |
| Git custody | `git worktree list`, clean candidate porcelain | Main86f18ba; candidate53ffcfc in `/home/ecochran76/workspace.local/codex-wake-time-prototype`. Main's three unrelated untracked notes preserved. No merge/push or installed upgrade performed in this pass. |

The installed [codex-wake skill](/home/ecochran76/.codex/shared/skills/codex-wake/SKILL.md) specifies the actual operational prerequisites: exact-thread enrollment, actor capability, actual-client opt-in/binding, bounded notification worker and sender receipt delegation/arm for suspend-and-reply. Stock Codex transport does not require a patched executable. No particular live mailbox, capability or binding was selected in this pass; therefore no current guard, transport or recipient readiness verdict is claimed.

## Exact next packet

Continue under Plan0122 with a bounded integration/activation packet; retain Plan0119's separate exceptional-recovery scope. Before any effects, establish the exact target bus/root, installed reader identities, enrolled threads/bindings, worker ownership, recovery state and unchanged guarded checkpoint. Do not infer this state from the supervisor or old acceptance.

Then integrate/review the candidate on the repository's normal release path; qualify a backup and install/rollback boundary; explicitly migrate only the selected healthy, quiescent mailbox. A legacy clock anomaly or disagreement blocks migration. The existing candidate cannot clear it, and this research does not authorize resetting it. If the selected store is held, prepare a recovery decision rather than treating migration as a repair. A separately enrolled disposable bus can prove delivery without claiming recovery of the held store.

Finally verify one bounded automatic exchange: A admission, exact existing B notification/read/reply, A suspension and automatic correlated return, unchanged deadlines and zero duplicate/uncertain transport attempts; inspect and terminate only owned test workers. This is acceptance of the new time path on real sessions, not the first proof that A2A exists.

Additional providers and NTS are useful follow-up qualifications, but they are not an inherent blocker to the candidate's explicitly accepted two-provider plain-NTP mode. That mode has reduced outage redundancy and no hostile-network authenticity. Keep those limitations explicit; do not require unrelated source research before checking the desired live workflow. [Candidate release/migration/rollback contract](../release-notes/0.8.0-network-time.md).

## Reconciliation

The roadmap's P63 paragraph was older than Plan0119's current accepted state; updated it to that authority. Plan0122's next action now distinguishes candidate activation from optional trust/redundancy expansion. No new shadow plan or implementation ticket was created. Remaining work is an integration/activation packet, with exact runtime/guard evidence needed before dependent effects.

Graphiti discovery skipped: current primary acceptance records and current runtime readbacks answer the bounded question directly; no advisory memory needed. Closeout disposition unavailable: no reviewed Codex Wake Graphiti target group established. Tests not rerun: documentation/read-only research only.
