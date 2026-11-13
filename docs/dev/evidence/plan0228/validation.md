# LOCAL-P228 validation

Base728b797f49e0c39730203cf6822a12ba8d6620a6.
Frozen review head4c0c0c052b55ee064b1d01095830ba9387f91b99.
Local Linux/Python3.12.13. No hosted CI, runtime/package deployment or policy
profile expansion. Recovered ten surfaces byte-match preserve13d11145 exactly.

- `python scripts/check_policy_wiring.py`: PASS, zero errors.
- `python .codex/skills/repo-policy-selector/scripts/select_policy.py --repo-root . --json`: enumeration completed; no recommendation was auto-adopted.
- Existing `release_selector_bundle.compute_tree_digest` over installed policy-library: PASS `caa14caa565407d12e350bcbf6d7b647f9cc205ed5e1abc71d77aeba69bbc3ac`, matching release/install manifests.
- Recursive local-file SHA256 verification of governance inventory/profile source declarations: PASS.
- Inline Python TOML semantic comparison `.codex/config.toml` versus base: equal; comment-only edit.
- Inline glossary uniqueness check for activity/availability/responsiveness/visible error: PASS; one definition each.
- `python -m unittest discover -s tests -p test_ci_scope.py -q`: PASS1test/3.207s.
- `/home/linuxbrew/.linuxbrew/bin/uvx --from ruff==0.14.2 ruff check --select F821,F822,F823 src scripts tests .codex/hooks`: PASS.
- `python .codex/skills/repo-policy-selector/scripts/audit_planning_contract.py --repo-root . --goal-only --json`: ok:true, zero problems.
- Same audit `--active-only --json`: retains inherited0220/0224/0226 deterministic-header findings,0new findings; baseline unchanged.
- `git diff --check 728b797f...HEAD`: PASS.

An initial ad-hoc source hash checker expected `sources`; actual manifest has
`governance_inventory`/profiles. It failed with KeyError before checking hashes;
recursive shape-aware readback passed, without changing manifest contents.
No tests of runtime/wake behavior were needed for policy/doc/comment-only scope.
No installed MCP reload or claim of live branch-policy admission was made.
