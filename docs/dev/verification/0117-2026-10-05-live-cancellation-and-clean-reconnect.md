# Live cancellation and clean reconnect continuation

Parent Plan0119/issue181. New user goal carries its own1100000-token checkpoint
ceiling. The supplied Plan191 reference matches Plan119; no Plan191 exists here.
Source remains exact merged eb79e927fb227af3657d5b121aa17026294976d7, stock
Codex0.160.0, native installed private CLI. No new transport/runtime source fix.

## Clock and scope

Current25-sample read-only clock probe observed a2.29-second wall-clock step.
Old mailbox elapsed drift was-291.93 seconds, near its unchanged300-second
continuity limit. Existing records/checkpoints were preserved. New native
configure/enroll/migrate/bind/delegate/resume commands established explicitly
authorized continuation-v2 with original A/B threads and a fresh journal/arms.
The product guard was not weakened; no host settings or shared daemon changed.

## Cancellation PASS, attempt1/2

Actual A native send admitted msg_7c07970193f34615ab2db6d5524dd5fe; native cancel
committed receipt_5cd92578f3784996a4b17dbeadecd7c7. Notification became suppressed,
recipient stayed unread, and zero transport attempts existed. B's exact owned
P119_CANCEL_HOLD composer fixture was unchanged while blocked and cleared only
after cancellation committed. Remaining bounded worker observations prove the
cancelled message stayed suppressed with zero attempts after B became eligible.
WorkerPID49423 ended0 with no residual process. Observed monotonic cancellation
upper bound from pre-admission absence:19.223seconds, within120. No retry needed.
Private continuation-v2/cancel-1 contains actual actor outputs, immutable native
receipts, guarded observations, cancelled-proof, final-proof and worker custody.

## Clean reconnect automatic return PASS, attempt1/2

Actual A admitted msg_bfadee8841474abd80ed90d6a69210a1 and registered its reply
arm while B was disconnected. Pending-before-reconnect proves no request attempt.
Controller explicitly resumed the ORIGINAL B thread and rebound its actual new
client generation. Product request attempt_ce89e865e7b64018bd549f44af1b8cf9
submitted once. B read/claimed and sent one correlated reply
msg_25873f23a2024277a5f4d38265ac63f3. Product return
attempt_653b86b5322e48d294639c0fdc504eba submitted once; actual A read receipt
receipt_f5d329d248ab4647b2236b8d59dd427e and accepted ack
receipt_056626815d0e4b2cbe7c29e52d85334b followed. No controller message/body
relay or foreground inbox helper after admission; reconnect is explicit lifecycle
setup, not a message turn. WorkerPID75707 ended0, two submissions/97ticks.

Actor turn readbacks show the actual product notification inputs and native
read/ack/reply operations. Read receipt wall interval is95.665seconds. Saved
deadline-proof bounds monotonic progress from the last pre-admission absence
observation to the post-read accepted-ack clock checkpoint at118.185seconds,
within120. The file observer's timeout was not treated as a terminal failure:
actual native receipt and process/journal readback established the outcome.
Private continuation-v2/reconnect-1 preserves actor outputs, actual turn JSON,
mailbox-final-proof, deadline-proof, both attempt records and worker-terminal.

## Still open

Full owned-worker restart with client reconnect, normal released installation,
explicit second root/unenrolled denial, installed rollback and30-minute owned
soak remain to be proved. These passes do not close Plan0119 or issue181.
