# Public v0.7.0 installation and installed rollback

Parent Plan0119 / issue181; primary serialized execution. PR214 source
90b1d64630d47391199b27b38c88a1acd1c46e45 passed required Python3.11/3.12 CI
run37250697991 and integrated through squash merge at exact main
9144fb3ea0e0c6bd79907594b9040ac7a77ddce8. Candidate tree matched that integrated
tree. Annotated tag v0.7.0 object9f4f368c58518774b76551c1f029867faa0b64c7
peels to9144fb3; public release is neither draft nor prerelease:
https://github.com/CochranResearchGroup/codex-wake/releases/tag/v0.7.0

## Normal installation PASS

Ordinary command: uv tool install --force --reinstall
git+https://github.com/CochranResearchGroup/codex-wake.git@v0.7.0.
Stable /home/ecochran76/.local/bin/codex-wake reports0.7.0; installed distribution
direct_url.json records requested_revision v0.7.0 and exact commit9144fb3.
No source PYTHONPATH or private candidate CLI is used for this installation.

Pre-upgrade active Codex Wake supervisor PID68168 was restarted after install to
load the package; current PID56882 is active, ExecMainStatus0. Exact four enrolled
repository-root identities/count are unchanged. Existing shared Codex daemon was
not restarted; stock Codex remains0.160.0 and its stable release symlink is unchanged.
OpenClaw runtime/plugin were not changed. Two existing Codex Wake skill copies
were synchronized to the public source; old bytes were preserved privately.

Public-tag product_smoke returned0, reports tag v0.7.0 and CLI0.7.0, and built
from the public tag in /tmp/codex-wake-public-tag-w6lx64pj. Its isolated no-dispatch
fixtures prove installation/source lifecycle only, not actual A2A delivery.

## Actual installed rollback and compatible readback PASS

Disposable ordinary uv tool copy uses private UV_TOOL_DIR/UV_TOOL_BIN_DIR under
the evidence root. Actual sequence: public v0.7.0 -> public v0.6.0 -> public v0.7.0.
The old released CLI returned2/invalid choice for the A2A messages surface.
Hashes of all canonical mailbox.sqlite files were identical before/after both
downgrade and restore; no journal downgrade or checkpoint reset was attempted.
This is command-surface refusal: v0.6.0 predates A2A. Distinguish it from the
separate pinned schema1-reader/schema2 refusal exercised by required CI.

Actual original A, using its issued capability and real thread/root context,
read existing msg_7ca3258545f94c14b10351a54c81db72 through the restored isolated
public installation. Same receipt_5dc4eafd7e1c4f41af922e8b47f2368f and message
returned successfully. No new send, arm, acknowledgement or reply occurred.
Actual actor turn and native output are preserved with final-proof.json.

## Released live service gate FAIL; environment defect reproduced

Released global CLI native configure/enroll/migrate/bind/delegate/resume/doctor/
status commands succeeded for a new explicitly cross-root-enabled private bus,
with original A/B IDs and independently issued capabilities. The shipped native
unit example was installed as codex-wake-plan119-v070-smoke.service, adjusting
only explicit private paths and bounded duration180/notification budget2. It
uses global released CLI and Restart=no; no timer or login enablement.

Native unit PID91069 exited5/runtime_unavailable and is absent; unit is failed,
MainPID0, ExecMainStatus5. B setup ended before service start; actual A sent
msg_f1500c1f16e244d7955f00422948f51d and successfully armed its reply. Read-only
journal proof shows accepted/pending/unread with zero transport attempts. No
controller turn/body relay after admission. This is a failed installed M1 case.

The user-systemd manager PATH excludes ~/.local/bin, where the stock codex
locator command is installed. The shipped native A2A unit specified its CLI
executable but omitted that lookup directory. An owned read-only systemd locator
preflight with explicit stable PATH succeeded, reported existing daemon0.160.0,
and exited0 without daemon bootstrap or restart. Correct the shipped service
environment through a new patch release; do not mutate v0.7.0 or reinterpret this
failure as a pass. One diagnosed zero-effect setup correction remains in scope.

## Private evidence and remaining scope

/home/ecochran76/.local/state/codex-wake/live-demos/20261004-wakeA-wakeB/tmux-plan119/v070

installation-before/after.json, global-install.log, supervisor-after.json,
installed-skills.json, public-tag-smoke-result.json and public-tag-smoke/;
rollback/ contains actual downgrade/restore logs, byte-hash refusal proof,
A-compatible-read.json, actual actor turn and final-proof.json. live/ holds
native setup outputs/manifest and installed unit; live/m1 holds the current case.

Original dirty root note preserved. Integrated evidence checkout and release
checkout removed normally only after clean state and exact remote custody were
verified; source branches retained. Current checkpoint checkout is
codex-wake-v070-acceptance / docs/p63-v070-installed.

Live installed-service M1, explicit second-root exchange and unenrolled denial,
and real30-minute owned soak remain open. Plan0119/issue181 remain OPEN. Never
substitute the public release or fixture smoke for those live acceptance gates.
