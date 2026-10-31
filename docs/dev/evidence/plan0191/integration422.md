# Canonical publication packet for #422

This packet proposes the qualified recovery/controller reconciliation for canonical Wake main. Base: `5fcf2d65052c3316f84d821c6ff1d233e6746187`; local qualified source: `9ff60357011788a9edabedfd768bca0a6c23030c`; qualified product: `793a82b440ad69157b825d9ebba764c446a8697c`. Main integration requires the actual PR merge/readback. Parent #420 owns that gate, the current worktree/lane disposition projection and final runtime readback. Plan0191 remains the historical isolated qualification authority.

## Content and custody correspondence

The proposed tree carries the qualified Wake source, launcher repairs, acceptance harnesses, glossary, historical plans and curated qualification receipts. Recovery terminology and distinct `P179` / `P179-NATIVE0165` lane identities are preserved alongside controller source. No runtime/native implementation changes are added by this publication packet.

All 662 tracked files under `src`, `scripts`, `tests`, `.codex` and `pyproject.toml` are byte-identical to the qualified source. Product source is also unchanged between product793a82b and qualified9ff6035. Thus the existing exact-source serialized Python suite (1,911 total / 1,910 passed / 1 skipped), 30 final managed matrix journeys plus one actual predecessor-pair journey, health/Bots and native protocol/package acceptance remain applicable. This is evidence reuse, not a new execution or production claim. The first expiry timing failure and its unconfirmed cause remain disclosed in qualification.md and the original local logs.

Native source `bf4df44cd51f8a5e1d1ee828633beaec62a46cb5`, original qualified Wake ancestry and native patch payloads stay private/local. Publication uses a new canonical-base commit, without the original qualified ancestry. Two payloads are deliberately excluded; local original source retains both:

- `9ff60357011788a9edabedfd768bca0a6c23030c:docs/dev/evidence/plan0179/native-0165.patch`, SHA256 `2e4ab610f8d461b81cba0cece722cb053bad4efae4a99842a225b910c0c5a135`.
- `9ff60357011788a9edabedfd768bca0a6c23030c:docs/dev/evidence/plan0180/oauth-fixture-fix.patch`, SHA256 `38c75b55d8c83d6df649d1e772e13b9ca353b987a7869c1cac5811b67bbffcc9`.

Three historical prose references now identify this private custody explicitly; no referenced payload was silently discarded. Original inputs and qualified history remain untouched. The #422 worktree/branch is retained for primary review and merge; primary owns subsequent clean retirement and catalog reconciliation.

## Fresh local validation

On Linux/WSL, Python3.11 and Python3.12 each pass 16 tests with source `PYTHONPATH` and fresh private HOME/config/state/CODEX_HOME:

```
PYTHONPATH=src:tests python -m unittest test_profile_launcher_forwarding test_managed_channel_launcher test_absorbed_profiles_concurrency test_controller_accounts -v
python3 scripts/check_policy_wiring.py
ruff check --select F821,F822,F823 src scripts tests .codex/hooks
python3 -m compileall -q src scripts tests .codex/hooks
git diff --check
```

All pass. The first Python3.11 setup used an interpreter without the declared websockets dependency and failed one import; the existing qualified ci311 environment then passed. That initial setup log is preserved, with no product change. Ruff is the available0.15.8 rather than hosted0.14.2. Hosted CI is skipped under the operator cost policy; no paid run, installation, service change, package selection, governor activation or native acceptance rerun is authorized or performed. Shared WSL and non-Windows/non-real-model qualification limitations remain those in qualification.md.

Exact commands, interpreter identities, byte-comparison count and logs are in user-state `reconcile420/422/validation.json`; initial setup in `validation-first.json` and `focused311-missing-dependencies.log`. This packet is delegated to ticket422; effective inherited model is not exposed by the runtime. Primary retains integration, tracker closure, shared plan/catalog and final protected-runtime authority.
