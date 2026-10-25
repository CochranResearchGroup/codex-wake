# #346 installed renewal acceptance

Source under test:5fc32c436b1744e8d3a32f7e6eb0b1dc1208189b.
Successor worker: /root/ticket346; branch test/346-renewal-installed-acceptance.
The acceptance script is `scripts/goal_limit_ux_acceptance.py`; its tested content
hash is1020459c8d2c09c5962f7b787d355ad35a1523e0b848a210d87d7ef12c15db0d.

## Installed boundary and result

An isolated wheel from the exact source was installed with MCP extras into:
`~/.local/state/codex-wake/goal-limit-ux/renewal-installed-20261025T044000Z/prefix`.
Its Python3.12 imported the installed package; all160package Python files matched
the source bytes. The actual stdio MCP catalog exposed82tools, including the
three renewal operations. No source PYTHONPATH was supplied to the CLI/MCP/watcher.

Command (from the worker checkout):

```sh
$PREFIX/bin/python scripts/goal_limit_ux_acceptance.py \
  --prefix "$PREFIX" --source-root "$SOURCE_ROOT" --output "$NEW_EVIDENCE_DIRECTORY"
```

The script refuses an existing output directory and mismatched installed source.
It uses the configured qualified clock, private fixture policy/accounting, a real
owned Unix websocket implementing the native protocol, the actual installed
independent watcher, subprocess CLI and native-metadata stdio MCP. The native
protocol and accounting history are injected, explicitly not stock Codex/frontend
or billing proof. No shared service or production policy was changed.

Final receipt: `renewal-installed-20261025T044000Z/final/receipt.json` under the
user-scoped state root above. Verdict PASS:

- An exhausted100-token window retained100spent while the model proposed150total
  and50remaining. Attempting application without an operator response was refused;
  the original ceiling stayed100.
- The actual `attention respond` operator CLI used its existing bus capability.
  The actual native-metadata MCP consumed that exact authenticated queue response
  and applied the extension, preserving usage and native identity.
- The approved resume remained pending until an independent watcher poll
  acknowledged the new enrollment revision. Retrying the same approved proposal
  then issued `thread/goal/set` with active status and verified native readback.
  Duplicate application returned the same result without another native effect.
- A separately explicit CLI reset applied a new window at0used/100lifetime,
  retained history and a new generation, and left the native goal paused.
- A separate allocation's scope, generation, limits, usage, deadline, time origin,
  enrollment revision, state, reason, stop latch, effects and checkpoint matched
  across the operations. Its native goal remained unchanged and received no
  mutating request. Ordinary fresh watcher observation fields were not treated as
  authority mutations.
- No turn/start or provider calls occurred. The owned watcher exited0. Fresh
  `final-process-census.json` found zero processes under the isolated install
  prefix; owned socket state was removed.

The first attempt failed before watcher start because a deeply nested evidence
path exceeded Unix socket path length. Its INCOMPLETE receipt is retained in
`attempt1/receipt.json`; this was a fixture location failure, not a product verdict.
The adapter was changed to use a short private temporary socket directory. Attempt2
passed; final re-execution strengthened peer-state comparisons and passed. The
final script and receipts retain those distinctions.

## Limits

This proves installed Wake CLI/MCP renewal and injected-native positive resume.
It does not prove a real frontend card, transcript notice or model context. The
#345 real native/frontend acceptance owns that distinct boundary. The source is
not merged, released or installed into the shared production prefix by this test.
Primary later changes that affect the exercised paths require matching-source
requalification. No broad code-review pass was run by this worker.

Memory disposition: forbidden; no memory write was requested.
