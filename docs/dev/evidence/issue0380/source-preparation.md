# #380 source preparation, not live acceptance

Plan0194 remains OPEN. Implementation source abdb91d3091fc8cba1cb7c83c7c22d4257563410
adds explicit in-place account isolation and pure pinned-version inspection.
No production account, launcher, daemon or running client has been modified.

## Changes and compatibility

The existing migration owner can retain legacy mutable symlinks in an attributable
backup while creating private account state in place. Native credential inodes,
account directory ownership, global paths and mixed legacy history are preserved.
Unknown writers and protected runtime dependencies hold changes. A process with
an idle configured account home is treated as a dependency even without open
history files. Rollback refuses newly written private state. Relocation remains
fixture-only; live isolation requires an explicit owned host policy and exact
preview target. A host policy is not operator approval to interrupt work.

Only exact `--version` or `-V` uses a neutral temporary home and pinned bytes
without acquiring account ownership or materializing settings. Normal launch
protections remain. Version inspection does not establish account identity,
stock fallback usability or installed/live acceptance.

## Local validation

Python3.12.13 checker-c13 with declared development/MCP dependencies:

- `PYTHONPATH=src:tests python -m unittest test_controller_migration test_controller_migration_authorization test_controller_accounts test_controller_history test_controller_history_authorization test_controller_builds test_controller_build_authorization test_absorbed_profiles_concurrency test_profile_launcher_forwarding -q`: **56 PASS**, 10.726s.
- `python -m ruff check --select F821,F822,F823 src scripts tests .codex/hooks`: PASS.
- `python scripts/check_policy_wiring.py`: PASS.
- Focused changed-file lint: PASS.

Migration RED/GREEN receipts include preserved shared history/credentials,
real idle subprocess dependency detection, mid-apply protected dependency change,
explicit unmarked-host authorization and refusal to delete new private history.
Version worker receipt SHA256:
60fb3feac3c25288cdcca59e89fdc3fddfc214282231bc55a5441cd2999bdb35.
No hosted GitHub Actions runs were requested. Native behavior is covered by prior
independent disposable WSL evidence; these source tests use synthetic state.

## Read-only live preview

Seven account homes and35 detachable legacy aliases were inventoried privately.
The global home also resolves mutable directories through a named account home.
The real process census remains incomplete. Preview is **HELD**, with
`protected_runtime_depends_on_account_alias` and `writer_census_unknown`;
production effects are explicitly unauthorized. Receipt SHA256:
5077106e58a7dd6d7ece1da59c2f9c45168b12d6184e75928a11be2a8156f0e2.
Raw paths, process identities and configuration remain in user-private evidence.

Do not remove these holds by treating inaccessible processes as idle, changing
policy to bypass them, or silently stopping clients. Finish source qualification
and prepare exact affected-session effects and rollback before asking the
operator about any interruption. #380 remains OPEN until actual installed/live
account concurrency, existing history, fallback and peer preservation pass.

## Additional package evidence

Wheel and sdist built locally. A temporary isolated wheel installation invoked
its stock launcher with exact `--version` against the existing registered
official0.164 SHA b93f6811d3f653f0fb83be4050d857fb9abbb111dfa2ce160563327daff7f306.
The native version and STOCK/hash labels passed from neutral temporary state.
The live PATH launchers, account stores and shared daemon were not replaced.
This proves staged package version inspection, not a usable live fallback or
account authentication. See source-review.md for the one findings pass and
final58-test focused result.

Post-review implementation source:051027fb8dbea398b907320dae18af73515e5f7b.
The same58 focused tests also PASS on Python3.11.15 in15.307s.
The broad pre-remediation run is diagnostic only because source changed while
it was running; do not attribute its result to an immutable final-source tree.

## Immutable final-source broad qualification

