# HF16 source acceptance

Base: 012f173. Branch: feat/337-tab-ordering. Owner: HF16 worker.

Seam: public tab_organization_commands.execute and parser/run adapter; actual
private tmux 3.4 server with /dev/null config; real shell process generations;
host-injected qualified provider observation metadata. Verified operator CLI uses
a real temporary BusStore-issued operator capability. No operator socket touched.

Focused unittest command:
`PYTHONPATH=src python -m unittest discover -s tests -p test_tab_organization.py -v`

Red: initial import failed because public adapter did not exist; subsequent first
real-tmux apply failed postcondition (tmux focus changed despite swap-window -d).
Green: same public-seam test passes after journaling implementation and queued
original-focus restoration. Permission-revision regression separately failed
because original plan applied after policy update, then passed after revision
was added to complete snapshot fingerprint. No pytest dependency added.

Nine focused tests prove real preview/apply/conditional undo, stable pane IDs and
process boot/start identities, unchanged route bytes, stale refusal, newer-focus
undo refusal, lost-response uncertainty and no replayed swap, pins, true common-dir
worktree identity, mixed splits verified operator CLI capability denial, mandatory permission denial, invalid budget refusal and offline journal inspection.

Limits: shared CLI/MCP registration is integration-owned. Native protocol fixture
coverage of the default observer is not claimed here; provider evidence injected
at the host seam is labeled. Existing RuntimeObserver/RuntimeStateObserver tests
remain their owners' evidence. No production/provider acceptance, canary, install,
GitHub action or memory write occurred. Human-command race remains documented.

Memory disposition: forbidden; worker packet explicitly prohibits memory writes.
