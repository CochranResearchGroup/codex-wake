# #353 primary native qualification

Primary integrated source6118f13 plus binary streaming-bound correction. Pinned actual native executable1,114,954,128bytes, SHA25686fad00e38f0c26a5c8d2eb2dbe34536c74655fb2fb45b4efc5d94e97e683b1f; actual stock0.164.0 frontend308,139,304bytes. Initial static256MiB bound excluded both real executables; changed bounded streaming hashing to2GiB before qualification. Public policy RPC timeout remains at most5seconds; the probe's earlier direct-adapter15second timeout was corrected when introducing an actual grant.

Command: `PYTHONPATH=src <repo-venv>/bin/python scripts/goal_notice_native_acceptance.py --app-server <pinned-native> --frontend <stock-0.164.0> --output /tmp/governor353-native-qualified`.

Terminal receipt PASS: real connected server PID/executable and separate client identified; static receipt created then reused; explicit inactive operator state preserved despite missing qualified inference accounting; hard_admission refused truthfully. Activation, stop and deactivation actualTUI rendering/model-context checks also pass; no provider requests; peer unchanged; owned process census empty. Full preflight observations: /tmp/governor353-native-qualified/host-preflight.json. No sampled or hardcap guarantee is inferred from a read-only capability probe; unobserved accounting remains unqualified.

Primary five-case public selection PASS before bound correction (12.114s); same final selection rerun after correction, recorded in /tmp/353-primary-final.log. Worker affected40casesPASS and final5casesPASS remain source regression evidence, not a replacement for this selected-native proof. Repo-wide pinned undefined-name checks and diffcheck PASS. No installed runtime/service or shared session was changed.

Final primary five-case selection:5PASS,12.695s after bound correction.

## Full-CI correction compatibility repair

Run40235630606 on49df3a9 failed on both Python versions: two existing public handoff-correction cases became successor_assignment_blocked. #353 was reopened; local exact two-case reproduction failed2/2 in3.547s. The new shared before_effect guard unconditionally required a spawn-only launch field on handoff/refresh receipts. Restricting optional preflight lookup to available launch metadata preserves the existing non-spawn seam. Exact existing cases then PASS2/2 in5.307s. Combined gateway/ledger/control/notice/preflight/spawn/correction selection PASS33/33 in17.187s (/tmp/353-354-final-selection.log). No test was removed or weakened. Prior CI failure remains preserved; final full CI must run on the successor commit.
