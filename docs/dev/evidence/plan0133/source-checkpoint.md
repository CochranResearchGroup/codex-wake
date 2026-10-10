# Source checkpoint — Plan0133

Baseline ac6a575; execution branch feat/native-network-time. Tickets0134/0135
source behavior is implemented; acceptance is pending exact hosted gates before
advancing0136. Global installation/supervisor are still unchanged v0.9.0.

Observed regression loops: arming guest UTC, held schema evaluation, direct
firing uncertainty bypass, outage reconciliation, fractional expiry, malformed
operator collection. Red/green logs retained. Public CLI/scheduler tests use
injected bounded provider data; this is source proof, not installed real delivery.

Qualified comprehensive run: isolated Python3.12.13 with declared dbus-next0.2.3
and websockets17.2;993 tests PASS138.845s, no exclusions or retries. Earlier bare
interpreter run:993 tests116.037s,16 missing-websockets errors plus one stale
schema assertion; retained and superseded by environment-correct validation.
Schema-report write-version metadata changed during the comprehensive run and
is separately covered by final-schema-focused.log (11 tests PASS); exact hosted
head will freeze all files. Reader-focused28 tests PASS; affected55 tests PASS.
Compileall and whitespace checks pass. Installed v0.9 reader holds schema5.
Read-only actual time acquisition accepted Cloudflare/NIST/Alastyr consensus;
no new provider, authentication guarantee, clock adjustment or service effect.

Review is primary Standards/Spec, source-only. Installed qualification, real
unattended after/at, owned worker restart and rollback remain0136. P63 and paused
APP-PERSIST are separate. Do not migrate existing live schema4 records, replace
live imported package files, restart unrelated workers, or replay retained
uncertain controls.

Next: inspect exact PR head hosted gates, repair only observed failures, accept
0134/0135 source when gates pass, then qualify an immutable installed candidate
for0136. Preserve root's unrelated protocol test. No Plan0127 goal restarted.
