# #602 acceptance

Base e8c79a79; implementation ee592e5d. Public ControllerTabs and generated CLI
family register/list/show/bind now persist acyclic lineage and exact client/environment
bindings. Root is derived; metadata confers no account/input authority. Replaced
pane births and conflicting bot/client ownership are held. Missing tabs retain identity.

RED: test_bot_families initially unsupported_operation (two public-interface cases).
GREEN: PYTHONPATH=src:tests uv run --no-project --with websockets --with msgspec
--with jsonschema --with dbus-next python -m unittest test_bot_families
test_tab_contract test_tab_destination_scope test_tab_profile_create -q
17PASS11.919s. Real owned tmux and CLI cover binding/restart/client distinction.
Existing destination/profile grant guard extended to family.open: red reached
forbidden effect, then green8checks after preserving account grant selection.
Pinned Ruff undefined-name selection PASS. No live bot/terminal/provider effects.
Display480756dd integrated e86a7aa6; worker73affectedPASS and3binding-loss/displayPASS;
coordinator registry/display6PASS. Presentation checkout released after exact
remote worker480756dd custody and clean-state verification. No broad review yet.
