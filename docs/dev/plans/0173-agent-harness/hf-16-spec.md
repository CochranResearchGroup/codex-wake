# HF-16 tab ordering

State: SOURCE_VALIDATED; shared integration and final review remain primary-owned.

Issue337. Approved form: activity first; repository-first configurable. Explicit,
focused, mixed, unqualified and linked windows are pinned at their exact indices.
Repository grouping uses canonical Git common-directory identity, joining worktrees.
Only existing slots in one exact session/server are permuted with swap-window -d.

Public seam: tabs preview/show/apply/undo and equivalent host execute adapter.
Preview records exact window/pane IDs, qualified native/host-bound conversation and
process identity, state, repository identity, pins and prelayout fingerprint.
Apply refuses any changed snapshot before effects. Each swap has a durable pending
receipt and readback. Uncertain/partial operations are never blindly retried.
Undo requires the exact recorded applied postlayout; newer layouts are held.
No automatic sorting, provider input, process restart or cross-session moves.

Tests use an actual disposable private tmux server and injected qualified provider
metadata at the public command seam. Shell-process fixtures are not native provider
acceptance. Shared caller registration remains with the integration owner.
