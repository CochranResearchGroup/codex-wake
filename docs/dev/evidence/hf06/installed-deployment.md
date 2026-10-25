# HF-06 installed candidate acceptance — 2026-10-25 UTC

Operator explicitly requested deploying/installing PR327, proving goal limits
and self-refresh, then examining the bugfix tickets. This is an immutable PR
candidate installation, not a public release or a main-merge claim.

## Installed identity and rollback

Installed source commit `7a52339d2efde008d2e337fd2058b7d271a2f96a`, version0.21.0,
prefix `/home/ecochran76/.local/share/codex-wake/releases/0.21.0-7a52339`.
Wheel SHA256 `8b178cedd15e61bda276bf82ad05501631df75d0b3a1c787eee9533d1234ac79`;
all135 source Python files match installed files. Five user command symlinks and
both complete skill trees updated. Prior0.20.1 prefix remains intact.

Private operator evidence/rollback directory:
`/home/ecochran76/.local/state/codex-wake/deployment-backups/0.21.0-7a52339/`.
It retains prior links, config, profiles, units, skills and campaign invariants;
no private file bodies or raw native transcripts are copied into this repository.

The exact goal controller was handed over using a25-second maintenance permit.
Final permit state `replaced`; its replacement generation matches the new fresh
controller. Both goal-limits and shared-refresh services now run the candidate
prefix (previous refresh monitor was0.19.0). Other services and the shared native
daemon were preserved. All five existing campaign invariants match before/after:
limits, charges, deadlines, generations, allocation, accounting basis, latches and
first-stop evidence. No resource renewal, automatic goal resume or latch repair.

Explicit common-policy adoption revision1 retained both legacy caller/profile
ceilings and found zero unresolved pending intents. Lifecycle owns the canonical
policy; goal-limits is bound to it. A dedicated private operator policy bus was
provisioned. The minimal permissive policy grants no shared-reload approval.
Codex Wake's future MCP configuration now selects the canonical common root;
other server settings remain unchanged. Existing connections are still cached.

## Acceptance results

All runs use the installed candidate interpreter and owned disposable roots.

| Check | Result | Boundary |
| --- | --- | --- |
| Native public self-enrollment and successor continuity | PASS;6 localhost HTTP requests;40 cumulative tokens;original deadline and unrelated control preserved | Native caller attestation into actual public MCP;local Responses fixture;zero external provider calls |
| Native idle-goal controller stop | PASS;zero model turns | Exact owned disposable native goal;active-turn behavior excluded |
| Native active-turn controls and operator reply | PASS;4 localhost HTTP requests | Actual native checkpoint/pause/interrupt;operator reply preserved;no real billing/delegation proof |
| Two-thread shared MCP reload | PASS;zero model turns;4.046seconds | Private native server and watcher;does not prove invoking-session-only refresh |
| Current-session installed configuration | Permission allow at revision1;current_connection capability unsupported | Authenticated operator CLI inspection;no refresh queued |
| Existing connected MCP configuration | Still refuses exact host caller/scope setup | Proves the old connection has not been refreshed |

Scripts: `goal_supervision_native_enrollment_qualification.py`,
`goal_supervision_native_idle_qualification.py`,
`goal_supervision_native_active_qualification.py`,
`shared_refresh_acceptance.py`. Their exact result.json records live beneath
`/home/ecochran76/.local/state/codex-wake/hf06-*qualification/` and
`hf06-installed-refresh-acceptance/`. Fresh OS checks found no surviving owned
qualification native/watcher processes. Production service PIDs remain active.

Retained failed diagnostic: the older injected Unix-protocol
`goal_supervision_qualification.py` fixture crashed on unexpected
`thread/turns/list`; it did not qualify enrollment. Its original traceback is
retained in `goal-qualification.log`. The independent native runs above passed;
this fixture failure is neither erased nor presented as a production defect.

## Open bug boundaries

#318 remains OPEN. Fresh installed CLI reports own-session permission correctly,
but self-refresh profile execution is shared-server scope. The current installed
Codex CLI is0.164.0; its freshly generated experimental ClientRequest schema
still defines `config/mcpServer/reload` with null params and no thread/server
selector. No shared reload or guessed client replacement was attempted on the
operator's sessions. Existing legacy resource proofs also name old versions and
fixed callers; updating expected values without proving actual reconnection is
not refresh acceptance. Repair exact connection/client execution first.

#319 remains OPEN. Healthy enrollment, ordinary stopping and continuity passed;
observation-fault recovery execution remains unsupported. These checks never
clear a stop or prove timeout recovery. The retained production campaigns are
now past their original deadlines, so they must not become recovery test cases
or receive an inferred allowance. Use a fresh isolated campaign to inject the
fault and prove authorized same-allowance recovery plus attributable episodes.

#310 remains open until the installed public connection and requested workflow
are accepted. Installation and healthy fixtures do not close any of these gaps.

Memory disposition: forbidden; no explicit user memory-write request.
