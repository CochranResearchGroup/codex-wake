# Ticket546 rejected encoder dependency experiment

Benchmark-only experiment requested against source127b4dc7 (runtime same494), without production or dependency edits. Installed python-rapidjson1.26 using `pip install --only-binary=:all: python-rapidjson` into private codex-daemon-test UID1017 venv `/tmp/wake546-rapidjson-bench`, CPython3.12.3. No Rust/Cargo or source builds. Parent acceptance caps remain unchanged.

Read existing private synthetic360958B formatting state and469346B snapshot from `/tmp/wake547-results/62877702-private-state/`; no raw contents emitted. ABBA encoder ordering, each five repeats of100 encodes, timer`time.process_time`, stdlib compact unsorted allow_nan=False vs RapidJSON allow_nan=False/ensure_ascii=True/sort_keys=False/BM_NONE/IM_ONLY_LISTS/MM_ONLY_DICTS. Receipt `/tmp/wake547-results/rapidjson546-benchmark.json`.

Median CPU seconds per100: formatting stdlib .147595/.155148 vs rapidjson .216474/.140184; snapshot stdlib .288926/.282125 vs rapidjson .201752/.190818. Formatting shows no dependable benefit; snapshot improves roughly1.45x, below the requested2x justification. Sixty snapshot encodes imply only about.05 CPUseconds saved, below the requested.3 CPUseconds/60s. This is an estimate from a serialization microbenchmark, not a whole-owner acceptance result.

Strict nestedNaN/+Inf/-Inf/bytes/set rejection passed with selected options. Critical floats including negativezero,1e-300,1e300 and128-bit integer, Unicode, nested booleans/null, tmux newline/semicolon/backslash/literalquote semantic roundtrip passed. Serialized bytes differ in Unicode escape hexadecimal case; no canonical digest encoder replacement is qualified.

Decision: reject adding this dependency for the measured workload. No source, dependency, persisted state or production changes. Official parameter authority: https://python-rapidjson.readthedocs.io/en/latest/dumps.html (allow_nan=False, compactstring output, insertionorder and strict modes). No broad review or post-review remediation run. Primary owner retains full qualification and memory closeout.
