# #780 separate Wake server qualification

Two independent Wake owner roots and two PostgreSQL 17 containers exchanged
messages over separate restricted OpenSSH listeners. This ran in disposable
local Linux state using staged source, a deterministic injected clock and
a subprocess receipt adapter. It exercised the public `message-owner`
commands and separate databases. No production service was changed.

- The destination committed original timed Message
  `114af455-b5b8-4611-9280-aff99c76f489` before the SSH response was lost.
  The sender retained `waiting_for_peer`. The destination showed
  `waiting_for_time` until the original due time `2000000010000000`.
  The original expiry `2000000090000000` remained unchanged.
- The destination recorded one effect and receipt
  `fixture-harness-114af455-b5b8-4611-9280-aff99c76f489` while responses
  were still being dropped. Repeating the original request recovered that
  same receipt without another effect. Changing the body under the original
  ID was rejected. The sender's PostgreSQL database had no recipient Message
  copy.
- The reverse route delivered reply `5904012b-9e17-43b0-866e-2e4c0625cf10`.
  The reply receipt and recipient database both retained the original
  `in_reply_to` value.
- An expired message produced no effect. A harness invocation with no
  acknowledgment recorded one `uncertain` attempt under its original
  identity. Retried owner polls did not rerun that invocation.
- An incorrect peer key, incorrect server host pin, unexpected SSH command,
  incorrect owner pin and remote settings frame were refused. None admitted
  the negative-test Message.

Local regression ran 35 tests against a disposable PostgreSQL database.
The focused exact-response regression passed separately. Compilation,
Ruff undefined-name checks and policy wiring passed. Hosted CI was skipped.

```sh
PYTHONPATH=src:tests python -m unittest test_message_owner test_controller_hosts \
  test_postgres_message_delivery test_messages_cli test_message_cutover \
  test_native_protocol_large_response
PYTHONPATH=src:tests python -m unittest test_message_owner.CrossServerReceiptTests
python -m compileall -q src/codex_wake tests/test_message_owner.py
python scripts/check_policy_wiring.py
```
