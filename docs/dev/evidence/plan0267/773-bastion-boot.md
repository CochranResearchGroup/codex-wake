# Native Bastion boot acceptance

The operator rebooted Bastion with the candidate from `ee7cfe6f`, native
Ubuntu PostgreSQL 16.15, stock Codex 0.172.0, and five isolated systemd
user units under a lingering user manager. The canary used deterministic
time bounds and a loopback model responder.

The first boot established startup before SSH. The retained wake stayed
pending until a private tmux anchor and a verified link to the real Codex
socket were configured. The original wake then delivered once. A second
operator reboot tested the corrected setup without intervention.

On the second boot, `39bc1397-cd70-411a-aa59-e93d73adb8b7`, all five units
started at 17:32:36 CST. PostgreSQL reported ready at 17:32:36.227.
Canary `wake_intent_e8ac6b8f0da04011bc1494b25a6ece84` completed at
17:32:37.052, before the first SSH authentication at 17:32:54. Wake
reconciled the retained journal and submitted once with the original due
time and expiry. PostgreSQL recorded one submitted attempt and the
original stock conversation contained one matching input and one
completed turn. The loopback responder observed one matching invocation.

The verifier exited zero. The five dedicated units, fixture processes,
listeners, and private data root were removed after evidence capture.
