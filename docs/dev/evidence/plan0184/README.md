# Cooperative daemon upgrade qualification

Plan0184 is the authority. `runtime-proof.json` is curated synthetic evidence;
full private dummy-account receipts retain provider requests, terminal captures,
updater logs and operation files. No production credentials/history were copied.

Run the retained acceptance harness as real Linux UID1017, with its staged
`wake/bin/python` and a unique case name. The harness requires its explicit
`/home/codex-daemon-test/daemon-qualification-0165` laboratory; it never selects
a working-account CODEX_HOME. `CODEX_QUALIFICATION_TARGET` names the immutable
complete candidate package's bin/codex. `CODEX_QUALIFICATION_MODE=refuse|hang|legacy`
selects a negative control; `CODEX_QUALIFICATION_BASELINE` selects the older-daemon
case. Each run owns its daemon, localhost provider, private tmux server and files.
The default happy path performs supported update, checks four tabs, then rolls
back the paused conversations with the complete baseline package.

The provider intentionally scripts the model responses. This establishes actual
native protocol delivery, goal tool execution, durable writes, admission gating,
UI reconnection and rollback. It does not qualify independent real-model choices
or checkpoint quality. Native unit selection and source/build identities are
recorded separately in validation.json and source-manifest.json at closeout.

First red was an unsafe successful replacement with no preparation receipt.
The failed history-reader candidate held installation safely. The UI failures
retain captures showing an unsubmitted slash command; a400ms separation between
paste and Enter fixes the test input without changing product behavior.
The legacy PID-time test flake is retained as an unresolved qualification risk;
a diagnostic pass does not erase it. No working-account installation is allowed
by this evidence packet.
