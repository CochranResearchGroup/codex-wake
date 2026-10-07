# Policy | Architecture Guardrails

## Policy

- Derive implementation boundaries from the live architecture and current service seams, not from aspirational or superseded layouts by default.
- Do not add new top-level workflows, endpoints, abstractions, or major aliases unless the governing plan or roadmap is updated in the same slice.
- Prefer tightening semantics and ownership boundaries over widening the surface area opportunistically.
- Prefer the Matt Pocock `codebase-design` workflow for interface and seam
  changes: hide consequential behavior behind a small interface, concentrate
  knowledge and change in the owning module, and test through the interface
  callers use. Judge depth by capability per interface a caller must learn,
  rather than implementation size. Avoid pass-through layers and speculative
  adapters; introduce a seam for a concrete variation or testability need.
- Use `domain-modeling` when domain language or relationships change. Sharpen
  terms with concrete scenarios and update the configured glossary as decisions
  settle; keep implementation detail in the appropriate design record. Record
  meaningful hard-to-reverse tradeoffs without requiring an ADR for routine
  implementation choices.
- Keep provider-specific or deployment-specific heuristics at the narrowest layer that can own them cleanly.
- When a change would blur current architecture boundaries, stop and update the governing plan before proceeding.

## Adoption Notes

Use this module when the repo:
- has a service or architecture seam that must stay coherent
- has active refactors or staged migration work
- frequently risks structural drift through ad hoc feature additions
