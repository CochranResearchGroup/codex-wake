# Ticket519 validation

Delivery target: integration branch, not production installation. Native psmux
SHA bbe825a30f7cddc91b043084049143a381aba5f7e9e36e4d0bb587e296d262ca.

## Focused TDD

- `PYTHONPATH=src .../.venv/bin/python -m unittest discover -s tests -p test_tab_psmux_formatting.py -q`
  - RED1: missing transport.formatting, one error.
  - GREEN1: typed transport test passed.
  - RED2: unsupported finite native formatting action, one error.
  - GREEN2: local-vs-effective option baseline behavior passed.
- `PYTHONPATH=src .../.venv/bin/python -m unittest discover -s tests -p 'test_tab_psmux*.py' -q`
  - Six focused tests passed, including invalid batch preflight before effects.

## Native runtime

`WSL_INTEROP=/run/WSL/1_interop PYTHONPATH=src .../.venv/bin/python scripts/tab_format_psmux_acceptance519.py --state /tmp/p519-native-run3 --windows-python /mnt/c/Users/ecoch/AppData/Local/codex-wake-test/controller405-20261030/venv/Scripts/python.exe --output /tmp/p519-native3.json`

Passed nine native/public checks in32.614s. Receipt identifies actual standalone
bridge hash, namespace, process/birth, source-exact WSL CLI and MCP, actual
PowerShell CLI rollback and native bridge read, inherited-vs-local restoration,
repeat re-enable, finite batch, clock/session option restoration and final
namespace absence. No provider/model call or production namespace mutation.

The installed psmux differs from tmux: single named window-option reads return
effective inherited values even without `-A`. Full `show-options -w` lists local
built-in overrides and is used for explicitness. Parent global values are read
independently. User options are session-scoped in this installed binary; the
expiry clock therefore belongs to the managed session baseline.

## Preserved first failure and recovery

First attempt failed with WSL `UtilAcceptVsock ... accept4 failed110` when native
Python opened the bridge via `\\wsl.localhost` UNC. Its cleanup attempt also
failed through the same path. No blind retry of the namespace creation occurred.
Exact owned namespace wake519-104995773b48 was stopped with a bounded native
Python `-c` call invoking only `psmux -L wake519-104995773b48 kill-server`: exit0,
empty stdout/stderr. Native acceptance was then changed to copy the standalone
bridge/helper into a unique Windows LOCALAPPDATA test directory, avoiding UNC.
Run2 and run3 passed and cleaned their exact namespaces and owned helper dirs.
No WSL service or production process was restarted.

## Remaining qualification boundaries

This proves installed native psmux protocol and source-exact public controller
behavior. Pixel rendering, selected/unselected colour fidelity, label width and
final installed-package HTTP/remote client qualification remain tickets523/524.
Hosted CI was not run; no paid capacity was requested.
