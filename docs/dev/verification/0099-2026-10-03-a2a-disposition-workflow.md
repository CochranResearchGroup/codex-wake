# Plan 0106 recipient disposition workflow verification

Parent: Plan 0101 / P63.6 / issue #181
Branch: docs/p63-delivery-qualification
Outcome: bounded foreground workflow accepted; long suspension remains open.

The executable messages wait parser supports received, reply, accepted,
declined, completed and failed. Historical recipient evidence is queried from
the authoritative journal without depending on the displayed 100-receipt cap.
Each satisfied disposition returns its exact committed receipt ID. Participant
and actor revocation checks remain enforced; observing does not read a body or
claim work. The shipped skill describes intent reuse, peer trust, decline and
failure, independent replies, and the unavailable long-suspension boundary.

Focused: 28 mailbox/CLI/receipt-signal tests passed in 8.957 seconds, no retry.
Comprehensive: 820 tests passed in 51.995 seconds, no retry. Initial default
unittest discovery selected zero tests and exited 5; corrected selection used
`PYTHONPATH=src python -m unittest discover -s tests -q`. This was a discovery
command error, not a passing full-suite result or a test failure retry.
CLI help and git diff --check passed.

Installed isolated Python 3.12 fixture built into
/tmp/codex-wake-p63-receipt-venv, with no global package/service change.
Mailbox smoke with scheduler and operations passed: historical acceptance and
completion waits returned original receipt IDs; 24 read connections closed;
children zero before/after; zero runtime effect methods and scheduler dispatches;
temporary bus and roots removed. The existing complete fixture includes a
second cancellable request, so requests=2 is provider-free fixture evidence,
not the one-request maximum real-agent packet. All actors and roots synthetic.

This does not prove actual named-agent request/reply, automatic notification,
daemon receipt restore, long suspension, resource soak, service or release.
Memory disposition unavailable; no healthy authorized Graphiti write path.
