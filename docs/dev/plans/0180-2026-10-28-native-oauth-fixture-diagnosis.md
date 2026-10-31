# Diagnose native0.165 OAuth completion timeout

State: CLOSED — exact timeout diagnosed and corrected. Owner: primary / wake2. Work item: this bounded repo-native plan.
Source baseline46a1f6506d; native branchfix/native-0165-oauth-fixture, existing owned native checkout. Plan0179 remains a closed private build with its frozen original evidence.

Objective: reproduce and fix the single OAuth callback-completion timeout retained by plan0179, through the real isolated app-server fixture. No production daemon restart, credentials, external OAuth/provider service, grant change or governor/resource mutation. Preserve the qualified0.165 package and source baseline.

Acceptance: repeatable exact red with original failure, minimal selected fixture, falsifiable ranked hypotheses, one-variable probes, correct-seam regression before fix, original exact test and original broader MCP selection green, no debug instrumentation or owned processes left. If a runtime fix is needed, qualify a new immutable package; a test-only fix must prove production source and existing package bytes unchanged.

Execution: one primary lane,2Cargo jobs, targeted tests only; max3diagnostic hypotheses plus one bounded remediation/verification pass before reframing. Existing exact test is the regression seam. Initial warm Cargo invocation began an unnecessary environment rebuild and was interrupted after verifying the owned process; compiled test executable provides an11.06s failing loop. Test fails waiting for login completion after callback/token exchange; subsequent reload/status checks are not reached. Raw logs and probe receipts stay under ~/.local/state/codex-wake/native-modern-0165/oauth-diagnosis.

Hypotheses in order: ignored nested credential-store key chooses default persistence; early completion event lost by reader despite persisted credentials; another post-token OAuth continuation hangs. First probe changes only the placement of the same file-store key in the private fixture config, leaving the existing compiled test and native executable unchanged.

## Verified outcome

The misplaced credential-store key was ignored under the mock provider, exposing the test to host keyring persistence. Private stalled-service probe reproduces failure; moving only the key to root removes the keyring call. Existing regression strengthened before the fix: RED11.02s -> GREEN0.94s. Original broader MCP selection25PASS/0FAIL2.65s; original exact invocation passes. Native fixb111dd221b changes one test file only. All package executable hashes are unchanged; no owned native/probe survivors or tracked debug tags. See docs/dev/evidence/plan0180/acceptance.md and resolution.json. Production remains outside this diagnostic slice.
