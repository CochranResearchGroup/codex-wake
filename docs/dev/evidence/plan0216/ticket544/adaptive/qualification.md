# Qualified idle fallback and targeted dirty panes

Dependencies (already integrated by root): cache3b050986, dirty test60ac5e38,
preserve-dirty cache fence c287ef32. This packet does not edit those cache files.
Root should cherry-pick only this packet's final implementation commit.

The retained observer now selects30second metadata fallback only when every pane
has an exact native binding, observed idle activity, a continuous available native
source and available tmux presentation metadata. Running/waiting, recent dirty,
unknown, unavailable and empty observations retain a maximum5second fallback.
Native and tmux events still poll at the existing default one-second tick and
project immediately; no activity/source-loss event waits for the slower fallback.
This qualifies idle backend metadata, not a claim of TUI responsiveness.

Known native status updates mark only the matching owned workspace/pane dirty.
Same-epoch actual window metadata changes mark live panes in the changed window.
Initial baselines and equivalent periodic native metadata baselines do not create
an everlasting dirty window. The cache's bounded30second recent-change context
keeps post-turn idle panes eligible for five-second visible-error checks. Same
source metadata refresh preserves other panes' recent context; a source/epoch gap
retains the cache's default invalidation behavior. Health's independent60second
exact-client cadence is unchanged.

Passive tmux and finite tmux snapshots now include pane_current_command, and the
passive subscription watches it. It is only a changed-metadata hint that triggers
process investigation; no harness, account, capability or input authority is
inferred from that string. Both typed snapshot paths retain the same fields.
Scheduler diagnostics expose chosen interval/reason, age, recent-change state and
late fallback explicitly. These diagnostics do not churn display revision tokens.

## Public checks

A real Unix-native/tmux fixture proves qualified idle skips inventory at6seconds
and uses30second fallback. Equivalent native rebaseline leaves projection stable.
A running status switches to five-second fallback; subsequent idle status preserves
recent change eligibility. The fixture then prints an owned red error while its
process/command metadata stay unchanged. At the next six-second scheduler advance
the public observer records present with a redacted message and zero health checks.
Removing just the native dirty marking reproduces absent instead of present;
that causal red is retained in dirty-error-red.txt. Source loss retains fast fallback.
No terminal input or provider request was used to create the fixture output.

Focused receipts record28selected tests passing Python3.12.13 and3.11.15. An added
public passive-vs-finite snapshot equality assertion verifies the command hint
shape and the actual sleep command. Ruff undefined-name gate and whitespace checks
pass. Full installed100tab60second resource qualification remains with547; this
packet neither relaxes thresholds nor claims a performance gate pass.

Memory disposition: forbidden; no explicit memory-write request.
