# LOCAL-P222 validation

Base: a337f510c27bef600fc95a375682c2fadbf5f59d. Linux/WSL, Python3.12.13;
source checks use PYTHONPATH=src:tests and the installed dev8 dependency runtime.

## Red to green

- `python -m unittest test_tab_formatting.FormattingTests.test_opted_in_refresh_recovers_replacement_and_rollback_stays_disabled -v`:
  RED unknown recover_namespace; GREEN through public controller refresh.
- `python -m unittest test_tab_format_autostart.FormattingAutostartTests.test_monitor_started_before_configured_socket_discovers_it_when_created -v`:
  RED late socket never discovered in6.310s; GREEN after socket-generation
  invalidation and bounded automatic discovery. Terminal config is unchanged
  between service start and socket creation.
- `python -m unittest test_tab_startup.StartupTests.test_unit_escapes_systemd_specifiers_and_quoted_paths -v`:
  RED literal-dollar root path would expand in systemd; GREEN after escaping.

## Focused source validation

`python -m unittest discover -s tests -p 'test_tab*.py' -q`:
258tests in113.217s;257PASS and1catalog declaration failure. Declared startup
operations local-only, regenerated command reference/coverage. The first corrected
selection caught stale generated docs; regeneration resolved that failure without
changing assertions.

`python -m unittest test_tab_contract test_command_contract test_tab_startup -q`:
11PASS in5.930s after declaration/regeneration.

Final review correction and new hold regression:
`python -m unittest test_tab_startup test_tab_formatting test_command_contract -q`:
15PASS in17.766s. This is broad validation plus focused remediation, not a claim
that the first broad command was all-green.

Pinned ruff0.14.2 `check --select F821,F822,F823 src scripts tests .codex/hooks`,
`python -m compileall -q src tests .codex/hooks`,
`python scripts/check_policy_wiring.py`,
`python scripts/generate_command_reference.py --check`, and `git diff --check`:
PASS. Standards and Spec primary reviews have no remaining blocking findings.
Only one review/remediation pass; no debug instrumentation.

## Packaged runtime qualification

Complete0.22.0.dev9 wheel installed with pinned existing dependencies, no source
path injection. Real Linux UID1017:16 public controller/CLI/startup/late-socket
regressions PASS16.033s; installed CLI/stdio/OAuth API acceptance PASS; prior→new→
prior→new package/launcher selection retains durable policy and no-dispatch poll.
Previous package is a byte-exact public installed-package repack, not an original
wheel. No private history or credentials copied.

UID1017 has no user-manager bus. A temporary user-manager probe exited1 and did
not establish a manager. Actual unit acceptance therefore used the working
user's real systemd manager with disposable fixture state only: unit started
before terminal readiness; automatic replacement recovery retained originals and
settings; repeated enable kept monitor generation; restart retained rollback and
pane identity; safe disable stopped only the fixture unit. Final reviewed wheel
passed this sequence. Fixture unit was disabled and removed after each run.

No host reboot, provider calls, new agent/conversation or native Codex binary
upgrade. UID1017 Python3.12.3 and working3.12.13 share the Linux kernel. No full
suite, Python3.11, native Windows or real-login reboot claim. Hosted CI skipped
under operator cost policy. Exact source/wheel/deployment binding is recorded in
the installation receipt; private logs remain under qualification/plan0222.
