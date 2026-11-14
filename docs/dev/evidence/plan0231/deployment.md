# P231 installed deployment

Operator instruction: `pr review merge deploy` (2026-11-13). This extends the
source-only closeout in PR609. Implementation tickets #602–604 and Bots #75–76
remain closed; parent spec #601 retains its documented open state.

## Review and integration

One two-axis review and one focused TDD remediation were already completed;
[review evidence](review.md) and [findings](review-findings.json) remain authoritative.
All three accepted Bots findings were fixed and merged in Bots PR78. No second
broad review was run. Wake PR607 and PR609 were independently read back MERGED.

## Wake deployment

Exact source: `282dcf02cda3aa9ddd88ce2ac86de48e4bed7d92` from merged main.
Package: `0.22.0.dev19`, wheel SHA256
`1d58a7dd77aee8a7f6ee1d51b4d8577dd9426beb2c50b478aa967d91028170b2`.
Built from `git archive` of that commit, with no working-tree additions.

- `uv build --wheel`: PASS. All 328 package members matched the wheel, installed
  package and corresponding source bytes; all 31 pre-existing dependencies were
  preserved at their exact versions.
- Installed Python3.12.13: `python -m unittest discover -s tests -p
  'test_bot_famil*.py'`: 17 PASS, 12.580s. These exercise the public CLI, private
  real tmux placement, exact attachment reuse, cleanup fencing and presentation.
- All nine stable launchers switched to the immutable dev19 prefix. Exact
  per-launcher prior targets were retained (the prior installation had mixed
  dev18 Wake and dev14 profile launchers).
- Only the tab monitor restarted: PID1587828 to PID3081031. Its actual interpreter
  resolved to the new prefix; generation `3f665ce0ebed4ab6a5567f8884c346a7`
  matched the fresh snapshot with 48 resources and no monitor error.
- Monitor settings remained byte-identical. Formatting reported applied with no
  failures; existing inactive routing remained inactive. No native daemon build,
  upgrade or restart occurred; no terminal input was sent.
- StableTime before switch: qualified live, NTS verified,
  `2026-11-13T23:24:05.339140585Z`, maximum error297.005498ms.

The old immutable packages and exact launcher/configuration preimages remain
private rollback custody. Restore the recorded launcher targets and restart only
the monitor from its previous prefix; do not replace native sessions or runtime
state. Resident MCP clients keep their prior imported code until their normal
reconnection; refreshed launchers and tab monitor are independently verified.

## Local validation scope

Hosted GitHub Actions were skipped under the operator cost policy. Existing
source qualification and this installed focused selection substitute; no full
Python3.11 matrix or unrelated comprehensive suite is claimed. Canonical policy
wiring and `git diff --check` passed during deployment.

Private package/rollback receipts are retained under the operator state directory
in `codex-wake/p231-deploy`; credentials, private state and raw logs are excluded
from this source evidence.

## Bots runtime qualification correction

Bots PR80 merged as `c7fe3a1ad8691201b47c130d73f257b70f145261`. The
pre-existing support manifest excluded both the installed native daemon0.169.0
and feature Wake0.22.0.dev19. The correction appends these two exact versions
and regenerates the dependency table; existing supported versions remain.
A focused deployment-diff review accepted this bounded correction, without
repeating the feature's broad review or TDD remediation.

Existing dependency/documentation checks: 11 PASS. Actual required-base runtime
preflight: PASS after qualification. Read-only real0.169 protocol and a private
real native TUI/process-generation join passed without model turns or daemon
restart. The separate attempted automatic family move returned
`retained/tab_protected`; moved-native-attachment acceptance remains unproven.
That protected result was retained, not bypassed or relabeled as a successful
move. Temporary threads were archived and owned temporary servers removed.

The existing host startup check also pinned the old native generation. Its
replacement retains exact socket/peer UID/PID, boot/birth, executable path/hash,
socket inode/device and cgroup proof, and rejects ownership within the Bots
cleanup boundary. It admits the qualified current generation only. No daemon
version change, broad scope-name allowlist or active-task cancellation is used.

## Bots package startup and ingress

Candidate source `c7fe3a1ad8691201b47c130d73f257b70f145261`, identity
`556d9a220ebe8305da814ccb53643c84d44aa4ea309facb7973d9086a09126cb`,
933 verified files. Candidate smoke and corrected required-base preflight passed.
HTTP startup selected the exact immutable package and current qualified native
generation; existing installation configuration was preserved. Native daemon
PID3511104/birth10403595 remained unchanged.

Ingress checked with independent anonymous and authenticated contexts using the
existing Cooper agent account. Anonymous access returned401 and named the correct
Cooper login realm. Accepted sign-in then reached app200 and health200. The health
build identity and source matched the candidate above; Codex and Remote View
connections both reported true. No credentials/cookies are retained in evidence.

The separate Bots messaging service remains on its existing Wakedev18 process.
Its21 A2A Python module bytes equal dev19, and the SPEC-1 guidance fix executes in
the new Bots HTTP JavaScript service; no messaging-worker refresh was required.
The worker was preserved. Four saved bot thread IDs remained unchanged. Absent
legacy attachments used the existing public recovery retry path, with one stable
request per eligible bot and no model prompt or forced hold bypass.

## Final configured family state

Bots HTTP PID3219055 selected the same verified package after the adapter-only
configuration restart. Final authenticated app/health checks remained200 with the
exact candidate identity and both connections true; anonymous protection remained
401 in its separate context. The explicit family adapter uses the existing Wake
controller root and enrolled Bots terminal workspace, with no provider grants.

Four persistent specialist roots are registered. Three exact restored attachments
were bound and adopted through the public family interface to preserve existing
root placement. New descendants retain default workers placement. The fourth
Grok root remains unbound under its pre-existing `input_unknown` desktop-input
hold; no input, hold reset, replacement conversation or forced recovery was sent.
Root independently read back four descriptors, three single bindings and one
unbound root using installed `tabs family list --json`. This is a configured
package deployment, not a claim that the held root or protected child move passed
live acceptance. No account/provider journey or model turn was performed.

Final configured adapter acceptance reused the same saved thread, window, pane
and PID/birth for all three adopted bindings. The configured organizer returned
`reused` for each; saved identities and private desktop/browser/auth/account-state
projections were unchanged. Existing opted-in formatting projected specialist
labels/scope and muted root accents without changing formatting policy.

Independent actual tmux option readback confirmed specialist labels on all three
restored windows and muted dim root backgrounds (colour109, colour66, colour60).
These are installed visible options, beyond formatter-only projections.

## Tracker and checkout closeout

Bots compatibility issue79 read back CLOSED. Closeout-only Bots PR81 merged
`e29ae5feb22339fa3fe6efa61f12b25e1c2aa9d9`; its difference from deployed
c7fe3a1 is the Plan0127 documentation only. Original feature tickets remain
closed, with parent601 deliberately open under the existing ticket contract.

The Bots deployment checkout was removed normally after verified source custody;
registered Bots checkouts returned2to1. Owned dependency symlink, smoke roots and
unused initial artifact were removed; rollback packages/config/helper preimages
remain. Shared native daemon generation was independently rechecked unchanged.
The Bots primary checkout is clean and preserves its three local policy commits
(three ahead/seven behind canonical main); it was never reset for deployment.
Wake used exact archived source and Git objects for this evidence PR, creating no
additional checkout. Existing unrelated Wake worktrees were preserved.

Memory disposition: forbidden; no explicit memory-update request. Zero graph
memory writes. Private deployment/rollback/provenance receipts remain outside Git.
