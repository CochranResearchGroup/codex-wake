# Retained migration qualification failures

- Initial full suite: eight classic CLI fixtures omitted the newly required
  explicit legacy choice. Fixture calls now select compatibility; no acceptance
  criteria were weakened. Log: private runtime0132-full-tests-first.log.
- Malformed schema4 expiry crashed the daemon. Red regression retained;
  classification now holds malformed native records before evaluation.
- Installed compatibility readback passed registration/refusal/cancel, then
  failed because the probe incorrectly supplied unsupported `show --json`.
  `show` emits JSON by default. Corrected documentation/probe uses `show`.
- First installed product smoke failed at its wheel-upgrade step because the
  uv-created acceptance venv had no pip module. This is harness infrastructure,
  not an upgrade verdict. Install pip in that private environment and rerun in
  a separate artifact directory; preserve the first sample and its stderr.
