# Plan0211 implementation and review closeout

All eight implementation tickets #527–#534 are closed. Parent #526 remains open.
Primary implemented #527; independent ready tickets were delegated one per agent,
then integrated only after dependencies and focused checks qualified.

Runtime freeze: `6afbda8cd166fc3ca08995256729a3353067f34a`.
Final wheel SHA256:
`79d196c249f99ef6ff263d8619cd95e39df77619c07a78dd628162517dc368c6`.
Private installed prefix: `/tmp/wake-p211-postreview-installed`.
No working-host installation, production layout mutation, real provider prompt,
merge, deployment or paid GitHub Actions run occurred.

## Standards

One accepted P1 finding, R1, resolved. Authorization and execution now share
backend/server/session selection, freeze it before journal intent, and fence saved
profile definitions by registry generation. The actual public authentication seam
first reproduced the same-name tmux/psmux saved-profile grant bypass, then denied
it correctly. The installed regression uses an inert profile executable.

## Spec

Three accepted P2 findings resolved:

- R2: session listing now summarizes cached health, activity and error evidence.
  Freshness and container identity fence cached observations; stale/unknown stay
  explicit. This adds no probe or model work during listing.
- R3: native psmux saved Windows cwd defaults now qualify through create/open,
  ensure and inherited new-tab operations. Generic native Windows argv/profile
  defaults are explicitly unsupported before persistence; actual native parsing
  did not qualify. WSL argv/profile defaults work. Cross-server tab movement
  remains unsupported, with no restart substituted for preserving a process.
- R4: enabling routing excludes all preexisting tab birth identities unless
  `--include-existing` is selected, even if a formerly nonmatching tab later matches.

The single review used fixed base `f0798e1` and frozen tip `bbfc494`.
Exactly one bounded TDD remediation pass followed. No second broad review ran.
See `adjudication.md`, `findings.json`, `remediation.json`, and sibling
`review-r2/validation.md`, `review-r3/validation.md` for first failures and fixes.

## Validation

Final post-review focused selection: **82/82 pass on each Python 3.12 and 3.11**,
78.398s and 75.843s respectively. The recorded selection covers profile authority,
scope, session lifecycle, bots, routing, summaries, native bridge/formatting,
contracts, selection CLI, delete, relocation, portable exits/client and completion.
Exact modules and commands remain in remediation and retained command logs.

Qualification is composite: the earlier affected-surface run on 3.12 ran 216
checks with one generated-docs failure, subsequently repaired and its three-check
module passed; the earlier 3.11 affected run passed 218/218. Later changes received
causally focused checks above. We did not rerun or claim a single final full suite.
The 180-second affected/installed budgets were respected; no comprehensive suite
was repeated. `presubmit/qualification.json` preserves source identities/results.

Post-review installed public workflow passed nine checks in 158.070s, including
real stdio MCP, authenticated HTTP/API/OAuth MCP and 22 actual native PowerShell
calls. Negative partial/uncertain controls return exit3. Installed focused R1/R2/R4
checks pass4, and native-default refusal/cwd contract checks pass2. Native psmux
cwd/open/new-tab/ensure/rename-formatting/delete/peer checks pass8. Package input,
Windows member equality and final cleanup readbacks are in the post-review packet.

Local static checks: generated command reference check, policy wiring, undefined
name lint, compileall, whitespace and active planning audit pass. Planning audit
retains 20 existing accepted baseline findings. Local Python/Linux plus actual
native Windows qualification replace hosted CI under repository cost policy;
this is not a hosted runner execution.

## Scope and cleanup

Named terminal sessions, durable empty definitions, human selectors, same-server
tmux process-preserving bulk relocation/conditional undo, categories, opt-in
priority routing/manual holds, explicit populated delete, discovery/help and
Bash/Zsh completion are implemented across CLI/API/MCP. Existing bot launcher
reuse was inspected; real bots were not launched. PowerShell completion and a
Windows-native Wake service remain future work.

Fixture-only psmux warm servers required exact namespace/hash/process-birth fenced
cleanup. Original failures and cleanup attempts are retained. Fresh OS process
readbacks, rather than session names alone, establish fixture cleanup. Unrelated
sessions, services, stock Codex and the working release remain untouched.

Memory disposition: forbidden. No explicit memory-write request; higher-priority
memory instructions require one. A non-write receipt is recorded outside Git.

Standards: 1 accepted/resolved (highest P1); Spec: 3 accepted/resolved (highest P2); remaining findings: 0.
