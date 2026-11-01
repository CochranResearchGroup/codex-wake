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
