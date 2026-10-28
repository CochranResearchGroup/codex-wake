# Account/build workflow: one review and one remediation pass

Fixed point: 48602bd458152cddb4f2ce1ab721098e9417d599. Reviewed candidate:6fec3d73aadd4da271a2004a53e14bf4b62db903. Specification: CochranResearchGroup/codex-wake#371; coordination#369. This is a source and disposable-fixture delivery, not production activation or complete acceptance of the broader account project.

## Standards

No documented hard violations established. Accepted one nonblocking maintenance finding: channel-specific required capabilities were duplicated across staging/revalidation. One shared mapping now owns that predicate. Duplicate durable JSON writers remain nonblocking backlog; no incorrect accepted behavior was demonstrated, and changing writer ownership was unnecessary for the bounded behavioral pass.

## Spec

Two P1 findings accepted and corrected:

1. Real native source contains Bubblewrap’s LICENSE link to COPYING, but source staging rejected all links. Public local-tree and archive cases went red, then green after safe regular-file source-link normalization. Source/archive identity and link provenance remain; outside/cyclic/directory/special links and final-package links hold.
2. Activation checked one tenant but published a default used by every tenant. The public regression actually launched unchecked Bob before the fix. Activation/rollback now select per validated canonical home; the launcher resolves that owner and rechecks declared history schemas before opening the backend. Alice/schema5 activation leaves Bob/schema6 unselected; adding schema6 to Alice after activation also holds. Source selection, archival protection and cached version reporting consume owner-qualified selections.

Exactly one combined Standards/Spec review and one coordinated TDD remediation pass were run. No second broad review was requested or performed.

## Validation

- Local complete suites:106 tests passed on Python3.11 and3.12; diff whitespace clean.
- Corrected installed development wheel: SHA256 c90421584cdc6cd8219fde164e22ded6443fe5b353e798b90dabae67c3cecff3; source2d56a07. Seven WSL acceptance groups plus13 installed upgrade tests pass. The current branch’s nine runtime modules exactly match the installed/qualified wheel; later commits affect documentation and the reproducible recipe.
- Native stock and modified binaries, two synthetic accounts, persistent terminal titles, concurrent clients, owner resume, duplicate rejection, legacy context fork, dropped-response reconciliation and explicit paginated hold were exercised. No model turns or production credentials; owned-process census empty.
- A prior wheel failed the original six-group packet, establishing a red-capable installed boundary. Setup failures remain retained and are not passes.
- One local scheduled-check cached-status assertion was intermittent during the full suite. It did not recur in12 isolated probes, the focused13-test upgrade suite, or subsequent full3.11/3.12 suites. Cause remains unproved; it is retained as a nonblocking validation concern rather than relabeled fixed. Metadata checks are bounded and best-effort and cannot block selected launches.

## Remaining boundaries

The real-account reauthentication report remains open in#372; local routing/loading and inherited-credential crossover fixes are demonstrated, not real refresh/expiry acceptance. Cross-account foreign paginated history and actual active-goal/allocation binding remain open in#376. Preparing legacy context neither starts work nor renews resources. Broader existing native reload/notices/accounting evidence was causally inherited and is distinguished from freshly run cases. Byobu workspace restoration remains#368.

Standards:1 maintenance finding fixed,1 nonblocking backlog; no documented violations. Spec:2 accepted P1 findings fixed; broader#372/#376 acceptance remains open.
