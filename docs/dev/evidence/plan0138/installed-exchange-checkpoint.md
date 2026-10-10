# Plan0138 unit3 — Original installed exchange active

State transition STAGED_PAUSED→AWAITING_INSTALLED_EXCHANGE. Progress: source and
isolated installed94controls PASS43.365s; all80package source files match source
60d2637572848f256f5cb0a715f1d72bb60c3653. Prefix0.11.0-60d2637 is immutable and
isolated; global0.10.1 entrypoints/services remain unchanged. First installed
failure93tests/5errors and correction are retained, not counted as a clean retry.

Private root ~/.local/state/codex-wake/plan0138/a2a/. Normal public configure,
network-time, enrollment, binding and sender delegation commands succeeded.
The default control msg_a42adc299b5446079eb2e0f903cc56d4 remained unread/deferred
with offline receipt under the actual worker; it was explicitly cancelled.
Its first admission attempt held time_uncertain with no effect; a later valid
network observation allowed the same original key. Both receipts remain private.

Actual sender01a12680-a480-7551-a5a7-f115f6357546 completed initiating turn
01a12688-ff67-7a20-bb9c-236b09bfb8f7 while delivery was paused. It admitted only
original request msg_72de4da6556641fc9d2a3935995ac7bd and registered delegated
arm wake_1186ec6fb03c4f02ac68bf48d791dab4, expiry16:13:16.744683UTC. Actual
recipient01a12681-3c92-7b30-b5d7-e3a2dbbee7c8 had completed seed turn
01a12681-cce1-7832-afa3-bdc405ece189, then its owned pane%213/window@201 was
normally closed with conversation preserved. Fresh pre-dispatch readback proves
notLoaded, sameUUID/root/provider. Sender pane%212/window@200 remains for reply.

Owned worker1 PID72816 was stopped by its verified private process group while
bus paused. Old installed0.10.1 dispatch returned paused/submitted0. Restored
candidate show proves exact originalID, body digest, deadline, idempotency key,
same_thread policy and original actor roots/generations unchanged; no new arm
or request. Normal bounded worker2 PID28907 was started from the same command,
verified live, and bus unpaused at16:01:44UTC. Worker duration1200/interval2/
max_dispatches2. Its stdout is unbuffered; handle in worker2.json, logworker2.log.
This detached normal worker survives this controller turn. Its receipt reader
health was ready; generic monitor check reports persistent=false for this bounded
A2A worker, so no persistent supervisor/service readiness claim is made.

Next: reconcile original request/reply and exact native completed turns; never
manually reply, recreate tabs or replay either original notification. Check
workerPID live/terminal and exact public mailbox evidence first. Sender initial
prompt and request authorize one reply only. No controller body relay follows
activation. Native queue acceptance alone is not execution. Preserve any failed
original record and investigate only an observed defect. On success, close only
sender test tab; preserve both saved conversations. Old unit1 supervisor50807
also remains owned and quiescent, to stop at cleanup.

Material outstanding gates: actual recipient/sender follow-up completion, installed
review/cleanup, public release and integrated source/installed parity. Full goal
remains active; checkpoint18:15:33UTC and stop before18:25:33UTC or3milliontokens.
No unrelated session, service, LitScout repair, Codex binary or shared daemon changed.
