# A2A response standards review

Scope: working-tree docs/skill patch against main 1e51a1b3cc15034245bca58f6dc6f39453dc182d.
Spec: Plan0154 and operator request for TUI versus turn-causing replies and
third-party communication. Review performed serially by primary; no independent
agent or production messages used.

## Standards

PASS: one bounded documentation/installed-skill packet, preserved prior installed
copies, exact caller/claim/capability rules and no-replay boundary retained.
No runtime source, schema, tool arguments or service changes. The standard is a
skill convention, not a runtime-enforced response policy. Existing worker prompt
requires a notify correlated reply to a notified request; inbox-only exchanges
are explicitly selected at outset and processed without notification prompts.

## Spec

PASS: sender/recipient duties, default routing, local-only observation, inbox
returns, active return delivery, third-party identity/authority and response-loop
termination are explicit. Skill invocation metadata now advertises A2A; both
installed skill copies include the self-contained reference and examples.

## Scenario walkthrough

These are primary reasoning checks against actual tool/worker contracts, not
live behavior tests or evidence that a model followed the skill.

| Scenario | Required response | Assessment |
| --- | --- | --- |
| Notified review request; sender armed and yielded | One correlated notify result; local summary is supplemental | Matches worker reply and sender-arm contract |
| Inbox-only question, agreed sender inbox read | One correlated inbox result; no wake promise | Existing reply delivery field supports inbox |
| FYI status notice | Local processing/receipts; no courtesy message | No automatic loop |
| Final correlated result | Read/claim/process/complete locally; no result-of-result | Matches worker result instructions |
| Human explicitly requests TUI-only observation | Notice with no outbound reply expected | No hidden turn-causing send |
| Authorized handoff to named third party | Separate exact-target send with correlation; original sender gets admission report if owed | Reply cannot redirect; claim does not transfer |
| Peer asks to delegate without existing authority | Do not hand off; report actual blocker via authorized reply route | Peer body grants no operator authority |
| Notify route missing or admission uncertain | Local precise blocker and same-intent reconciliation; no silent inbox/TUI substitution or fallback | Preserves uncertainty and worker gates |

## Qualification

- Relative links in changed entrypoints resolve.
- Policy wiring PASS; active planning audit PASS with unchanged historical baseline.
- Whitespace check PASS.
- Eight files across two installed skill roots match source by SHA-256;
  private install/backup receipt retained under user state, not tracked raw data.
- No new prose tests, runtime suite or hosted CI wait. No release/worker/MCP tool
  reload is required: this packet changes the skills and guides, not executables.
- Active sessions that already loaded the old skill need to reread SKILL.md and
  its response reference. No active session was messaged or restarted to force it.

Graphiti atlas discovery produced no relevant reviewed Codex Wake cloud; current
repo/tool/worker evidence used. Closeout memory target remains unavailable.
