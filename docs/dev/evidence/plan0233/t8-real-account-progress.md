# P233 T8 live qualification progress — incomplete

The operator approved one bounded live packet: twelve Grok responses, two OpenAI
worker responses, sixteen local tool calls and fifteen minutes. Qualified start
was 2026-11-15T19:45:25Z; the original deadline remains 20:00:25Z. This is manual
monitoring, not independently enforced external supervision. No allowance reset.

Official Grok 1.0.77 device sign-in succeeded. The pinned official model listing
completed successfully and advertised grok-4.7 as default. Authentication presence
and catalog access do not qualify inference or coding capabilities. No tokens,
verification material, credential files or private working history are copied
into this receipt. Native package hashes were rechecked against all six files.

The first standalone native probe failed before inference because Wake rejected
the official native auth lock's 0644 mode. The credential file remains 0600.
The existing public CLI/private-bearer regression was extended with that actual
lock mode and failed before the fix. Wake now accepts other-user read permission
on the nonsecret synchronization file while retaining owner, regular-file,
no-symlink, inode and flock checks; other-user write permission still fails.
The lock is not chmodded or replaced. Focused auth checks: twelve PASS in 2.123s;
existing catalog check: one PASS in 3.326s; diff check PASS. A private, no-refresh
real native bearer read passed without exposing the value.

A second fresh native probe then failed with `inference request outcome unknown;
automatic replay withheld`. No assistant answer or local coding tool execution
was observed. The resulting tree is held, aggregate usage remains unknown, and
no replay or further paid work is authorized on that tree. Bootstrap auth-command
invocations are not response counts: twelve failed emissions in the first probe
are retained separately, and successful emissions in the second are also retained.
No OpenAI worker inference was dispatched. Current diagnostics suppress HTTP
status for generic failures; a bounded local diagnostic regression is in progress
before any decision about another provider request. Do not infer an HTTP status
or provider outcome from this generic message.

Native source/package remains at the prior qualified revision until that pending
diagnostic change is validated. The Wake auth fix changes runtime code, so the
previous wheel's auth acceptance must be rerun against a newly identified wheel;
unaffected UID1017 native package gates remain historical evidence, not proof of
a changed native package. T8 #639 and parent #628 remain OPEN. Seven children are
closed; broad review and post-review remediation counters remain zero. No working
profile installation, restart, deployment, provider logout or automatic login retry.

Private execution receipts are under the existing p233-t8 state directory;
raw synthetic histories and process/job identifiers remain workstation-local.
