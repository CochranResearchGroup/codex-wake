# Documentation reconciliation validation

Base: `1a276d0ff8469e5fbd3deac1e61a7854351fc100`.
Branch: `docs/roadmap-reconciliation`.
Environment: local Linux, Python3.12.13; documentation-only patch. All commands
ran in the isolated branch checkout. No hosted CI, source changes, installation,
service restart or new runtime acceptance. This is not the Python3.11/3.12 full
release/package matrix. Prior42checks/live sample remain historical worker proof.

| Command / check | Observed result |
| --- | --- |
| `python scripts/check_policy_wiring.py` | PASS, zero errors |
| `python -m unittest discover -s tests -p test_ci_scope.py -q` | PASS,1test/2.767s |
| `/home/linuxbrew/.linuxbrew/bin/uvx --from ruff==0.14.2 ruff check --select F821,F822,F823 src scripts tests .codex/hooks` | All checks passed |
| Inline Python relative Markdown file-target check over touched docs | PASS |
| `git diff --check` | PASS |
| `python .codex/skills/repo-policy-selector/scripts/audit_planning_contract.py --repo-root . --active-only --json` | FAIL:3inherited header findings;0new findings |
| Fresh GitHub readbacks | #503CLOSED; #540OPEN; all541–547CLOSED |

The audit's inherited0220/0224/0226 findings exist at the pinned base. No policy
baseline was expanded and none of those plans was changed. The initial wrapper
expected the prior base's two findings; the newer base also carries0226. The
corrected comparison verifies the exact three rather than claiming global PASS.
[Summary](planning-summary.json).

Initial Ruff invocation used `uv run --with ruff==0.14.2 python -m ruff` and
failed before linting: its cached package referred to a deleted temporary scripts
path. Direct pinned `uvx` execution above passed; no source or checker change was
made. Preserve this as setup failure/correction, not a failed lint relabeled PASS.

The workflow scope selector is deliberately conservative: only evidence-only
Markdown/JSON changes can choose its docs lane. This patch also touches ROADMAP
and plan metadata, so it may select full. Applicable local documentation checks
are recorded above; no full release-suite or package/runtime claim is made.


Frozen patch732d9568 scope classification:
`python scripts/check_ci_scope.py --event pull_request --base 1a276d0f --head 732d9568`
returned `scope:full`, `reason:path_requires_full`. The single documentation review
returned Standards0/Spec0; [report](review.md). This records a bounded local docs
qualification, not an unexecuted full-suite pass. Final metadata/link checks are
repeated only for the added closeout artifacts; no behavioral change invalidates
prior lint/classifier/policy evidence.
