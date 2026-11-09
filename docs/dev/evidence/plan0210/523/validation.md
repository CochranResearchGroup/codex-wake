# Ticket523 rendering qualification

Base: e274810. API checkpoint: 0dea949. No production namespace, desktop-wide
capture, provider/model process, service or native executable changed.

## Public behavior

Projection supports full256-colour, basic named-colour and plain default-colour
modes. All carry type/state text and native current-window brackets plus
bold/underline where supported. Expiry respects the selected fallback, retaining
STALE text and selection. ASCII metadata is the default; optional Unicode counts
combining characters conservatively and bounds CJK text to display cells. Native
manual tab names continue through #W and are never renamed.

Capability descriptions distinguish known protocol families, observed binary
identity and per-client rendering acceptance. An unobserved backend name is not
runtime qualification; unknown backends are unsupported and colour depth remains
unknown absent client evidence. A pinned psmux hash identifies only the qualified
native protocol, not all client colour/glyph behavior.

## TDD and focused validation

- `PYTHONPATH=src .../.venv/bin/python -m unittest discover -s tests -p test_tab_format_rendering.py -q`
  RED1: plain mode retained yellow background. GREEN1: plain default colours and
  selected brackets passed.
- Native matrix RED: installed psmux's renderer consumed literal metadata
  `#[bg=red]` after expansion even when the input hash was doubled. The actual
  console omitted that text. Tmux's attached renderer safely kept the literal.
- Focused regression RED: psmux projection lacked a separated literal `# [`.
  GREEN: psmux metadata displays `# [bg=red]`, breaking the renderer's second-stage
  style introducer before cell bounding and escaping. Tmux retains exact text.
- Batch-capacity regression RED: an82KiB batch reached the bridge. GREEN: encoded
  frame preflight raises capacity before any native effect. The maximum256items
  remains additionally limited by the65536-byte frame; no arbitrary-size claim.
- Python3.11 rendering tests passed. Final focused3.12 formatting and native
  psmux regressions are recorded with the final receipt.

## Installed rendering acceptance

`WSL_INTEROP=/run/WSL/1_interop PYTHONPATH=src .../.venv/bin/python scripts/tab_format_render_acceptance523.py --windows-python /mnt/c/Users/ecoch/AppData/Local/codex-wake-test/controller405-20261030/venv/Scripts/python.exe --output /tmp/p523-final-matrix-green.json`

Byobu6.11/tmux3.4: an owned attached140x30PTY exercised full/basic/plain modes,
native selected/unselected cues, literal hashes/commas/braces/style-looking tags
and shell-looking metadata, CJK cells and ASCII fallback. Option/format expansion
and actual terminal ANSI output are separate retained checks; no claim of human
colour perception or pixel screenshot validation.

Installed psmux SHA bbe825a30f7cddc91b043084049143a381aba5f7e9e36e4d0bb587e296d262ca:
finite native option/style readback and direct format expansion cover each mode.
An owned dedicated Windows console wrapper opens CONIN$/CONOUT$ explicitly. It
attaches only the disposable namespace and reads only that console buffer before
and after native tab selection. Exact child PID/birth and wrapper PID bind
cleanup; client termination is waited and wrapper reaped. Original formatting
and session values restore exactly and the test namespace is absent afterward.

Native UTF8 correction: psmux outputs UTF8 while Windows Python's default locale
can be cp1252. Initial CJK readback was mojibake. Explicit UTF8 decoding in the
native bridge preserves the original Unicode name; subsequent real native
format/name checks prove the correction.

## Preserved diagnosis boundaries

ConPTY attempts emitted16setup bytes `ESC[?9001h ESC[?1004h`, not a status bar.
A bounded resize/focus probe showed exit0 and no registered native client. The
version-pinned upstream non-TTY gate explains why inherited WSL pipe handles
printed the version rather than attaching. The dedicated native-console path
qualified actual rendering; no binary upgrade or production workaround occurred.

Pinned source: https://github.com/psmux/psmux/blob/20aa1d7/src/main.rs#L5826-L5837 .
This directed diagnosis; native console evidence establishes actual behavior.
`#{E:window-status-format}` also returned a default formatting path on this build;
direct native expressions and actual UI were used instead. That lookup's result
was never promoted to a claim that per-window UI rendering was unsupported.

Native inline-style failure and ConPTY receipts are preserved, not erased by the
passing final run. Final matrix retries follow the material sanitization fix.
No hosted CI was run or paid capacity requested. Memory disposition: forbidden;
worker scope does not authorize memory writes.

## Final result

Final native matrix passed full/basic/plain on both backends, including actual
attached-client rendering. Windows console background attribute sets were0/3/6
for full/basic and0for plain. Both selections were observed in every mode; the
literal style-looking and shell-looking metadata stayed visible after the fix.
Final receipt records exact source hashes, installed psmux version/hash and
post-cleanup known PID/birth readback. Exact-owned server/client/wrapper are absent
or exited, and the unique console title is absent. Individual pane/conhost PID
births were not retained; the receipt names that visibility limit rather than
asserting a full host process census. Pane/name continuity before cleanup and
namespace absence after supported shutdown were verified.

Final focused Python3.12:16formatting tests and7native psmux regressions passed.
Python3.11:5rendering tests passed. These are focused checks, not a full-suite
claim. No broad review was run by this worker.
