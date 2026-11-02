# Installed native qualification for incremental activation (#380)

This qualifies the current Wake wheel in disposable wsl-test, Ubuntu UID1000.
It does not qualify the operator's live authentication or close #380.
Source implementation5f8c467; wheel SHA256
60e82e7394eb05e56b1f24e60c43ba9355835eea62d80044196d2eae6fcbb2ef.

Actual complete modified0.166 binary:
48ed489ceed144d277c44a505ef5cbcb63250fa361fe132bed1fdab3f7cfb7d5.
All six package files/hashes/modes matched the original accepted inventory
fe4266c33a9c2e71b08bb09df0aa5359d59d16b1307cea0bc536e2fd5a852003.
Retained modified0.165 baseline:
0d511c4a77c56b0a09f8549f6e43218ee899d0b66598725d4b67c71dc935a973.
Official0.166 stock binary:
b8a11fedf24b2dfb59a70c9e52b030f9a508dcd49cd2dd0d41956f4c785156b8.

## Observed outcomes

The first installed-package history case passed in36.627s, under its600s
packet. Native TUI history in three homes remained visible through165/166
launch, reconnect, failed-start recovery and compatible rollback. Private-client
ownership and incompatible-schema refusal passed. Each child also exercised
current controller admission/configuration before the public history.resume path;
an inactive configured account did not block the admitted homes.

A separate concurrency/stock case initially failed during baseline setup:
thread/read(includeTurns) was requested while turn/start was still inProgress;
list_turns returned unsupported before any local seed response. The raw failure
and empty teardown census remain retained. A correction under the original bound
was held for insufficient remaining time, without starting another native case or
renewing the packet.

The independent synchronized case waits for the actual turn/completed event
before reading saved turns. Native binaries and success assertions were unchanged.
It passed in40.708s under a new explicitly recorded240s packet:

- Two actual native clients occupied different admitted account homes together.
- One home resumed its saved conversation with modified166, official stock166,
  and modified166 again while the other modified166 process and conversation
  stayed pinned. Executable hashes were observed through /proc for every launch.
- History visibility, reconnect, failed-start preservation, compatible rollback,
  incompatible-history refusal and same-home private-client exclusion passed.
- Both native and outer-driver final owned-process censuses were empty.

Both successful cases used synthetic history and three explicitly scripted
localhost Responses calls per case. Real model requests0. The owned proxy blocked
background external CONNECT attempts; those attempted destinations remain in
private receipts. No external provider response or live-account claim is inferred.
No production goal, governor, allowance, service or session was changed.

## Staging and next gate

The six verified modified-package files were copied read-only from the completed
WSL artifact into a new immutable working-host staging prefix. Both official stock
and modified166 passed public pinned version inspection on the working host using
neutral temporary homes. The active native selection and launchers were unchanged.
Old upgrade jobs, deadlines, source/review contexts and compiler cache stayed intact.

The operator's privileged metadata snapshot inspected1,687 processes, unknown0,
and found no selected-home dependency. It is a snapshot, not ongoing permission:
actual migration guards must collect fresh privileged metadata at each effect.
Read-only planning now limits initial activation to five accounts/25 aliases.
The protected mutable-directory account and a retained managed account with goal
state remain outside that cutover. No #413 recovery or old-goal resume is authorized.

Live authentication, installed public CLI/MCP readbacks on the actual account
layout and any final protected-account activation remain unaccepted. Canonical
receipts, failures, actual PID identities and packet clocks remain user-private.
