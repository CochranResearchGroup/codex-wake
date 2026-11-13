# P0226 bounded repair acceptance | 2026-11-13

Documentation base4b7da1f9dc2ad16e67f091f1cbc8d85468252407. This closes the
repair outcome; it does not renew or execute the Sentinel campaign.

| Acceptance | Evidence and disposition |
| --- | --- |
| Stable launcher survives rotation | Retained red/green real registration/persistence/locator regression;97focused source and installed checks in original diagnosis/install notes |
| Deleted explicit build pin remains unavailable | Explicit-pin control retained; no silent PATH/account fallback introduced |
| Generic resolver unchanged | preserve_launcher is opt-in only for native registration; retained focused coverage |
| Exact working installation | PR592/34b7362, installed0.22.0.dev13; original installation notes retain wheel/byte equality and97checks |
| Current caller resident version | Read-only wake_sessions_configuration self-refresh returns0.22.0.dev13; this does not prove every other connection |
| Installed prevention regression | Immutable dev13 Python ran test_native_launcher_continuity:3PASS0.087s; imported native_intents/app_server paths verified under installed prefix, no source shadowing |
| Overdue delivery/result | Reviews8/9 artifacts name exact successors and native submission IDs; completed within original windows; recipient's latest completed turn corroborates review9 |
| Scope/cleanup | Original recovery preimages retained and diagnostic checkout retired; this verification created no runtime worker or mutation |

[Diagnosis](../../notes/0226-native-launcher-continuity-diagnosis.md) and
[installation](../../notes/0226-native-launcher-installation.md) retain earlier
failure/success conditions. Private user-scoped readbacks reside under
~/.local/state/codex-wake/reconciliation/p226-readback-20261113/:
verified-summary.json, resident-proof.json and recipient-results.json. Raw campaign
records, prompts, recipient identifiers and report contents stay outside Git.

Reviews8/9 completed at2026-11-12T18:19:19.796043Z and2026-11-13T02:42:15Z,
respectively. Exact wake/native submission correlation and original-window checks
passed; review9 also has report/result receipt identifiers. Native transport
acknowledgment remains not_observed; completion is proved by separate attributable
work artifacts, not by changing that field's meaning.

## Residual LP-01 and acceptance adjudication

Current caller MCPdev13 plus installed regression establishes the source/version
prevention path available to this connection. A live future wake was not created
for proof. Seven earlier approved successors remain immutable literal0.167.2
pins, not upgraded durable aliases. Earlier readback found2submitted/5pending,
all7due/expiry values preserved and recorded executables present. This is dated
metadata, not a current guarantee or instruction to keep/replay pending work.
Recipient readback was notLoaded, so its own resident MCP version is unknown.

These are residual limits rather than failed original repair criteria: the
specification explicitly preserves literal pins, requires separate recovery
authority and forbids pretending source repair rewrites existing targets. Later
installation and approved overdue review readback are now independently evidenced.
A future release retirement requires scoped exact-record reconciliation; no
blanket cleanup, record rewrite, replay, allowance renewal or forced recipient
load/reload is permitted by this closure. Future reviews retain their campaign
owner and original windows. Plan LP-01 keeps this risk discoverable without
creating a duplicate feature campaign.

## Documentation verification

No code/runtime effects. Commands: policy wiring, relative Markdown file links,
whitespace and active planning audit with exact inherited-finding comparison.
Installed regression and private readbacks above are prior-phase evidence, not
new tests run for this documentation patch. Local Linux/Python3.12.13 differs
from hosted Python3.11/3.12; no hosted CI or full-suite claim.
Memory forbidden under session developer boundary; zero Graphiti writes.

Observed closeout checks at base4b7da1f9 plus docs patch:
`python scripts/check_policy_wiring.py` PASS; inline relative-file link check
PASS; `git diff --check` PASS. Active planning audit now retains only0220/0224
header findings; replacing0226's non-deterministic IN_PROGRESS header resolves
that existing finding without baseline expansion.

Primary documentation review, separate axes: Standards0findings after checking
policy routing, preservation and dated evidence; Spec0findings after comparing
original definition of done against the acceptance table. Closure preserves
explicit-pin behavior and all authority boundaries. No independent reviewer or
new implementation review is claimed; no source behavior changed.

## PR598 integration verification

Base advanced to6150e5a5 (merged P229 reconnect work). Merge resolutionf36ec348
retains both RUNBOOK append blocks and all P229 changes. Source/tests/scripts/
package files byte-match that base; final PR delta remains four P0226 Markdown
files. Relative links, policy wiring and whitespace pass. No new runtime tests
or repeated implementation review are required for this documentation conflict.
Primary Standards/Spec integration verification found0new candidates.

The initial integration audit wrapper expected the earlier two findings and
failed on P229's newly inherited missing Current State section. Base6150e5a5
contains that exact defect; the corrected comparison retains0220/0224 headers
plus0229 missing Current State, with0new findings from this branch. No baseline
expansion or unrelated plan repair. P0226's own header finding stays resolved.
