# Ticket 546 stable projection qualification

Source base: `feat/observer-format-546`, root integration after ticket 543.
No production terminal or monitor configuration was changed.

## Result

- Static qualified type, palette and native name survive observation age.
- Dynamic traits independently honor `source_available=False`. Their retained
  values and redacted provenance remain in formatting inspection details.
- An observed dynamic trait with `source_available=True` survives quiet time;
  source epochs/binding qualification are provided by the shared observer.
- One existing managed session option, `@wake-format-clock`, now contains the
  publisher lease deadline. Native time is evaluated with `#{T:#{l:%s}}`;
  `#{T:%s}` alone was experimentally empty on stock tmux 3.4. A 30-second upper
  bound fails closed for a grossly future lease. No new backend option exists.
- Only generated dynamic cues and attention styling expire. Native names,
  qualified type and palette remain visible without STALE or blanket dimming.
  The lease makes publisher death safe without rewriting every window timestamp.
- Unchanged monitor projections issue no per-window reads/writes until a
  60-second custody audit. Changed projections always read current options before
  writing, preserving manual overrides and baseline custody. Explicit operations
  still check immediately. Shared lease updates remain separate from window
  writes, and unchanged windows do not trigger native redraw commands.
- Missing samples clear old cues before another window renews the shared lease.
  Static metadata is retained only while exact saved pane identity matches the
  current physical window. Replaced identities lose all old claims. An entirely
  unavailable workspace cannot renew its lease.
- Existing baseline rollback, reenable, explicit manual-style resume, native
  selection cues and presets remain covered by the existing public tests.

## Validation

Focused selection:
`PYTHONPATH=src /tmp/wake216-py311/bin/python -m unittest discover -s tests -p 'test_tab_format*.py' -q`
55 tests passed in 15.809 seconds.

The same selection on `/tmp/wake216-py312/bin/python` passed 55 tests in 16.572
seconds. Local Linux stock tmux 3.4 was used for native behavior tests. Hosted CI
was skipped under repository cost policy. This selection is not the complete
repository suite, the 100-tab workload, installed-package acceptance, or live-host
acceptance; those remain parent integration gates.

Red evidence: new public projection tests initially failed for the observed
quiet valid source becoming stale and loss of qualified build type; source-loss
and unknown-state expectations failed before implementation. Native lease test
then reproduced the empty native clock expression before the literal-format
correction. Old expiry tests were revised to the accepted P216 behavior rather
than retaining contradictory STALE/dimming requirements. A first wider run also
caught a resume branch using an uninitialized session readback; corrected before
both-version green. No failed test was relabeled a pass on retry.

Additional checks: undefined-name ruff selection for touched source and focused
formatting tests, plus `git diff --check`, passed. Raw terminal content, credentials
and production inventory were not retained. Private test servers and monitor
processes were cleaned up by their owned fixture contexts.

No tracker closure, merge, deployment or live formatting action was performed.
The primary owner owns the single substantive closeout memory disposition.
