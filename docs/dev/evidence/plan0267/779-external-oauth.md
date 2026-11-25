# Issue 779 external OAuth MCP qualification

Candidate source `f44a25c717be0fa68dee3f6f643e920b1b05ac3f`. The candidate
was exercised through Streamable HTTP, OAuth dynamic client registration,
authorization code with PKCE, and the MCP SDK at a fixture-only local
issuer. The normal psmux owner ran on native Windows, and the sender
owner ran in WSL. Test profiles, mailbox recipients, and terminal
namespaces were isolated. Both stock Codex clients used local inference
fixtures.

| Check | Observed result |
| --- | --- |
| Control-only mailbox send | Synchronous wait rejected before admission. Asynchronous submission returns metadata and no reply content. An explicit content grant can receive the correlated fixture reply. |
| Pinned Windows schedule scopes | Consent for a general host target alone does not grant the separately listed exact Windows target. The stale peer generation and another grant's status lookup are rejected. Identical admission replays the same ID, while a different expiry conflicts. |
| Actual tmux tab loss | The OAuth client registered and bound schedule `schedule_10147b03f55c617b830ac5749f95379e`. After closing the fixture tab and restarting the monitor, stock Codex 0.171.0 resumed conversation `01a21151-e626-7222-8b92-2925aec67fe5` in its original private profile, tab `wk-749` at index 1. Occurrence `:1:0` submitted once. Index 7 and its sentinel survived. |
| Actual native Windows psmux server loss | The OAuth client admitted `b84137c7-dee6-4842-8cc2-5b31aa425204` with eligibility `1795587077000000` and expiry `1795587273000000` UTC microseconds. Native Windows stock Codex 0.169.1 and psmux 3.4.0 restored thread `01a21154-438e-7b42-9717-92e410edfff9` at index 2 with a new server birth. Windows, WSL, and the original OAuth grant all returned the same submitted receipt `01a21154-fa51-7951-9731-0a5771d6b5af`. The native turn contained the fixture marker and the independent guard was unchanged. |
| Actual tab management and former-tab history | Explicit workspace grants listed, renamed, and closed one fixture tab each on tmux and Windows psmux. On the following read, the only live tab in each workspace was its guard. Separate exact-account metadata consent returned both former bindings, their observed working directories and their absent state. The metadata grant could not read saved records. An additional content scope retrieved the withheld synthetic records without reopening either tab. |

One earlier psmux rename produced an uncertain receipt. That run did not
establish its physical outcome. The conclusive management run used a
fresh namespace and checked the actual psmux names as well as the public
receipts. The history regression also covered former tab-name reuse and
verified that the historic binding and current binding stay distinct.

Local regression with an isolated PostgreSQL database passed 42 tests.

```bash
PYTHONPATH=src:tests python -m unittest test_external_oauth_connector \
  test_controller_runtime test_controller_history test_unified_connectors \
  test_message_owner test_tab_psmux -q
ruff check --select F821,F822,F823 src scripts tests .codex/hooks
```

The live public resource metadata returned HTTP 200, and anonymous
GET `/mcp` returned HTTP 401 with the protected resource metadata
challenge. The installed runtime was `0.22.0.dev37-df30d4f`. Its existing
policy had a host/environment target and no isolated candidate grant.
The available browser profile metadata did not identify the exact
authorized ChatGPT workspace for the qualification. Connected ChatGPT
acceptance still requires a reachable candidate endpoint, an identified
ChatGPT app and workspace, and a consent grant restricted to the isolated
target. No live grant, ingress setting, real tab content, or real agent
message was changed or used in qualification.
