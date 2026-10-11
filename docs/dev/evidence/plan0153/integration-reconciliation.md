# Approved setup and StableTime reconciliation

Operator "ok go" approved both prepared setup/default-label and retained adapter
publication scopes. The six docs/agents files, AGENTS routing, registry and missing
four provider labels are applied. Existing labels retained. Issue243 has exactly
bug/ready-for-agent; no external issue was altered. AGENTS pilot hash refreshed
and wiring passes. Earlier no-commit setup draft is superseded by the operator's
integration authorization; deployment proceeds only after refreshed qualification.

Root main holds a concurrently developed pending_time schema6 candidate. Its
own release note explicitly starts the full relative delay at first qualification;
that conflicts with F4's original-expiry requirement. It also defines a different
schema6 representation. It is preserved (root dirty files and private raw patch/
untracked snapshot), not merged or installed. Malformed records still hold.
Do not replay incident attempts or infer either candidate was deployed.

The current four StableTime adapter files are admitted intact from root:
stable_time.py, time_inspection.py, time_provider.py, test_stable_time.py.
This includes contract2.0 support and removal of the old blanket one-second bound.
Native contract parsing follows ../wsl-time/src/client.rs: finite authenticated
bounds permitted, best-effort ignored for UTC authority, bounded native QPC,
canonical epoch, independent operators, generation and acquisition freshness.
Contract1.0 still requires below100ms; contract2.0 can represent wider intervals
up to300s freshness. Native request tolerance and stop/expiry remain independently
enforced. Unavailable response can supply elapsed evidence only; original unknown
relative origin is never rebased. Source includes public CLI/poll three-hour
wide-bound recovery and old/new provider boundary tests.

Fresh combined wheel has86-file source parity. Isolated installed qualification
passes eight workers, concurrent dedup, exactlyone monitoring successor, interrupted
submission no replay, unanchored original-expiry hold and old-reader rollback.
Read-only live candidate snapshot observed authenticated counter-only evidence;
that is availability evidence, not UTC or a production wake/turn acceptance.
Source-changing work is frozen before final broad verification and publication.

Bounded primary reconciliation review (new approved integration packet):
Standards: adopted adapter uses pinned loopback HTTPS/private CA/bearer without
proxy/redirect/guest fallback; known-file snapshot admits only four files, preserves
root work, and refreshes policy inventory. Spec: new public CLI/poll regression
proves original three-hour deadline with six-second authenticated v2 bounds;
best-effort and unbounded UTC refused. F4 unknown-origin hold and counter-only
continuity remain unchanged. No new general review loop or earlier ledger reset.
Before activation, eight managed wake roots had70 records and no schema6 records.
Do not restart the independent retained webhook listener or create replacement
incident wakes. Retained prior release is the rollback target.
