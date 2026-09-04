# Product Smoke Matrix

This matrix is the repeatable validation surface for productized
`codex-wake` releases. It separates safe installed-surface checks from live
wake delivery checks so operators do not confuse predicate evaluation with
resume delivery.

## Safe Installed-Surface Smoke

Run this against an installed `codex-wake` binary, not `PYTHONPATH=src`:

```bash
python scripts/product_smoke.py --json
```

The script writes artifacts under `.codex/wake/smoke/<timestamp>/` by default.
It verifies:

- `codex-wake --version`
- `codex-wake schema --json`
- `codex-wake product-readiness --json`
- `codex-waked --once --no-dispatch`
- `codex-wake monitor check --json`
- `codex-wake supervisor run --once --no-dispatch --json`

By default, the smoke isolates `XDG_CONFIG_HOME` and `XDG_STATE_HOME` for the
safe surface checks. Use `--use-user-state` when the smoke is intended to
inspect the real workstation install.

Use `--expect-monitor-ready` only when the selected wake root is expected to be
owned by an active repo service or persistent supervisor loop.

## Public-Tag Install Smoke

To validate a public GitHub tag without mutating the user-scoped `uv tool`
install, install the tag into a temporary virtual environment:

```bash
python scripts/product_smoke.py --public-tag v0.5.1 --json
```

This covers package installability from GitHub, CLI version reporting, schema
reporting, monitor-check execution, and supervisor `run --once --no-dispatch`.
The release closeout should still include the final user-scoped install command:

```bash
uv tool install --force --reinstall git+https://github.com/CochranResearchGroup/codex-wake.git@v0.5.1
```

## Live Codex App-Server Smoke

Live Codex delivery requires a real resumable thread id and a monitored wake
root:

```bash
python scripts/product_smoke.py \
  --wake-root .codex/wake \
  --use-user-state \
  --expect-monitor-ready \
  --live-codex-thread-id <thread-id> \
  --json
```

The harness registers a short app-server wake with a unique marker, waits for
the wake record to reach a terminal status, and records the final wake JSON in
the artifact directory. The release evidence must include the wake id and the
operator-visible turn or transcript readback that contains the marker.

## Live OpenClaw Gateway Smoke

Live OpenClaw delivery requires a real agent id, session key, Gateway auth, and
a monitored wake root:

```bash
python scripts/product_smoke.py \
  --wake-root .codex/wake \
  --use-user-state \
  --expect-monitor-ready \
  --live-openclaw-agent main \
  --live-openclaw-session-key <session-key> \
  --live-openclaw-workspace polycy \
  --live-openclaw-channel <channel-id> \
  --live-openclaw-deliver \
  --json
```

The harness records the created wake id, unique marker, and final wake JSON.
The release evidence must include Slack, transcript, Gateway, or equivalent
readback proving the marker was delivered through the intended session.

## Tmux Smoke Boundary

Tmux dispatch is manual/operator-visible unless the operator intentionally runs
the smoke from the target pane and captures visibility evidence. A tmux smoke
must record:

- `TMUX_PANE` and tmux socket source for the wake record
- the wake id and final wake status
- `visibility_result` or direct pane evidence showing the prompt landed in the
  expected Codex pane

Without that evidence, tmux remains `manual_only` in product-readiness and
release closeout.

## CI Boundary

CI should run source tests, package build, installed-wheel smoke, plugin tests,
and static plugin checks. CI should not run live Codex app-server, OpenClaw, or
tmux delivery checks because those require local sessions and credentials.
