# Plan0162 — Released installed acceptance

Source: PR263/88f008d plus corrective PR265/1ee7229, each merged to canonical main.
Stable release:v0.15.1. Prefix:/home/ecochran76/.local/share/codex-wake/releases/0.15.1-1ee7229.
Public wheel/sdist readback hashes: public-release-0151.json.

- Hosted Python3.11/3.12 release gates PASS, including1,231 unit tests, packaging,
  compatibility and installed smoke. Exact source evidence: patch-ci-qualified.json.
- Five global commands point at the new prefix;99 Python files match main bytes.
  Both installed skill roots match4 canonical files. Prior0.14.0 remains installed;
  backups under ~/.local/share/codex-wake/deploy-backups/0.15.1-1ee7229.
- Global fresh MCP advertises19 tools. Installed private-bus smoke PASS with
  request/read/claim/completion/reply and capability denials,0 native turns.
- Owned real Codex/Tmux startup PASS: tab-only, fresh and exact saved resume,
  zero model turns. Raw proof observer also saw its calling verification shell;
  separate later /proc Codex-home census found0 owned residue and0 denied reads.
  Ten active Wake services keep the same PIDs/states, no service restarts.
- Actual read-only global checks of `tab 18`, `18:policies`, `poicys` return the
  same current no-live-Codex condition. New tools perform matching internally.
-0.15.0 was activated, then rolled back to0.14.0 after an owned startup race.
  Unknown native binding now remains starting; a different known thread still
  returns target_changed. Public-seam regression observed red then36 checks green.
  Failed proofs, rollback receipt and superseded prerelease/tag retained.

Boundaries: existing TUI MCP schemas require a normal resource/session refresh.
Host launch profiles/caller grants and mailbox enrollment remain explicit; deploy
adds no automatic grants. Production-peer notifications or model-compliance are
not claimed by zero-turn lifecycle and provider-fixture mail acceptance. Existing
transport behavior was retained. No global daemon/TUI restart or incident replay.

Repository custody: parent lifecycle closeout PR264 retained. Original stack tip
b5ce1ea is archived remotely; feature/patch refs retained. Closeout documentation
is a separate PR on canonical main; then fast-forward the root and remove only
the clean temporary docs worktree after fresh zero-CWD-owner readback.
