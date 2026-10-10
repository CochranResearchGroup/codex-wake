# Plan0138 installed preflight — failed sample and correction

Candidate d5f0524 / isolated0.11.0-d5f0524,94-test selection before added control:
actually93tests ran28.210s and failed5errors. Original log is private
~/.local/state/codex-wake/plan0138/installed-focused.log. No acceptance exchange
or original request had been admitted when this failure occurred.

The fixture patched the tmux wrapper before the saved-delivery module imported
its alias. Loading another test first left that alias unpatched. Corrected fixture
patches the saved transport's external tmux I/O seam directly, removing import-order
dependence. The leaked real subprocess also exposed a product gap: missing tmux
could stop the worker. It must not establish that the saved recipient has no tab.
One consolidated installed-preflight repair catches bounded SubprocessError and
holds runtime_unavailable. Public dispatcher red:17tests, one tmux error; green:
17PASS6.302s. No ambiguous external effect occurred and no request was replayed.

Separate setup CLI misuse passed thread: prefix to bind-tmux, which already adds
that prefix. It returned selection_error for thread:thread:UUID with zero binding
effect. The original private receipt is retained; continuation uses raw UUID for
binding/delegation and does not repeat configure or capability issuance.

Rebuild the corrected source into a new immutable prefix. The failed original
prefix and log remain untouched. Final installed focused controls and live
unattended exchange remain required; neither source green nor setup is acceptance.
