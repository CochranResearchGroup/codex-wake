Single broad review pass1, Standards axis. Frozen head afd0061f; diff command git diff fa2363c24bf921ecf0bd8390739e96041e620e8f...afd0061f. Full commits.txt and diff.patch adjacent. Standards: AGENTS.md; docs/dev/policies/0005-engineering-git-and-release.md,0006-validation-and-closeout.md,0008-codegraph-usage.md,0014-architecture-guardrails.md,0016-code-testing-discipline.md,0017-work-item-traceability.md,0021-collaborative-development-workflow.md; docs/agents/codex-code-discovery.md and runtime-proof.md. No CONTRIBUTING.md or CODING_STANDARDS.md found. Read relevant standards. No edits/no delegation. Report file/line and documented rule for hard violations; baseline heuristics below are judgement calls, repository overrides and skip tooling-enforced checks. Under400words. Prioritize consequential correctness/safety/lifecycle problems; do not invent nits.

- **Mysterious Name**: a function, variable, or type whose name doesn't reveal what it does or holds. → rename it; if no honest name comes, the design's murky.
- **Duplicated Code**: the same logic shape appears in more than one hunk or file in the change. → extract the shared shape, call it from both.
- **Feature Envy**: a method that reaches into another object's data more than its own. → move the method onto the data it envies.
- **Data Clumps**: the same few fields or params keep travelling together (a type wanting to be born). → bundle them into one type, pass that.
- **Primitive Obsession**: a primitive or string standing in for a domain concept that deserves its own type. → give the concept its own small type.
- **Repeated Switches**: the same `switch`/`if`-cascade on the same type recurs across the change. → replace with polymorphism, or one map both sites share.
- **Shotgun Surgery**: one logical change forces scattered edits across many files in the diff. → gather what changes together into one module.
- **Divergent Change**: one file or module is edited for several unrelated reasons. → split so each module changes for one reason.
- **Speculative Generality**: abstraction, parameters, or hooks added for needs the spec doesn't have. → delete it; inline back until a real need shows.
- **Message Chains**: long `a.b().c().d()` navigation the caller shouldn't depend on. → hide the walk behind one method on the first object.
- **Middle Man**: a class or function that mostly just delegates onward. → cut it, call the real target direct.
- **Refused Bequest**: a subclass or implementer that ignores or overrides most of what it inherits. → drop the inheritance, use composition.

