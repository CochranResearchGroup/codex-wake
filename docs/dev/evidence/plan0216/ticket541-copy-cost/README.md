# Observation-record copy seam

Controlled100window synthetic process-metadata benchmark through public
ObservationCache.observe. Process/identity probes are explicit external boundary
fixtures, not realprovider data. ABBA order,60frames/sample, two samples/variant;
CPUtime measured separately fromwalltime. Every frame mutates returnednested
traits and confirms next publicread remainsuncorrupted.

Only complete observation records switch from Python deepcopy storage to
JSONencoding/freshCdecoding. The processdictcache stays unchanged, avoiding the
prior combinedcache experiment's double-encoding cost.

Cached-read CPU ratio candidate/baseline0.348; forcedrefresh0.486. Results are
microbenchmarks, not actualinstalledmonitor acceptance or hardgate passes.
Benchmark baseline source e5beb4c7. Default recorddata already follows the shared
JSON transport contract; outer (observations,session_rows) tuple is retained.

Commands: PYTHONPATH=src /tmp/wake216-py312/bin/python
docs/dev/evidence/plan0216/ticket541-copy-cost/benchmark.py (explicit-check
refresh; documented cached-read variant).
Receipts preserve raw four-sampleCPU/wall measurements. No service/provider/live
configuration changed. Parent #547 must rerun exact installed package metrics.
