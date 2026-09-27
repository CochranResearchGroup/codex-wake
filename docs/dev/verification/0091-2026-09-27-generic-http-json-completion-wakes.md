# Generic HTTP/JSON completion wakes

Date: 2026-09-27
Issue: #169
Plan: `docs/dev/plans/0096-2026-09-27-generic-http-json-completion-wakes.md`
State: ACCEPTED

Codex Wake now has a reusable built-in source for ordinary HTTP/JSON job-status
resources. Configuration uses a fixed URL, standard JSON Pointer fields,
bounded terminal values and selectors, and an optional environment credential
reference. The transport is a bounded read-only GET and the journal retains
selected metadata rather than raw response bodies. AuraCall's current status
envelope passes as an ordinary fixture; no product-specific runtime code was
added.

Provider-free validation passed 705 comprehensive Python tests and 12 OpenClaw
plugin tests. Compilation, diff hygiene, active and goal planning audits,
source-registry smoke, and an isolated installed-wheel CLI and registry smoke
also passed. Tests cover terminal and nonterminal responses, selectors,
restart deduplication, malformed and oversized responses, redirects, address
confinement, credential readback exclusion, source lifecycle, readiness, and
the existing tmux and app-server dispatch boundaries.

PR #170 passed hosted Python 3.11 and 3.12 release gates and squash-merged as
`0cae470950119c79cdfbfa404dc31c45d27bb90b`. Canonical main run
`36356569300` passed both release gates. GitHub issue #169 is closed and the
I169 lane is removed.

This receipt does not claim a release, user installation, service change, live
provider read, target dispatch, or visible delivery. Those effects remain
separately gated.
