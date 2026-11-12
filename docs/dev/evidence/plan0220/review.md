# Plan0220 single broad review

Frozen Wake `3f8a18fa...23b87803`; native `d3e31126...bd519d5`. Independent
Standards and Spec reviewers ran once; primary verified and adjudicated every
candidate. Exact findings and evidence are in [review.json](review.json).

## Standards

`STD220-1` and `STD220-2`: **nonblocking_backlog**, P3 judgment calls. Effective
task/shared deadline selection is duplicated between native-guard arm and guarded
start. Native lease capacity admission/eviction is duplicated between ordinary
and guarded enrollment. Current predicates agree; no behavioral defect was
demonstrated. Extracting either helper is outside this presentation remediation.
No blocking documented-standard breach was established. Some oversized combined
outputs were truncated; native lease source was subsequently inspected in bounded
segments. This is not certification of individual inspection of every generated
or historical hunk.

## Spec

`SPEC220-1`: **blocking**, P2. With task100/1000 and shared500/500, the persistent
strip says900left although the normalized effective remainder is0. It must render
the authoritative remainder.

`SPEC220-2`: **blocking**, P2. Native details do not identify task versus shared
limiting scope or show the applicable shared allowance. Operators cannot tell
which ceiling requires attention.

Both violate the frozen remaining-resource/limiting-scope requirements. They are
presentation gaps, not evidence of failed underlying containment. One bounded
TDD pass owns these two findings; focused verification cannot restart discovery.

Accepted findings: Standards2 backlog, highestP3; Spec2 blocking, highestP2.
