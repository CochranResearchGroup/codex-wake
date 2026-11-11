# Native governor controls · #572

The presentation preview is `preview.html` (synthetic values, no operations).
The implementation is the real Codex Rust TUI, retained as `governor-ui.patch`.
`manifest.json` binds the patch, native source base/commit and file hashes.
This is a supplemental patch over the retained native167 base, not a patch over
stock upstream. Existing native source, installed binaries and rollback packages
remain untouched.

The native `/wake` command dispatches typed local events. Governor calls use
fixed executable `codex-wake` with argv `governor VERB SELECTOR --json --endpoint
UNIX_ENDPOINT`; explicit mutation submissions add request IDs and an observed
revision when available. The Python owner authenticates local operator authority;
no model field grants authority. Forms are local text prompts, not model prompts.

The persistent strip displays the current task; another selected task is named
in the palette/details. Status is polled serially (completion plus three seconds,
15-second request timeout), with widget/thread cancellation. Transport failure
shows disconnected/accounting unknown; no zero-usage or advisory fallback.
Read-only catalog entries reuse existing wakes/tabs/sessions/accounts commands.
The target picker accepts only owned Codex rows on the current qualified Unix
daemon. Messaging is visibly unsupported without a qualified actor binding.
No destructive operation is exposed, so no destructive confirmation is needed.

Validation stages and immutable package qualification are recorded in
`validation.json`; private raw Cargo Signal receipts are retained outside Git.
Working-account installation, service restart and provider turns are excluded.
