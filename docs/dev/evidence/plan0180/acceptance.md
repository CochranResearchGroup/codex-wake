# OAuth fixture timeout diagnosis

RESOLVED_TEST_FIXTURE_ONLY. Native fixb111dd221bcf56f625c0aecde9380b1fb57a4d85 on fix/native-0165-oauth-fixture, based46a1f6506d. Only app-server/tests/suite/v2/mcp_server_status.rs changed; production source and all four qualified package executable hashes are unchanged.

## Red-capable feedback loop

Original exact test: `cargo test --locked --offline --profile dev-small -p codex-app-server --test all oauth_login_automatically_selects_callback_specific_cimd_without_metadata_issuer`. A compiled-test invocation of the same exact case avoids dependency recompilation and reproduces the original timeout in11.06s. The callback/token exchange completes; login-completed notification times out. The later reload/status checks are not reached. No model work or real OAuth provider is required.

Initial native Cargo re-entry began a cache/environment rebuild; only the identity-verified owned Cargo process was interrupted. Direct invocation uses the existing all-4f5a8e5e03b96cfd test executable and explicit CARGO_BIN_EXE_codex-app-server. Raw commands/logs are under the operator-local oauth-diagnosis directory. A subsequent unmodified-baseline pass is retained: the original symptom depends on host keyring responsiveness and is not claimed deterministic in an uncontrolled environment.

## Hypotheses and causal probe

Ranked before testing: ignored nested file-store key exposes default keyring persistence; completion event is lost by the reader; another post-token OAuth continuation hangs. Source and parsed fixture config show root_store=null and provider_store=file. The mock config builder appends extra_config after its provider table, so the TOML key is ignored as a provider setting. The same mistake exists in the exact upstream0.165 test; no daemon behavior regression is attributed to the Wake patches.

A private Unix listener accepts a D-Bus connection but never completes its credential-service handshake. This raises the reproduction rate without reading or changing real keyring contents. The existing test and native executable remain unchanged; the one-variable correction relocates the same file-store key in the private config. Wrong placement:11.296s, exit101, one stalled-bus connection. Correct placement:1.002s, exit0, zero bus connections. Separate corrected un-stalled run:1.287s. These are direct real OAuth fixture/native-process probes, not a mock of the completion result.

## Regression and fix

Before applying the fix, the existing OAuth integration case was strengthened on Linux with a private listening D-Bus endpoint passed only to its child app-server through with_env_overrides. The endpoint never responds, making unintended keyring dependence deterministic. No timeout, OAuth assertion, provider behavior or credential implementation was relaxed. Regression-only source still has the wrong setting and fails at login completion in11.02s.

The fix uses the existing with_root_config method for mcp_oauth_credentials_store=file; with_extra_config now contains only the MCP server table. The same strengthened regression passes in0.94s. Original broader MCP selection after final formatting:25PASS/0FAIL in2.65s, versus the previously retained22PASS/3FAIL selection. The two earlier missing-stdio-helper prerequisites had already been repaired in plan0179. Final original exact invocation also passes. No full-native-suite claim.

## Cleanup and delivery

Rustfmt and whitespace checks pass. No tracked DEBUG-oauth165 instrumentation remains. Temporary Python probes are retained only in the clearly marked operator-local debug-probes directory. Their sockets were closed and temporary directories removed; native fixture process census is empty. Source checkout has no tracked dirt after the fix commit; generated .codegraph remains local derived state. Serial primary review confirms process-scoped environment isolation, unchanged deadline/assertions and test-only write scope.

The original0.165 package at native/modern-0165-46a1f6506d remains byte-identical and privately qualified. This test-only correction requires no daemon/package rebuild, deployment or rerun of unrelated paid/runtime campaigns. No production daemon, governor, resource allocation or real provider was changed. The previous unresolved OAuth qualification gap is now closed by this evidence; raw failed build/qualification receipts remain intact.

The fixture patch remains private/local at `9ff60357011788a9edabedfd768bca0a6c23030c:docs/dev/evidence/plan0180/oauth-fixture-fix.patch`; its payload is excluded from canonical Wake publication. Historical reverse-application verification againstb111dd221b passed. Plan0179's larger upstream port patch remains a distinct preceding artifact. Raw evidence: ~/.local/state/codex-wake/native-modern-0165/oauth-diagnosis/{resolution.json,regression-red.log,regression-green.log,mcp-selection-final.log,original-scenario-final.log}; earlier single-variable probe receipts remain alongside them.
