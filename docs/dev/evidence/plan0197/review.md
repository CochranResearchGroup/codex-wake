# Plan0197 review and bounded remediation

One broad review, frozen atcd1249711213453fa8aeafa1a6a35636aa3938cc against
6fb4fe7a9b6511a6bca4d090298cb85daf59ebf3. Compared with
`git diff 6fb4fe7...cd12497`; commit list `git log 6fb4fe7..cd12497 --oneline`.
Spec: Plan0197 and its five local tickets. Reviewers were read-only; primary
reproduced and adjudicated all candidates. No second broad review was run.

## Standards

Reviewer /root/review_standards returned no actionable candidates. Primary found
no evidenced documented-standard breach in that report. Accepted findings:0.
Standards/policy sources: AGENTS.md, GLOSSARY.md, agent discovery/runtime guides,
and policies0003–0006,0014,0016,0017,0021. No CONTRIBUTING.md or
CODING_STANDARDS.md exists. Fowler smells were treated as heuristics, with
repository policy taking precedence; no tooling-enforced issue was re-reported.

## Spec

Reviewer /root/review_spec returned two candidates. Both were independently
reproduced by primary in a disposable registry and accepted as blocking:

- S1: `completion.py` normalized `accounts.enabled` without resolving aliases.
  With known alice, alias work=alice and enabled=[work], the existing account
  owner admitted alice but completion returned no suggestions. Requirement6:
  locally registered account-name suggestions must respect selected admission.
- S2: equal-form flags completed static choices but skipped account discovery.
  `builds list --account=al` returned no candidates while the separate form
  worked. Requirement6 promises account-name completion for supported flags.

Both are fixed at24e4cc1b884338077afe9585fc8b4cc7ee665557. S1 resolves enabled
aliases before prefix normalization. S2 returns full flag=value candidates for
account names/aliases. No finding was rejected, deferred or left needs-evidence.

## TDD pass1 and focused verification

One bounded remediation pass, two vertical red/green cycles:

- Red: `venv312/bin/python -m unittest discover -s tests -p test_completion.py`
  failed the new enabled-alias test (expected alice/work, received empty).
  Green: `PYTHONPATH=src:tests venv312/bin/python -m unittest
  test_completion.CompletionTests.test_enabled_alias_uses_the_same_account_admission_as_owner`.
- Red: `PYTHONPATH=src:tests venv312/bin/python -m unittest
  test_completion.CompletionTests.test_equal_form_account_flag_completes_names_and_aliases`
  failed (expected --account=alice, received empty).
  Green: same test plus the existing actual interactive Bash/Zsh Tab test,
  extended with an equal-form account flag. Both real shells pass.

Final Python3.11/3.12 checks per version: `unittest discover -s tests -p
 'test_*completion.py'`13PASS plus `'test_command*.py'`12PASS. Undefined-name
lint and generated-reference/coverage staleness checks pass. Earlier full local
presubmit240tests/16checks per version atc0fafa2 remain separately attributed;
only completion code/tests changed after that qualification. Earlier setup/path
failures and the transient clock observation remain recorded in acceptance.json.

The exact final wheel was reinstalled through scripts/install.sh into disposable
UV tool/home roots.236Python members match source/wheel/install; alias admission,
equal-form account suggestions, fresh shell activation and preserving uninstall
pass. No live operator configuration or provider effects. Final fixture process
census empty; clean worker branches/worktrees retained.

Standards:0accepted, no severity. Spec:2accepted blocking findings, both resolved.
