# Controller #405 qualified physical roles

The canonical receipt is
[`crosshost405-installed.json`](../evidence/plan0190/crosshost405-installed.json).
The exact integration source is `03677e618891342257c2a87f284c2d1e05befa83`;
its wheel SHA-256 is
`cf2db34ce43c49a4be9181393919f7a8bca402e289b03d38e1c93750c0b96c82`.
That wheel was installed into isolated Windows, primary WSL, disposable
`wsl-test` and Bastion prefixes. Thirteen execution-owner/client module hashes on
each Linux target match both the wheel and current integration source. Windows
bootstrap/client/ACL module hashes match the same wheel.

Native Windows CLI callers and WSL callers reached actual WSL and Bastion
controllers through API and OAuth MCP, retaining their original service grant
and filtering the ungranted account. Actual Byobu capture and stale-generation
refusal worked on both physical Linux targets. Real OpenSSH used a fixed remote
principal; a receiver that completed its read then withheld its reply remained
uncertain across reconnect without another receiver invocation. Same-key reads,
offline refusal, reconnect, revoked SSH mapping and revoked OAuth API/MCP access
were checked. The matrix passed 13 checks. On a slow host, the fixture permits
at most one birth-pinned observation refresh after a pre-admission freshness
refusal; it never repeats an admitted or uncertain exchange.

An actual Windows psmux 3.4.0 process and two real shell panes were controlled
through a private finite bridge owned by a WSL execution authority. Server PID,
Windows creation time and executable hash pin that bridge. API/OAuth MCP and a
caller running inside `wsl-test` observed the Windows presentation. Actual capture,
same-intent receipt replay, unowned-input refusal and failure after the exact
owned namespace stopped all passed. The fresh Windows server and both physical
Linux fixture processes stopped; their private Byobu sockets are gone. Test OAuth
token files were removed from the Windows fixture directory.

Each physical Linux target also passed 13 installed build/authorization tests,
including stage, immutable selection and rollback in disposable homes. Those
payloads are synthetic shell fixtures; this qualifies the installed owner on the
physical host and does not promote a real production build. Four current-package
client tests and the selected Ruff checks passed. Hosted CI was skipped under the
operator's cost policy; commands, source, results and environment differences are
recorded in the receipt.

## Material platform boundaries

**A native Windows Wake execution owner is unsupported.** Its POSIX storage and
locking owners were not ported. Windows is qualified as a native controller
caller and a physical psmux presentation behind an explicit WSL authority; it is
not a green native-owner matrix cell. Native Windows TUI responsiveness is also
unsupported. The published Windows `codex-wake.exe controller remote` command uses
a standard-library client and validates current ownership plus the file DACL
before reading its OAuth token. `--transport api` and `--transport mcp` select the
same protected operations. Legacy `python -m codex_wake.cli` imports POSIX owners
and is not a supported Windows entrypoint. Linux CLI delegation is unchanged.

The lost native health package was rebuilt from exact source `95cd89dd5f` in an
owned persistent target directory with two jobs. Its CLI hash is `5597f709...`;
the full source/package/V8/input manifest is the adjacent native rebuild receipt.
The primary agent separately qualified immutable Bots public health against that
actual native package, including a main-loop-only stall, fresh post-resume
challenge, all five Wake frontdoors and private draft/history/queue invariance.
That consumer proof does not enroll production SharedCodex receivers.

No governor, resource renewal, provider experiment, production restart or
production account migration was performed. Earlier preliminary identities and
bounded fixture/test failures remain in the private evidence root. This packet
uses no final graph review/remediation round; primary integration and ticket
closure remain separate acceptance steps.
