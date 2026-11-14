# Persistent wake source validation

Qualified code: `a32da00c5315a8db04a6aa1949e1045f02a1b558` (0.22.0.dev20).
All six child tickets CLOSED; PR #618 is the integration handoff. Parent #610
retains spec discussion. No merge, working-host upgrade or production scheduling.

Local Python3.12.13/Linux validation replaces paid hosted CI. Commands:

- `python -m unittest discover -s tests -p 'test_*.py' -f -v`, then bounded
  serial explicit-ID continuations: all 2564 discovered cases (2546 unique IDs)
  have passing coverage. This combines source5ba/adf/a32 and affected regressions;
  it is not a single uninterrupted full-suite run at one commit.
- Focused remediation: 90 tests passed, plus two critical restart/history
  regressions; native/Grok/policy23 and publication7 passed at final source.
- `python -m ruff check --select F821,F822,F823 src scripts tests .codex/hooks`,
  `python -m compileall -q src tests .codex/hooks`, policy wiring, active-plan
  audit, command-reference check, CI scope and plugin checks passed locally.
- `python scripts/validation_build.py --outdir <private>/qualified-dist`:
  wheel SHA256 `cb59542ba2be825f6ce33fcfa9398439e55f67f358fb4598293c74c887f2e6c5`.
  Installed disposable-prefix CLI register/show/revise/cancel passed; armed=false.
- Exact baseline `e8c79a79` source holds new-mode records while current reader
  accepts them. This is source compatibility, not installed legacy qualification.

Original timeouts and failures are retained: deep temporary socket paths exceeded
OS limits; isolated HOME hid existing rustup for version-only synthetic preflight.
Both environment causes were corrected. An existing asynchronous publication test
now waits for both rows and freshness within its unchanged three-second deadline.
Native-only mode metadata was removed from unsupported Grok tool schemas.
No new fixture framework, native build, provider turn or live restore was run.

Raw manifests, source commits, commands, timings, failures and final coverage.json
are retained outside Git at `~/.local/state/codex-wake/validation/persistent-610/`.
Hosted Python3.11, Windows, live provider/Byobu restore, installed legacy upgrade
and working-host daemon acceptance remain unqualified and are deployment gates.
