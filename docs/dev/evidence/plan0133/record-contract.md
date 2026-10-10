# Native network time record contract

New native CLI registrations use schema5, retaining the schema4 native target,
exact identity and submission evidence, with the existing network-first policy
and arming observation. Schema4 stays guest-timed; schema1 promotion remains
schema4 and never opts an old record into a new time domain. No live migration.
Readers supporting only1–4 hold schema5. New readers reject malformed policy
or observation metadata without dispatch. Relative due and file TTL use rounded-up
upper-bound creation time; absolute due and expiry preserve fractional precision.
Due, retry and expiry require fresh trustworthy lower-bound evidence. Deadline
intervals crossing expiry hold submission. Reconciliation observes existing native
intent without resending, including while time is unavailable. Cancellation
records unknown time without obtaining guest UTC for a network-domain event.
The arming slice initially held schema5 until ticket0135 enabled bounded evaluation;
source qualification now includes that evaluation. Installed activation remains0136.
