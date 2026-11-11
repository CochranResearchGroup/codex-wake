# Source identity remediation — single post-review TDD pass1

Review source: frozen head afd0061f. Accepted Spec finding: basename/thread
matching could replace a disconnected source with another account's feed.

Behavioral test: `tests/test_tab_observer_identity.py` uses stock disposable tmux
and two real Unix native protocol fixtures. Distinct homes share basename `home`
and thread ID `shared-thread`, with independently expected idle/running states.
The test disconnects A while its server process survives, then triggers B's real
metadata rebaseline inside the retained observation's cache lifetime. B must not
make A's source available or supply running activity. No provider/model requests.

Red, before product changes (both commands exit 1):

```
PYTHONPATH=src /tmp/wake216-py311/bin/python -m unittest discover -s tests -p test_tab_observer_identity.py
PYTHONPATH=src /tmp/wake216-py312/bin/python -m unittest discover -s tests -p test_tab_observer_identity.py
```

Both failed at `assertFalse(pane['traits']['activity']['source_available'])`:
`AssertionError: True is not false`. A first exploratory assertion also exposed
initial ambiguity (A's exact endpoint was None while both feeds were present).
The retained red specifically exercises disconnected-A substitution.
An initial bare Python invocation could not import websockets; it is not a
behavioral result. Existing dependency-complete environments above were reused.

Repair: retain the qualified metadata endpoint, full native home, peer process
birth and source epoch in each native binding. Inventory projects passive state
only when all these fields and the thread match. Missing legacy source fields
fail closed. Reconnect epochs cannot reuse the former binding's event authority;
existing metadata/process reconciliation must create a matching binding first.
Existing non-native sample behavior remains unchanged.

Green after repair and strengthened initial exact-source assertions:

```
PYTHONPATH=src /tmp/wake216-py311/bin/python -m unittest discover -s tests -p 'test_tab_observer*.py'
PYTHONPATH=src /tmp/wake216-py312/bin/python -m unittest discover -s tests -p 'test_tab_observer*.py'
PYTHONPATH=src /tmp/wake216-py311/bin/python -m unittest discover -s tests -p 'test_tab_traits.py'
PYTHONPATH=src /tmp/wake216-py312/bin/python -m unittest discover -s tests -p 'test_tab_traits.py'
```

PASS: 6 observer tests on each interpreter (3.060s / 2.553s); 6 traits tests on
each interpreter (0.215s / 0.210s). The focused identity test also passed alone on
both interpreters before the broader selections. Root concurrently remediated
cycle-deadline propagation and invalidation; the shared observer file integration
commit includes those changes, with their separate root-owned TDD receipt.

These are local source checks. Hosted CI was skipped under the cost policy.
No wheel build, installed acceptance, resource gate or new broad review was run
by this worker. Prior installed receipts remain tied to their prior source;
the integrated candidate needs the separately owned installed qualification.
Live no-transition and shared-kernel limitations remain unchanged.
Memory disposition: forbidden — task prohibits memory writes.
