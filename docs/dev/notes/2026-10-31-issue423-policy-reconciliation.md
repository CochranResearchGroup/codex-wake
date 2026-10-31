# Issue 423 policy reconciliation | 2026-10-31

Owner: ecochran76. Work item: #423, parent #420. Scope: reconcile local-only
`7352695bad2bc0d4d3af2d227ef7a97cdd2a147c` and
`43e3db2c067facc93c07677ee6de75f92b6cb4b4` against canonical
`5fcf2d65052c3316f84d821c6ff1d233e6746187`. Source integration remains a
primary-coordinated PR gate; this receipt grants no runtime or governor effect.

## Commit dispositions

Neither policy intent was superseded: all seven affected canonical policy bodies
still equal the first commit's parent. Carry the v0.1.34 library, selector,
release notes, install provenance and seven policy bodies exactly from7352695.
This preserves resource ceilings/reserved closeout, ticket-driven vertical
slices, compact working state, acceptance-focused testing, cumulative allocation
review and standard policy MCP semantics. Bundled development isolation and
runtime/product boundary changes remain library templates; no additional local
policy modules are adopted. The original dated rollout receipt remains historical
provenance, not a fresh validation claim.

Reject7352695's generated AGENTS output: it erased product/MCP/skill routing and
added30 references to nonexistent23–52 policies. Canonical main already retains
the correct22 paths, routing and CI-cost policy; preserve its AGENTS byte-for-byte.
Do not manufacture missing policy bodies or apply a newer release.

Carry43e3db2's reviewed profile selections: policy-context MCP section selectors,
work-item-traceability source and cited ticket-driven obligation, and complete
canonical fallback list. Retain the other scope/task/citation decisions. Refresh
inventory and profile hashes against the final canonical files, including the
preserved canonical AGENTS. Do not copy its obsolete AGENTS hash.

Both original commits remain preserved through parent420 custody refs/bundles;
this branch does not move the primary main ref or alter original history.

## Pin and authority evidence

The installed v0.1.34 manifest names source8b59d04f16fee097b809edf59483c150a946e1f0.
GitHub's annotated tag99f23ec26348fd6be4d5311ef62884f3da1a1b9e peels to
be1a924dc04588fea2f2844f3e4775dd6c31396b. Authenticated archive comparison
proves all129 installed selector files, including manifest, catalog, profiles,
modules, scripts, tests and releases, byte-identical to that tag; no missing or
differing files. This establishes bundle equivalence without pretending the
manifest's source commit is the tag target. The declared library tree digest is
38870d55dab14ac689dbbbcbf5a5305a3fd70cf30874418431a3db64c2119c42.

The session MCP is rooted in the primary checkout and returned its43e3db2
packet; it is not authority for this worktree. Read branch-local canonical
Markdown and qualify the installed CLI with this branch's explicit root.
The profile remains policy-maintenance only, not product/release authority.

## Local validation and limits

- `python scripts/check_policy_wiring.py`: PASS;22 unique existing paths,
  exact inventory/profile hashes and canonical fallback paths.
- `python scripts/policy_context_qualification.py --governance-cli <pinned
  4f0ef58 prefix>/bin/governance-context --receipt <user-scoped receipt>`: PASS
  current hydrated profile, retained-packet freshness, changed source, missing
  file, added file and out-of-scope controls. No production effects.
- `python .codex/skills/repo-policy-selector/scripts/select_policy.py --repo-root
  . --json`: already-aligned; no validation problems.
- Selector `test_select_policy.py`:42 tests PASS. Full downstream suite initially
  ran128 tests with11 errors because source-repo contract tests expect sibling
  `modules/`, absent in a downstream bundle. Preserve this first failure; run
  the full suite in the authenticated release-source layout instead.
- Goal audit: PASS. Active planning audit: eight failures, exactly equal to
  canonical baseline: missing deterministic states in0166–0169,0177,0178,0190
  and missing Current State in0176. This policy slice changes no plan artifacts;
  those existing shared-plan defects are explicitly deferred to the coordinator.
- Focused Wake policy wiring regression:1 test PASS. Hosted Actions skipped
  under operator cost policy. Local environment is Python3.12.13 on the
  workstation, rather than hosted Ubuntu's3.11/3.12 matrix. No product behavior
  changes, so installed Wake/native/runtime checks are not repeated.

Additional validation: all128 selector tests PASS in the authenticated upstream
release-source layout; pinned ruff0.14.2 F821/F822/F823 PASS across Wake src,
scripts, tests and hooks; library tree digest and `git diff --check` PASS.

## Dirty build-0165 policy custody

The coordinator assigned the unique uncommitted0006 installation-gate hunk from
build-0165 to this policy lane. Canonical0006 lacked its operational constraints.
Retain that section verbatim as a repo-local rule, without changing the bundled
shared module. It requires either a separate real Linux UID or disposable WSL,
exact complete package/launcher/history/reconnect/rollback proof, final process
census and preserved protected supervision state before proposing working
installation. Qualification grants no installation authority. The existing
profile already selects the entire0006 subtree; refresh its inventory/profile
hash without broadening policy-maintenance scope. Original dirty source remains
untouched and protected by parent420 custody. No installation was attempted.

Full command outputs, archive comparison, per-path dispositions and baseline
comparison are retained in the user-scoped reconcile420/423 evidence directory.
Memory disposition: unavailable; no reviewed Wake Graphiti group is configured.
Primary owns final shared ledger, integration, issue closure and main re-anchoring.
