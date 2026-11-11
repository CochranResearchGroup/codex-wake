# Quiet publication cost

Public monitor publication now keeps unchanged fullsnapshots for atmost10seconds
and never longer than half configuredstale_after; changed projection/evidence
is still published immediately. The small owner heartbeat remains1second.
The20second default freshness window and dynamiccue expiry are unchanged.

Public regression red: unchanged frame published at6seconds. Green requires no
write at6 and publication at11 after previous changed frame at1. Another existing
metadata-materialization fixture expected the old5second pulse; initial green
failures are retained and that heartbeat boundary moved6→11. The real owner test
withstale_after2 still requires fresh bounded publication at1second.

Only physical JSON key sorting was removed from monitor state writes. Digests and
protocol output ordering are unaffected. Actual synthetic469346byte snapshot,
5samples×100encodes with Python3.12: sortedmedianCPU0.30709s, unsorted0.22631s
(73.69%cost). JSONdecoded values equal. This microbenchmark is not acceptance.

Focused commands: PYTHONPATH=src /tmp/wake216-py{311,312}/bin/python -m unittest
discover -s tests -p test_tab_monitor_publication.py . Final results recorded in
green311.log andgreen312.log; all4tests pass perinterpreter.
