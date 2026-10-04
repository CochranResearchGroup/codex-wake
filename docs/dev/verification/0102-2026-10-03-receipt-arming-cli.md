# Receipt arming prerequisite evidence

Baseline: 75686bac66abd4be11cfbe865cb8918addfd0af5; Plan 0110 / issue #181.
Synthetic temporary buses only; no live enrollment, provider, service or dispatch.

## Feedback and qualification

Initial fresh CLI test: exit 2, arm-receipt absent. The initial absent-grant
assertion incorrectly expected no wake directory although fixture setup creates
it; corrected to assert no pending record. First implementation returned
READER_CAPABILITY_UNAVAILABLE. This correctly retained the active-reader gate.
Fixture advertises its live parent reader in isolated XDG state. Missing and
wrong-root advertisements remain refused. A once daemon overwrites health with
its own subsequently exited PID; re-advertise the live fixture reader before a
new arm rather than bypassing liveness. No runtime authentication was fabricated.

CLI repeats preserve wake identity; changed receipt condition conflicts under
the same key. Absolute expiry remains stable across retries. Fresh daemon
preserves pending state before reply; synthetic committed reply yields exactly
one durable no-dispatch firing across restart. Revoked grant holds pending;
expired arm moves to expired. Mailbox event/receipt/envelope counts unchanged
by registration and observation; no bodies or capabilities in CLI output.

## Validation

Focused: PYTHONPATH=src python3 -m unittest tests.test_a2a_receipt_arming
tests.test_a2a_receipt_authority tests.test_a2a_cli tests.test_a2a_receipt_signals
-q: 25 tests, Python 3.12, 6.446s. Same selection Python 3.11 passed.
Comprehensive: PYTHONPATH=src python3 -m unittest discover -s tests -q:
834 tests, 42.093s, no retry; log /tmp/codex-wake-p63-arming-suite.log.
Compile/diff and active planning audit passed (20 accepted legacy findings).
Isolated wheel installed commands (PYTHONPATH=tests, no source path): four
tests, 2.190s; installed import under venv site-packages. FD 5 to 5; child
processes zero to zero. Wheel SHA256:
de6a9a09c47abbb8c049edb950c1a457e70ca0a9931053bf495cad6c1e26740a.

## Limits

Fixture reader advertisement is synthetic qualification, not installation or
a live actor identity. CLI arming is accepted; actual agent suspension/delivery
is not. Full Plan 0101 remains OPEN. Hosted gate/publication tracked separately.
Graphiti discovery skipped: current canonical sources and prior verified
checkpoint suffice. Memory write unavailable: no authorized repository group.
