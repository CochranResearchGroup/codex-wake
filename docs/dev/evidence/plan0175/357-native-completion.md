# #357 native completion funding acceptance

Source e8eaabe (worker82a30b9), extended native driver SHA256 `b61ac79908ec73dc90ed788c1b8609a280e7e38d70783d0bc0cf48b5f06fb9bf`.

Command: `PYTHONPATH=src <repo-venv>/bin/python scripts/request_admission_native_acceptance.py --app-server <pinned-native> --frontend <stock-0.164.0> --output /tmp/governor357-native --completion`.

PASS with the same pinned actual native/stock frontend as #354. Original cap207, measured warmup7 imported before hard coverage, per-request provider-enforced maximum50. Three named obligations protect50tokens/10seconds each. First implementation request spends50, bringing usage57; the next implementation request is denied BEFORE forwarding with150tokens protected. Actual TUI shows completion_resources_protected and fresh used/reserved/remaining/cap/deadline values. The host binds each named acceptance/review/remediation funding request; each real native request forwards once and settles50. Final usage207/207, reservations0, original deadline retained, correctioncycles1. All named funding obligations have source-backed host dispositions; objective_complete remainsFALSE because funding is not semantic acceptance.

The single typed Deactivate governor command still works at ZERO through actual stockTUI, produces explicit Governor-generated acknowledgement with0paidinference, preserves usage/cap207 and pausedgoal, and starts no work. Live hardactivation includes actual Used7/207 and precedes guardeddispatch. Provider calls:1warmup+4guarded; externalprovidercalls0; freshownedhome processcensusEMPTY. No production service/mask/configuration or budget was changed.

The named stages are INERT FUNDING FIXTURES, not actual code review or remediation of this repository. The requested one formal Standards/Spec review and one postreviewTDDpass remain unexecuted at this checkpoint.

Primary affected selection: `PYTHONPATH=src:tests <repo-venv>/bin/python -W ignore::DeprecationWarning -m unittest test_completion_reserve test_request_admission test_objective_ledger test_goal_notices test_governor_deactivation test_host_preflight -q` —30PASS15.201s. Initial local command named a nonexistent test_completion_resources module; its failed log /tmp/357-primary.log is not counted as passing evidence. Correct command /tmp/357-primary-final.log above. Worker24affectedcasesPASS7.452s; broader finalCI remains required.

No arbitrary external provider or default installed route is claimed qualified. Semantic completion dispositions are trusted host/controller evidence, not inferred from counts. All source changes remain in the integration branch; deployment is separate.
