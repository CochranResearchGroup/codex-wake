# LOCAL-P215 | Reusable muted tab palette presets

State: OPEN
Ticket: LOCAL-P215
Owner: primary
Priority: P2
Dependencies: P214
Branch: feat/tab-color-presets
WIP limit: one

## Outcome and acceptance

Operator selected Slate from published preview and requested all three palettes
as presets. Ship Slate/Dusk/Graphite as immutable named presets matching preview
colors, compact/noSTALE layout, subtle selected background, type-only accents and
small attention markers. Persist per-session preset, expose through shared
CLI/API/MCP configure and inspection discovery. Preserve original baseline and
existing explicit plain/full behavior. Qualify private native rendering/switch/
rollback, deploy exact wheel, select Slate for default. Do not restart automatic
health monitor while loaded-host cycle remains unqualified.
