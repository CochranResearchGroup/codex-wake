# OBS-02 | Reused feed implementation and current passive observation

Historical worker report: the local alias disposition below was subsequently
superseded by [canonical reconciliation](../../notes/0216-2026-11-12-canonical-acceptance-reconciliation.md).
Measured results remain unchanged; this report does not reopen canonical #542.

Source: `34194dbf7cc2fe54c44f9c6e8c7997ef22c52797`.
Worker branch: `feat/p216-obs02-verification`.
Scope: OBS-02 only; no source changes, review rerun, issue mutations, deployment
or production-monitor activation. Root validated OBS-01 before dispatch.

## Existing implementation and current seam checks

PR551 already integrated the native/tmux feeds and persistent observer. Retained
source contracts and tests distinguish native protocol fixtures from real native
status delivery; no duplicate observer implementation was needed.

Current local Python3.12.13 focused commands:

```
PYTHONPATH=src /home/linuxbrew/.linuxbrew/bin/uv run --no-project --with 'websockets>=17,<18' --with 'dbus-next>=0.2.3,<0.3' --with 'jsonschema>=4.26,<5' --with 'msgspec>=0.22,<0.23' python -m unittest discover -s tests -p 'test_tab_native_feed.py' -q
PYTHONPATH=src /home/linuxbrew/.linuxbrew/bin/uv run --no-project --with 'websockets>=17,<18' --with 'dbus-next>=0.2.3,<0.3' --with 'jsonschema>=4.26,<5' --with 'msgspec>=0.22,<0.23' python -m unittest discover -s tests -p 'test_tab_tmux_feed.py' -q
```

Native: 3 PASS in1.184s; tmux:6 PASS in4.925s, no skip or retry. Native tests are
protocol fixtures. Tmux tests use private actual stock tmux, exercising baseline,
metadata changes, disconnect/reconnect, replacement, bounded idle polling,
coalescing, literal names, environment preservation and owned cleanup.

## One bounded read-only installed-native window

Used the existing `scripts/tab_observer_live547.py` harness, installed Python from
`0.22.0.dev11-32eb90f`, `--seconds 25`, and a unique private user-state receipt.
Exact command (exit0 on first invocation):

```
/home/ecochran76/.local/share/codex-wake/releases/0.22.0.dev11-32eb90f/bin/python scripts/tab_observer_live547.py --seconds 25 --receipt /home/ecochran76/.local/state/codex-wake/qualification/p216-obs02-20261112/live.json
```

No
repeat window was run to chase an event. The full metadata-only report is at
`~/.local/state/codex-wake/qualification/p216-obs02-20261112/live.json`; it contains
no raw screens/transcripts or credentials. No private endpoint/account data is
copied here.

- Actual wall25.480175s; native source connected, tmux source available.
- **Three natural native status updates**, four native events including baseline.
  This improves the older zero-transition live receipt; it is actual installed
  native delivery evidence rather than a fixture broadcast.
-43 existing tabs,15 bound conversations. Exact pane-layout digest unchanged;
 69 observed process births unchanged,0gone.
- Health requests, screen captures, provider requests, configuration changes and
  production-monitor activation all false. Formatting used two read-only option
 reads, both succeeded with no writes/refresh/input.
- Two owned read-only control clients closed; original harness census0 remaining.
 Fresh subsequent `/proc` readback: both controls absent and live driver absent.
- Aggregate-owned CPU1.69s, phase `/proc` RSS peak40,833,024B. These25s health/error-
 disabled phase observations are **not**60s default-tier resource acceptance.
 The process-lifetime `ru_maxrss` value is not a phase RSS measurement.

Installed/source byte equality checked after observation:

| Module | SHA256 (equal in source and installed package) |
| --- | --- |
| tab_native_feed.py |46f2b125992f0c12f798d7ad80b9a4720acb0b19e28386874f50a49917a5ffa7|
| tab_tmux_feed.py |f759927916a0209008281dca41c5b98d811753fda638d22fd60181d577f4b7a0|
| tab_observer.py |3eecbf0c10fd16276972aa278f13756e96ad7c086afa6090cf0491939c0e0f61|
| tab_format_read_channel.py |de78b7296126598598d4c0f5959e52ebc9d0ddd5c979ad23e68278f36a598c93|

## Limits and proposed disposition

Existing implementation is integrated and current focused seams pass. Actual
native passive delivery is observed for the single current connected source;
this window does not identify or independently qualify both stock and modded
native flavors. It does not prove100-tab scale, p95 event-to-projection latency,
60s resource caps, or the OBS-05 minimum44-tab existing-host gate (43 observed).
No source event timestamp was retained from which p95 could be honestly computed.

Proposed ticket state: implemented/integrated, **partial acceptance**. The single
actual source was not individually identified as stock or modded. Under OBS-02's
explicit requirement to qualify actual stock/modded sources, that axis remains
unmet; generic feed delivery cannot substitute for independent flavor evidence.
Root must reconcile these remaining axes against the frozen ticket. Do not
silently equate one native source with stock/modded parity or turn the43-tab
window into44+ acceptance. The existing campaign's one broad review and one TDD
remediation remain consumed; this worker did neither again. No implementation
finding justifies a source patch in this bounded packet.

Memory disposition: forbidden under session developer boundary; no explicit
memory-update request. Zero Graphiti writes.
