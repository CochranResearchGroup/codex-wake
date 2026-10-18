# New-caller resource hold diagnosis

Observed on installed0.17.2: caller01a14cc0-1379-78a3-8f23-8446ea24d1ca is
absent from private host policy; grant for01a14c3b is a different conversation.
Fresh public MCP reproduces exact held/armedfalse and host caller grant missing
or malformed on two independent runs. Public private-fixture minimization with
empty caller map reproduces without native socket/controller/history. Adding
only that exact caller key using a known valid grant changes the same MCP
process response to held/not_enrolled; removing restores original error. No
production policy changed, no grant inherited, no enrollment receipt created.

Ranked hypotheses: missing exact caller, malformed grant, stale MCP, malformed
set arguments. Differential confirms missing caller; valid grant fields accepted.
Fresh configured27-tool MCP returns same failure, ruling out stale wiring as
the cause of this hold. Original set invocation independently shows17.5percent
and900seconds. MCP schema requiresintegerpercent; CLI parser also requiresint;
backend already supports finite numeric percentages. Source patch changes the
MCP type to number and CLI to float, preserving range/finite/authority guards.

Regression at actual stdioMCP→CLI→host admission seam uses original2M/6h and
17.5percent/900s but an empty private grant map. Red before fix:invalid_argument.
Changing only MCP exposes second red:invalid_cli_response from CLI parse. With
both inputs fixed, returns genuine host grant refusal rather than schema error.
14focused MCP/CLI/supervision checksPASS6.711s. No debug instrumentation added.
This fixes fractional reserve admission, not missing authorization.

The original armed expectation intentionally remains unfulfilled in production.
Exact host refusal is expected for a new ungranted UUID; automatic user-authorized
bootstrap/continuation across different conversations is not implemented here.
A tab/CWD/title alone cannot select a prior allocation or reset counters. No
production grant, goal, monitor, enrollment, expiry or allocation was changed.
