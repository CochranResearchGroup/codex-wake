# Unattended native submission | 2026-10-09

Verdict: **PASS on installed Codex 0.162.1**, for an idle, live, independently attached TUI recipient on the shared local daemon.

An isolated initiating agent A registered a user-systemd timer, then completed its turn. Afterward a plain Python process ran the installed `codex queue --thread EXACT_ID --message TEXT`. The process removed CODEX_THREAD_ID, TMUX and TMUX_PANE; it neither called an MCP tool nor injected terminal input. B executed the queued prompt and returned `UNATTENDED_NATIVE_RECEIVED_20261009`, visible in B's original pane.

## Evidence

- A: `01a1227e-a0a7-7523-aafe-b80702aa56d5`; arming turn completed at 1791580188.
- B: `01a1227e-a041-7b72-9c36-18349e7dd22c`; recipient turn `01a12280-80fc-7a71-8816-3a0825021726` started at 1791580209 and completed at 1791580211.
- Timer process PID 13458 started at 1791580206.917427; CLI exit 0, with queue ID `01a12280-80ef-7772-a00a-c68bd32ecbba`.
- `unattended-A.json`, `unattended-B.json`, `unattended-queue.json`, and `unattended-B-pane.txt` bind the observed ordering and actual completion. They preserve only disposable experiment content.
- First attempt failed before submitting: systemd PATH omitted codex. `unattended-first-failure.txt` preserves the failure. The single retry used the installed absolute executable path and timer AccuracySec=1s.
- A transient wait response reported the newly created recipient turn as interrupted; the later read returned that same turn completed with its exact final token. A queue exit or one status snapshot alone is insufficient completion evidence.

## Reproduce

Start two disposable clients with `run.py start`; wait for their fresh IDs and READY tokens. Ask A to register:

```sh
systemd-run --user --unit=codex-native-unattended-prototype-FRESH \
  --on-active=20s --timer-property=AccuracySec=1s \
  /usr/bin/python3 "$PWD/scripts/prototype_native_sessions/unattended.py" \
  EXACT_B_THREAD /absolute/private/receipt.json
```

A must finish immediately after registration. Inspect the receipt, then use native thread readback to verify B's completed turn and its pane to verify visible synchronization. The script exits after queue submission, before B's response finishes. Stop the dedicated clients with `run.py stop`; archive only the disposable threads and stop only the named timer/service units. Historical IDs in these artifacts are archived and must not be reused.

## Product consequence

An unattended Wake scheduler has a concrete native CLI delivery candidate; it does not need the calling agent's TUI-hosted MCP tool to submit to this recipient class. This qualifies the first native-delivery gate, not a production adapter or a comprehensive replacement contract. The native queue API is a separate path from `codex_tui.send_message_to_thread`; their semantics must not be assumed identical.

Still unqualified: busy recipients, no attached TUI, daemon/client restart, uncertain submission reconciliation, native queue deduplication or expiry, legacy migration, cross-host transport, and other versions. These belong in the next bounded implementation/qualification plan. No production module or installed Wake service was changed.

Memory disposition: unavailable — no verified project Graphiti group; committed prototype evidence preserves this outcome.
