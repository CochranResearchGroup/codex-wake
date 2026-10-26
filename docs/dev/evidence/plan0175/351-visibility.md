# #351 visibility acceptance

Source: feat/transparent-governor, baseline ce1ad93; fixture native server SHA256 `86fad00e38f0c26a5c8d2eb2dbe34536c74655fb2fb45b4efc5d94e97e683b1f`, stock frontend 0.164.0.

Public red: `PYTHONPATH=src:tests <repo-venv>/bin/python -m unittest test_governor_visibility -q` failed because enrollment created no activation notice and show omitted stop presentation status. Green: same module plus test_goal_notices/test_goal_engagement, 13 PASS (2.806s). A 94-test goal-suite run had one old assertion expecting only a stop; updated to require activation and stop, and its focused rerun passes.

Native command: `PYTHONPATH=src <repo-venv>/bin/python scripts/goal_notice_native_acceptance.py --app-server <pinned-native-server> --frontend <stock-0.164.0> --output /tmp/governor351-native-qualified`.

PASS: generated activation and stop rendered in the actual stock TUI; model context retained; no inference for notices; explicit shell-tool turn interrupted; reconnect rendered the retained notice once; peer unchanged; lost append acknowledgement reconciled once. Provider turns: 0. Owned process census after cleanup: empty. This qualifies the pinned fixture server, not arbitrary installed hosts or provider inference.

Preserved first failures: /tmp/351-red.log (missing activation/status); /tmp/governor351-native-debug.log (native 768-byte notice ceiling); /tmp/governor351-native-bounded.log (tmux last-session exit race); /tmp/governor351-native-final.log (orphan plugin-fetch cleanup). Renderer compacted; owned tmux server retained through reconnect; previously censused exact process identities retired at cleanup. Terminal qualified receipt: /tmp/governor351-native-qualified/receipt.json.

Model-context availability, UI rendering observed by this acceptance, and a human reading the notice remain separate facts. Journal proof remains `ui: unverified`; the TUI capture is the separate rendering evidence. No production configuration, watcher mask, allocation or session was changed.
