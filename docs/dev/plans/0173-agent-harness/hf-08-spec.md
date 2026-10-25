# HF08 independent work acceptance

State: OPEN
Owner: ecochran76 / primary
Work item: https://github.com/CochranResearchGroup/codex-wake/issues/335
Base: 4570306

## Current State

Operator selected the recommended deterministic checks plus explicit decisions in
form response d9b59f368e984dff925597304f90e901. Implement one public acceptance
owner and equivalent CLI/MCP paths using existing task pins, custody and policy.

## Frozen behavior

An operator or exact task-delegated controller freezes an immutable acceptance
contract against an actual admitted assignment pin. Workers may request evaluation,
never approve/replace the contract or supply successful outcomes as evidence.
A contract lists required canonical artifacts and exact SHA256 values, optional
bounded deterministic verifier argv/cwd/exit classifications and optional named
human/reviewer decisions. Everything stays within the approved brief workspace.
No shell interpolation, model-selected roles, arbitrary verifier overrides, new
permission grants or universal same-UID isolation claims.

Evaluation revalidates the exact original pin, artifact snapshot and current
acceptance.verify permission before each verifier effect; required resource
custody guards command execution. Verifiers are approved non-daemonizing local
process-group commands, bounded to at most30seconds, discard output, and clean
up their own process group. A known required check failure is rejected. Missing,
stale/changed or unreadable artifacts, verifier infrastructure/timeouts/unclassified
exit codes and absent/stale decisions are unknown, never convincing-message
success. Acceptance binds exact contract revision/digest, pin, artifact digests,
optional Git commit identity, check results, deciding authority and observation.
Artifact/pin/commit changes during or after verification invalidate prior evidence.

Human/reviewer outcomes are explicit authenticated decisions against the exact
contract and artifact snapshot; they neither run operations nor widen permissions.
Independent deterministic checks execute from the frozen contract. A worker done
message alone never changes acceptance. Results are typed accepted/rejected/unknown
and can be inspected as future branch predicates. Inspection revalidates snapshots;
original receipts remain retained when evidence becomes stale.

## Public seams and acceptance

WorkAcceptance defines contract/evaluate/decision/inspect; command adapters use
existing verified CLI principal and trusted native caller/controller delegation.
MCP never exposes an operator role or arbitrary argv on evaluation. Tests cover
real local artifact bytes and Python verifier processes, required failed/missing
checks, stale pin/artifact/commit, verifier errors/timeouts, current permission
revocation, explicit judgments and actual caller refusal. No provider, production
installation, unrelated workflow engine or quality-score framework.
