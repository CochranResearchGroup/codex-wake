# PowerShell bootstrap diagnostics

State: CLOSED
Owner: ecochran76
Issue: #478
Branch: fix/powershell-bootstrap-diagnostics
Base: 25d7005c0198a46c04665682acda1f09c4a9d841

## Current State

Implemented at `56ef935`. Actual PowerShell regression proved native stderr under
Stop leaked arbitrary text and hid the exit code; the fix captures native output
privately and reports only exit/category. Malformed connection JSON is sanitized.
Twelve affected tests passed on each Python version, including successful actual
PowerShell Unicode/multiline/four-mode behavior. Ruff, generated metadata, policy
wiring and diff checks passed. Exact commands/log hashes are in
`docs/dev/evidence/plan0202/qualification.json`. Source integration uses a linked
PR; no working installation/deployment or original intermittent-cause fix claimed.

## Scope and acceptance

Report WSL exit code and an allowlisted category. Keep raw stdout/stderr private;
never print connection JSON or arbitrary error messages. Delete temporary files
on success/failure. Preserve exit2 and no normal output on failure. Verify unknown
stderr stays unknown and success remains compatible with the existing client.
No retries, new services, native model calls, deployment or working installation
changes. Done after red/green, affected local checks and source PR integration.
