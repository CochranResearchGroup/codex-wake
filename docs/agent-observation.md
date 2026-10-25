# Semantic agent observation

Inventory membership and a recent binding are separate from what an agent is
currently doing. Use `agents observe` for a fresh semantic state or `agents wait`
for a bounded wait on a state. Neither sends input, starts a runtime, loads a
saved conversation, accepts work or grants mutation permissions.

```sh
codex-wake --wake-root /owned/wake agents observe --managed-agent-id agent_ID --json
codex-wake --wake-root /owned/wake agents wait --managed-agent-id agent_ID \
  --state ready --timeout 60 --freshness 30 --interval 1 --json
```

The same operations are `wake_agents_observe` and `wake_agents_wait` in MCP.
Runtime endpoints, capabilities and binding files are host configuration, never
model tool properties. A local Grok read can specify its existing `--runtime-root`,
`--binding-id` and `--binding-sha256`. Grok MCP reads use the host-bound actor
profile. Missing configuration remains unknown.

Defaults are a 30-second maximum evidence age, a 60-second wait timeout and a
one-second poll interval. Freshness accepts 0.1..300 seconds, waits 0..300 seconds,
source reads up to 60 seconds, and polling 0.05..5 seconds. The monotonic wait
deadline bounds subsequent reads and sleeps; a zero timeout starts no runtime
read. The initial fresh matching state can satisfy a wait; no prior transition
is required. This is not a durable event subscription or unattended wake.

States are `working`, `ready`, `awaiting-human`, `auth-required`, `disconnected`
and `unknown`, with supported/unsupported capability fields. Codex maps exact
native idle/active/known approval or user-input flags and explicit notLoaded
status. Unknown combinations remain unknown. Grok currently proves only its
version-qualified empty composer as ready; busy/draft text is not proof of
working. Neither adapter currently qualifies auth-required. Work completion and
acceptance are outside this vocabulary.

Evidence includes exact managed/conversation identity, provenance, timestamp,
freshness and a bounded reason. It excludes frames, prompts, transcript contents,
credentials and endpoints. Suppression, mismatched namespace/root/process, partial
or stale evidence, unavailable sources and future timestamps cannot become ready.
A freshly observed but unsupported native state may be fresh unknown; it is never
promoted to an action grant.

Wait results distinguish `matched`, `timeout` and `unknown`; the last redacted
observation is retained in the response. Unknown evidence cannot satisfy a known
state predicate. A CLI observation exits 0 for an observable result (including
unknown); waits exit 0 for match, 3 for timeout/unknown and 2 for invalid/unavailable
requests. MCP returns the same structured state independently of tool errors.

The public owner is `AgentObservation.observe/wait`; runtime evidence is injected
at its observer seam. Production `RuntimeStateObserver` uses the existing
read-only app-server reader and Grok observation adapter. Source tests qualify
these interfaces with disposable state and protocol fixtures; they do not claim
new provider support or production rollout.
