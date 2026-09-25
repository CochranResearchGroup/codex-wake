# GitHub CLI credential backend qualification

Date: 2026-09-25
Issue: #166
Plan: `docs/dev/plans/0094-2026-09-25-gh-auth-credential-backend.md`
State: LOCAL_ACCEPTED_HOSTED_AND_INSTALL_PENDING

The provider free credential tests pass with a fixed `gh auth token
--hostname github.com` command, sanitized failures, explicit environment
reference fallback, and the Homebrew service-path fallback. New source and
binding CLI configurations default to `GH_CLI`. An HMAC-only webhook listener
environment is accepted for that source. Existing explicit references remain
valid and the durable configuration schema is unchanged.

Focused validation passed 63 Python tests. Comprehensive validation passed
694 Python tests. The OpenClaw plugin suite passed 12 tests. Python compilation,
diff hygiene, active planning, and goal governance audits passed. An isolated
wheel was built and its installed CLI displayed the `GH_CLI` default. A
service-like environment with systemd's path and the user's home successfully
resolved the configured `gh` credential without printing it.

The retained #141 hook and service still run from their isolated 0.5.2 wheel
and their existing limited-token reference. This qualification did not update
the live binding, invoke a webhook administration write, redeliver a payload,
or dispatch a wake. Hosted gates, canonical merge, user-tool install, and
installed readback are recorded in the issue closeout after they occur.
