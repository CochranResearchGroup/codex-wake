# P233 native source custody

This directory preserves native Codex changes as source patches. It is not an
assembled or qualified package and does not activate a working profile.

`t2-source-manifest.json` pins the T2 base, commit, complete source tree, changed
file hashes, patch hash and focused local acceptance. The base is the governor
source identified by `../governor-native-572/manifest.json`; that directory
retains its complete native patch and upstream anchor. Apply the T2 delta only
to that exact retained base. The primary independently applied this delta to an
isolated Git index at the base and verified the resulting complete tree equals
the manifest source tree. No native checkout or installed package was changed.
A verified Git bundle is additionally retained in workstation-local custody.

T2 adds the Grok-specific wire/configuration and SSE conversion into the existing
native tool loop. It preserves command-based private bearer authentication and
holds unqualified features and incomplete/uncertain streams. It does not enable
a generic chat gateway or silently route through API keys.

Local checks distinguish the 274 API/provider tests, three native behavior and
OpenAI regression tests, one remote configuration test, generated-protocol
comparison and focused API library lint. The native checks preceded a private
transparent type alias; affected API tests/lint followed it. Full workspace lint,
full platform coverage, account entitlement, live coding, complete packaging,
isolated upgrade/rollback and installed behavior are not established here.

Future ticket deltas must preserve this acceptance boundary. The program retains
one broad review and one bounded remediation after its implementation tickets,
then exact package qualification and authorized merge/deployment.

Source deltas omit unchanged context; apply them with `git apply --unidiff-zero`
against their exact manifest base. This avoids meaningless trailing-space
context records inside tracked patch data. Each delta was independently applied
in an isolated Git index and verified against its complete expected source tree.
