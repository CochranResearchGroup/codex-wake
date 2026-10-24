# Default own-session refresh access (#310)

Source change pending integration and release. No version or production
installation change is included.

Verified native MCP sessions can inspect and request refresh for themselves on
provisioned `shared_mcp_idle` and `client_idle` host profiles without a per-session
UUID entry. Explicit caller entries override the default; an empty list denies
access. Operators can disable the default with `session_permissions.self_access:
false`. Existing explicit grants and legacy receipts remain compatible.

Shared effect-scope approval, idle observations, checkpoint/resource proof,
fixed deadlines, emergency pause and budget controls continue to apply. CLI UUID
claims alone receive no new authority. Independent controllers revalidate queued
permissions and block revoked requests before effects. No objective allocation is
created or renewed by this default.
