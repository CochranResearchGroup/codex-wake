# Ticket0143 installed exchange — PASS

Immutable installed candidate0.11.2-313e5aa, source
313e5aab7f01fb27df84a7ec70dafcda8950fe66; source PYTHONPATH unset.
Ticket0142's117 installed controls and81-file parity apply unchanged. No new code.

Owned A01a126ec-d039-7041-b927-92c94480ad1f and
B01a126ec-f920-7da0-a45f-34bd551336ca used private bus p71-pair.
A sent request msg_bcd7ab59ca7b45bc942af2ed67e75cf8 and armed original
wake_41c375b66a0d428488e6060925a8a432, then initiating turn
01a126ee-18f1-7d41-a66a-c62e7ac363d7 completed before activation.
B's setup turn01a126ed-cc0d-7022-86f5-e22dede90037 also completed first.
No controller relay, post-admission queue prompt or foreground inbox poll occurred.

Request attempt7399b9042e1646cc8ae89c419cae06bb has native queue receipt
01a126f0-0263-7b81-b918-02d057de8927. B's actual notification turn
01a126f0-0267-74f1-b367-c286b37a0c31 contains exact request and attempt markers,
claimed work, computed1739+2864=4603 with unchanged nonce and sent one correlated
result msg_34afee750f744cd6924a749e0f84b5c4. Request terminal receipt
4978d6b4a32f4a3ca860e8c1b72a8d08 records completed processing.

Reply attempt4952334e622a412ebd907650a8c509ff has native queue receipt
01a126f0-b592-7eb2-9c0f-96812f4d94f5, native_live_recipient_v1.
A's actual return turn01a126f0-b594-7342-9796-c7962761e332 contains exact reply
and attempt markers and completed; terminal receipt674ba812245c450bafea09daf8b0fec9.
Both public message states accepted/submitted/completed. The receiver generated
the answer; the controller only supplied request input and observed evidence.

Worker43581 was stopped by verified PID/start-ticks/argv while bus paused and
the original request pending; replacement50774 used the same bus/bindings/arm.
Old lease expiry and pre-effect time_uncertain holds are retained. Replacement
finished normally with exactly two committed submissions,27ticks. A clock hold
after reply commitment left the arm firing when that effect budget ended.
One public dispatch on the now-paused bus reconciled its existing committed
receipt: arm submitted, dispatch paused, results=[], submitted0. This was
bookkeeping recovery, not a second transport or controller delivery. Earlier
Verification0122 reconnect/soak is historical evidence only; the changed transport
and private worker restart are qualified here, with no new blanket soak claim.

Both exact tabs closed normally forced=false, affected_messages/wakes empty,
conversation histories preserved. Fresh OS readback: clients14938/16667,
workers43581/50774 and panes%231/%232 absent. Private bus remains paused.
Raw setup, capabilities, histories, freeze, original receipts, worker logs and
cleanup are retained under ~/.local/state/codex-wake/plan0143/.
No unrelated session, service or LitScout repair was changed.

Memory disposition: unavailable; no reviewed Codex Wake Graphiti group is available.
Non-write receipt is retained privately. Release/activation belongs to0144;
remaining recovery and campaign gates remain OPEN.
