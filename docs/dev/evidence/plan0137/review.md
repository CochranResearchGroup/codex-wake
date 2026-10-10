# Plan0137 primary review

Frozen baseline2a8a945; contract Plan0137. Serial primary Standards and Spec
review; no independent evaluator claimed. Bounded diagnostic projection changes
only queue failure retention; transport, acceptance matching and no-resend remain.

## Standards

No accepted blockers. Arbitrary subprocess output, argv and exception messages
are withheld, including unknown errors; only fixed allowlisted hints and bounded
metadata persist. Processing inspects at most4096 units per output; receipt less
than1024characters in rejection/timeout/unknown/OS-error controls. Optional native
metadata is compatible with existing readers. No new dependencies or schema.

## Spec

No accepted blockers. Real rejected queue reproduces dropped stderr/returncode;
retention patch fixes symptom. No causal reconstruction of original LitScout wake
is claimed. Timeout partial bytes, unknown output and OS errors qualify. Subsequent
read-only reconciliation retains diagnostic, original intent and attempts1.
First counter fixture also counted daemon discovery; guard now counts onlyqueue.
Original failed fixture sample preserved; no change to retry policy.

25 focused native tests PASS1.042s; injector regressions logged separately.
Installed wheel proof and release activation remain pending at this review point.
