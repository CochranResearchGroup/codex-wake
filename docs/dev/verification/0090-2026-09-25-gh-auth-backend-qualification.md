# GitHub CLI credential backend qualification

Date: 2026-09-25
Issue: #166
Plan: `docs/dev/plans/0094-2026-09-25-gh-auth-credential-backend.md`
State: ACCEPTED

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

PR #167 passed hosted Python 3.11 and 3.12 gates and squash-merged as
`8ae3a024845bcacb5bded502e323ff9e8635736b`. Its canonical main run
`36130577196` passed. The canonical source tree was built into wheel SHA-256
`26fe6d001e8fc1c071d8b6b9f10aac124b8d7ff0d5f382b531866915866de41a`.
The rollback wheel from the prior installed source `5aad4e0` has SHA-256
`7f2176cc079ddd1ddf26f057daa185f4d564de612cf9511e9e94703194ce309c`;
the prior installed `app_server.py`, `supervisor.py`, `monitor.py`, and
`service.py` hashes matched it before installation.

The supported `uv pip install --python ... --no-deps --reinstall` path replaced
the user-scoped tool with the canonical wheel. Five affected installed module
hashes matched that wheel. The installed CLI showed the `GH_CLI` default and
the installed credential resolver obtained a same-user `gh` token without
printing it. The user supervisor restarted once from PID `26291` to `22222`;
all four enrolled roots reported recent ready health and zero active wakes at
the pre-effect census. Both installed Codex Wake skill copies hash exactly
`3249a222506ab0e1d5d632dbb29e8997893dae25c207e42f30b0d34daaef6715`,
matching the canonical tracked skill.

The retained #141 hook `685366419` remains active with last response HTTP 200.
Its listener PID `751` and poller PID `80370` remain active and enabled on
their isolated runtime and explicit limited-token binding. The durable read
credential remains mode 0600. No provider administration write, webhook
redelivery, live dispatch, or retained binding migration occurred in this
rollout. Multi-repository live qualification is deferred to a separately
bounded operation.
