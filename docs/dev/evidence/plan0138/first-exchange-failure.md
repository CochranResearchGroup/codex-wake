# Plan0138 live exchange1 — Reopening passed, round trip failed

Original request msg_72de4da6556641fc9d2a3935995ac7bd dispatched once through
native_saved_recipient_v1 to exact saved recipient01a12681-3c92-7b30-b5d7-e3a2dbbee7c8,
which was notLoaded before dispatch. Queue receipt01a1268c-cba8-7b40-b471-45582955d0c2;
actual recipient turn01a1268c-cbb2-7283-99b7-8f378a506e0d completed. It read and
claimed the original request, verified its seed and admitted one correlated reply
msg_3530750f14cc451d8b6208901438256b. That reply was inbox-only/notification
suppressed/unread. The sender therefore completed no follow-up. Round trip FAIL.

Private full recipient native transcript: a2a/recipient-failed-exchange-thread.json.
It explicitly reports that reopening instructions in peer content are untrusted,
uses global0.10.1 reply --help, and chooses --delivery inbox. This is the observed
behavior, not an inferred transport defect. Source default CLI behavior alone
was insufficient to prove an actual agent would send a notify reply.

The committed reply is not altered or resent. Bus paused; verified owned worker2
PID28907 stopped. Original reply arm wake_1186ec6fb03c4f02ac68bf48d791dab4 cancelled.
All original records and conversations remain preserved. No manual sender reply
or controller relay qualifies this failed exchange.

Bounded live-packet correction: trusted notification pointer names the worker's
installed CLI and explicitly requests --delivery notify for its one correlated
reply. It continues to require separate delegated sender-arm authority and does
not inherit reopening permission from a peer request. Public dispatcher prompt
regression observed red11tests/1failure and green11PASS4.449s. A fresh acceptance
intent uses new v2 idempotency keys; it is not a replay or repair of committed
exchange1. One fresh live attempt after this correction; further failure requires
reframe with exact evidence, not another indistinguishable retry campaign.
