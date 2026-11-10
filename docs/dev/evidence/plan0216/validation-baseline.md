# Validation baseline

Policy wiring: PASS. CodeGraph initialized and status verified (766files,18248nodes);
source changed since indexing, so direct current source remains authoritative.

Active planning audit: FAIL with one pre-existing problem, unchanged from review
base fa2363c: OPEN Plan0214 lacks Current State section. Its existing delivery
paragraph records deployment. This slice does not silently alter its historical
status or add it to accepted baselines. Audit also retains20 historical accepted
findings. P216 itself introduces no reported audit problem.

Commands: Python3.12 scripts/check_policy_wiring.py; Python3.12
.codex/skills/repo-policy-selector/scripts/audit_planning_contract.py --repo-root .
--active-only --json. Full ephemeral audit /tmp/wake216-planning-audit.json.
