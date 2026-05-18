# Codex Wake

Codex Wake is a local wake spooler for TUI-bound Codex agents.

The first implementation target is a small `codex-wake` CLI that writes declarative wake records under `.codex/wake/`. Later slices add the daemon, tmux injector, and Codex hook ack flow described in [docs/dev/0001-wake-spooler-design.md](docs/dev/0001-wake-spooler-design.md).

## Development

Run the focused test suite:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
```

Run the CLI from source:

```bash
PYTHONPATH=src python -m codex_wake.cli --help
```

Create an app-server-targeted wake instead of a tmux-targeted wake:

```bash
PYTHONPATH=src python -m codex_wake.cli after --app-server-thread-id thread_abc 45m -- "Resume the scheduled task."
```

Archive terminal wake records:

```bash
PYTHONPATH=src python -m codex_wake.cli archive --all-terminal
```

Run one daemon polling pass from source:

```bash
PYTHONPATH=src python -m codex_wake.daemon --once
```
