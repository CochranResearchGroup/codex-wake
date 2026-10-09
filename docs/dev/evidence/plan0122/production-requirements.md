# Production time acquisition qualification

Date: 2026-10-08. Parent: Plan0122. Branch: feature/network-time-consensus.

## Investigation boundary

Question: what evidence is still needed to admit Netnod/PTB alongside Cloudflare/NIST, and how should acquisition authenticate replies and measure age on WSL?

Primary sources only: operator documentation, IETF RFCs and Microsoft API documentation. Bound: three targeted search rounds and focused official-page reads, ending when admission decisions and unresolved questions can be stated. No operator contact, system configuration, new live probes or production rollout. Previous four-provider replies remain reachability evidence only.

## Findings

**Four diverse operators is a sound target.** [RFC 8633 section 3.2](https://www.rfc-editor.org/rfc/rfc8633.html#section-3.2) recommends at least four independent diverse sources and explicitly describes a two-versus-two disagreement caused by mixing smeared and conventional UTC. This supports the existing target and uncertainty rule; our bounded interval selector is not claimed to implement the full RFC NTP algorithm. Operator diversity alone does not prove independent reference hardware or network paths.

**Netnod's current leap profile remains unresolved.** Its [2015 first-party announcement](https://www.netnod.se/news/leap-second-added-to-the-global-time-scale) documents stopping its NTP service around that leap second and restarting afterward. That establishes historical behavior, not today's no-smear guarantee for every endpoint. Its [current NTS documentation](https://www.netnod.se/netnod-time/how-to-use-nts) lists `nts.netnod.se` and regional NTS endpoints. These are different names from the earlier `ntp.se` UDP probe. NTS reachability and explicit current time-scale policy still require qualification. No absence-of-search-results inference is accepted.

**PTB supplies public NTP and documents NTS.** Its [official NTP service page](https://www.ptb.de/cms/en/ptb/fachabteilungen/abt9/gruppe-95/ref-952/time-synchronization-of-computers-using-the-network-time-protocol-ntp.html) lists public endpoints and an NTS service without registration. A later focused fetch timed out; the earlier successful official-page retrieval supplied the service statement. Neither that statement nor PTB's general UTC explanations explicitly establishes endpoint leap-smearing policy. This remains an admission gate, not evidence of incompatible behavior.

**Authentication is available, but cannot be inferred from plain NTP replies.** [Cloudflare NTS documentation](https://developers.cloudflare.com/time-services/nts/) supports NTS at `time.cloudflare.com`; Netnod and PTB also document support. We have not qualified an NTS endpoint for NIST. [RFC 8915 sections 8.5–8.7](https://www.rfc-editor.org/rfc/rfc8915.html#section-8.5) covers certificate-time bootstrap, delay attacks and downgrade risks. Authentication does not eliminate latency uncertainty. Missing NTS must never be silently relabeled authenticated.

**Windows elapsed timing can be separate from Windows UTC health.** [Microsoft's QPC documentation](https://learn.microsoft.com/en-us/windows/win32/sysinfo/acquiring-high-resolution-time-stamps) states that QueryPerformanceCounter includes sleep/hibernate and its frequency is fixed during system operation. This supports a candidate WSL elapsed-time source even when Windows wall-time fallback is excluded. It does not prove our collector/interop path correct. Counter readings must bracket acquisition in the same counter domain; subtracting Linux and Windows readings is invalid. Both host and guest boot identities, collector generation, interop delay, suspend and process restart require validation. Unbounded delay or unknown age must yield time uncertainty.

## Recommended implementation contract

Retain Plan0122's network-first consensus and healthy consistent Windows fallback. Separate these admission checks:

1. Reviewed operator and endpoint identity plus explicit time-scale profile. Unknown profile stays disabled; ordinary agreement and leap-indicator zero do not establish a no-smear policy. A live qualification command may show disabled candidates and their reasons.
2. Transport validation and an explicit per-source authentication policy. Prefer an established NTS implementation behind the acquisition interface; decide its packaging with a bounded read-only runnable spike. No new crypto implementation, automatic TLS-validation bypass or silent NTS-to-NTP downgrade. NIST's current plain-NTP evidence remains explicitly unauthenticated. Whether to admit it for deadline effects is an explicit unresolved policy decision, not a research finding.
3. Trustworthy duration and common-instant normalization. On WSL, evaluate host QPC bracketing with conservative transport/interop bounds. Never promote the prototype's Linux raw timing into production by assumption. Exclude stale evidence and invalidate cached observations across host/guest restart or unknown resume state.
4. Explicit numeric policy values with rationale, failure diagnostics, rate limits and retry/backoff. Existing pure-core test values are not production defaults. Preserve UTC deadlines; pause time-dependent effects when bounds cannot settle them.

The reliable first deliverable is an inspection-only acquisition path that reports bounded consensus or a specific unresolved reason. Production deadline effects require the additional qualification gates. Research has narrowed the questions, not completed four-provider production admission.

## Proposed execution breakdown

The user approved this breakdown; canonical tickets are Plans0123–0126 under `docs/dev/plans/`. The numbered proposal below is retained as research history, not a competing status authority. Each draft is a complete verifiable user behavior; there is no separate schema-only or adapter-only ticket.

1. **Inspect network time without changing the system clock.** No ticket blockers. Operator can run a bounded inspection command and see qualified network consensus or per-source exclusion reasons. Includes acquisition, normalization, configuration, NTS packaging spike, explicit authentication/time-scale admission, numeric policies and deterministic fault tests. At least two independent admitted sources must be demonstrated before production candidacy; all four candidates remain visible, and unknown profiles stay disabled.
2. **Use healthy Windows fallback during network outages.** Blocked by 1's acquisition/inspection contract. The same inspection path demonstrates fallback, health exclusion, stale evidence and conflict behavior. Windows synchronization health and UTC uncertainty must be independently justified; running service status alone is insufficient. No network tie can be broken by Windows.
3. **Keep mailbox deadlines usable through time uncertainty.** Blocked by 1; not by Windows fallback. A temporary mailbox can create, inspect and cancel while time is uncertain; expiration and time-dependent delivery wait, then recover automatically with original deadlines. Includes versioned migration/rollback design, multi-process fixtures and unchanged live-store custody. Read-only operations do not mutate guarded time anchors.
4. **Prove wake behavior across outages, sleep and restart.** Blocked by 2 and 3. An isolated wake/mailbox workflow persists a request, observes deterministic due/pending/uncertain transitions, inspects the resume payload, and verifies cancellation and no early firing. Includes installed-candidate entrypoint proof against disposable state, fault-injected boot/resume cases and a separately authorized actual sleep/restart acceptance run if needed. Document release/migration steps; no live rollout is implied by ticket completion.

Critical-path owner: primary agent. Ticket 1 is the first frontier. After 1, tickets 2 and 3 can progress independently with low overlap if their public inspection contract is frozen. Ticket 4 is serialized reconciliation. Detailed source locations belong to implementation discovery, not this ticket breakdown.