Source83b3032993179e4013260f3adca409a8ca955fb9 (implementation source unchanged
from051027f): **1,941 tests PASS, one skipped**, 376.180s, Python3.12.13.
Command: `PYTHONPATH=src timeout 600 python -m unittest discover -s tests -p 'test_*.py'`.
Environment: fresh XDG_CONFIG_HOME/XDG_STATE_HOME; CODEX_WAKE_STABLE_TIME_CONFIG
empty; inherited CODEX_PROFILES_CONFIG/CODEX_WAKE_ACCOUNTS_CONFIG/CODEX_WAKE_ROOT
unset; TMPDIR in a fresh owned /dev/shm directory. This is functional isolation,
not production disk persistence or native installed acceptance. Python3.11
qualification was the focused58-test selection, not a second full suite.
No remaining visible test-root environment processes were observed; unreadable
unrelated processes remain unknown and no whole-host quiescence is claimed.
The superseded broad run was stopped only after exact PID-generation/group
ownership verification; its diagnostic log is preserved.

Final wheel SHA256:
d93ea6fef6ff3cfdc6e589064a0b539367466fdd911ecd99d5bff596350330f5.
Final wheel's stock0.164 version entrypoint passed from the temporary installation.
Production launcher hashes remain the original identical staged-refusal scripts.

## Official stock0.166 provenance

Official release: https://github.com/openai/codex/releases/tag/rust-v0.166.0.
GitHub asset689712643, codex-x86_64-unknown-linux-musl.tar.gz,
121,764,138bytes, API-published archive SHA256
a0bf572d2f93f056c6712a6da348e96078dc84f3885fd7be67807ef389cb3978
matched the actual downloaded bytes. Its single regular native binary is
319,346,888bytes, SHA256
b8a11fedf24b2dfb59a70c9e52b030f9a508dcd49cd2dd0d41956f4c785156b8.
That SHA matches the existing plain codex executable. The public load_build /
run_build pinned-version path returned0 and codex-cli0.166.0 using a separate
private manifest and neutral temporary home. The native executable emitted its
temporary-home helper-alias warning; no live helper aliases were installed.
This resolves provenance only. Live stock fallback compatibility remains unpassed.
The official archive and curated receipts remain private; no current registry,
PATH launcher, shared daemon or account was changed.

Draft source PR: https://github.com/CochranResearchGroup/codex-wake/pull/459.
#380 remains OPEN; source review/TDD counters are1/1, live acceptance false.

## Incremental admission after refreshed dependency census

Implementation5f8c467 adds optional host `[accounts].enabled` selection to the
same account and in-place migration owners. Inactive configured accounts are
reported explicitly and cannot be resolved for private launch. Default discovery
is unchanged; empty/invalid/unknown admission lists are refused. A synthetic
public migration regression first failed on a protected legacy peer, then passed
when only the selected account was isolated; peer/global links and inode identity
remained unchanged. CLI/MCP admission parity and invalid configuration refusal pass.

Current source: **1,943 tests PASS, one skipped**, Python3.12.13,356.771s,
using the same isolated XDG/RAM temporary-state command/environment above.
Focused60 tests pass on3.12 (12.965s) and3.11 (12.812s). Undefined-name, policy,
focused lint and package build pass. A fresh temporary installation with declared
base dependencies starts the actual codex-wake entrypoint successfully. The
initial deliberately no-dependency installation lacked websockets at CLI startup;
its diagnostic was preserved, then the declared dependencies were installed.
No source change or unsupported dependency workaround was used for that result.
Wheel SHA256:60e82e7394eb05e56b1f24e60c43ba9355835eea62d80044196d2eae6fcbb2ef.
The installed wheel's real-account metadata-only preview reports six admitted
accounts, one inactive account,30 planned aliases and only writer_census_unknown;
production effects remain unauthorized.

The refreshed read-only census maps23 native processes to tmux panes;26 native
processes in total infer the global legacy home. Seven OS-protected processes
remain uninspectable without privileged metadata access. The global credential
file has no observed hardlink peer among the named account credential files.
No credential bodies were opened. An isolated stdlib-only read-only census helper
was prepared privately; it reads kernel metadata, not commands or credential
bodies, and has no mutation/signal/restart operation. Operator-authenticated sudo
was requested to collect the missing evidence. No existing restricted browser
or filesystem privileged helper was repurposed to bypass its scope.

The selective-admission addition is outside the prior frozen broad review.
Counters remain1 broad review/1 findings pass; no second review loop or claim of
live acceptance was made. No source has been merged or deployed. Real activation
requires fresh ownership/dependency qualification, precise effects/rollback and
operator approval before any interruption. #380 remains OPEN.
