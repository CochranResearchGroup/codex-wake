# Plan 0120 — WSL time consensus prototype

State: CLOSED
Branch: prototype/wsl-time-consensus
Owner: primary agent
Scope: agreed clock contract and isolated interactive simulation.

## Current State

Windows-first time, two independent network sources, network consensus overriding a disagreeing Windows source, automatic uncertainty/retry, and sleep-inclusive deadlines were agreed in conversation. Prototype is captured and its eleven guided action sequences executed under Node; scenario outcomes are preserved in prototypes/wsl-time-consensus-walkthroughs.jsonl. Production remains unchanged. Research notes 0008 and 0009 in the original checkout preserve the preceding measurements; their clock-setter attribution remains unresolved.

## Contract

- Prefer a fresh Windows observation when no accepted network consensus contradicts it.
- Two fresh, independently administered network sources may establish consensus and override Windows. Distinct hostnames alone do not establish independence.
- A lone network source does not establish network consensus.
- When available fresh sources conflict without consensus, hold time-dependent effects and retry automatically.
- If no network sources are available, fresh Windows time remains usable; network availability is not a prerequisite for the primary source.
- Sleep counts toward wake deadlines and message expiration. Recovery reevaluates the original deadlines; it does not extend them by the outage duration.
- Accept only fresh observations after restart. Preserve deadlines; do not reuse old observations as fresh or compare counters across boots.
- Treat accepted time as an interval. A deadline is definitely due only when the lower bound reaches it. If the interval straddles the deadline, hold that effect until the evidence resolves it.
- Read-only inspection and cancellation should remain available during uncertainty. Pause only time-dependent decisions, not all operations.

## Prototype choices, not production defaults

The demo starts with a 1-second maximum combined interval width for network agreement and a 30-second sample freshness budget. Both are adjustable. Observations carry explicit uncertainty. Pair consensus uses the conservative union of their intervals and rejects overly wide unions. Independent network-source labels are supplied inputs, not verified properties. Conflicting Windows plus one network source pauses. Cached observations conservatively widen their upper bound by simulated age; their lower bound never advances without a fresh sample. They age out after the freshness budget. Actual elapsed-age measurement and oscillator bounds remain adapter qualification questions. No system clock is set.

## Acceptance and definition of done

Single-file interactive demo exposes full state, free play and ordered scenario walkthroughs. Exercise agreement, Windows outlier, one-server outage, total outage/recovery, disagreement, sleep, restart, stale samples, deadline boundary and duplicate-provider rejection. Record scenario outcomes. Preserve prototype on its branch; do not integrate it into production.

## Non-goals and limits

No NTP client, real Windows bridge, system-clock repair, live mailbox reconciliation, scheduler migration or release. Sleep/restart are simulated. Protocol authentication, leap-smear compatibility, source independence, response-delay uncertainty, interop bounds and production parameter selection require a later adapter qualification packet. Two agreeing servers are a policy quorum, not proof of absolute canonical UTC.

## Next bounded packet

Qualify real read-only Windows and network adapters, including latency bounds and protocol validation. Wire into production only after separate implementation and persisted-state migration work.

## Validation and custody

The exact pure module embedded in the HTML was extracted and its eleven guided sequences executed under Node with exit zero. Outputs matched the documented scenarios; these are walkthrough executions, not a production test suite. UI browser rendering and real sleep/restart were not independently exercised. Original checkout dirty files were not moved or committed. The prototype and contract are retained together on prototype/wsl-time-consensus, locally; no remote publication or product integration is claimed.

Memory disposition: unavailable — no reviewed Codex Wake Graphiti group in established context; record a non-write receipt against this plan.
