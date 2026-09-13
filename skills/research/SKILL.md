---
name: research
description: Use before building anything novel, modifying unfamiliar code, ranking unfamiliar tech, or whenever a library/API is involved. Logs every consultation to .turing/read.log. (Lineage: godmode/reference-engine, godmode/github-search, agent-skills/api-design)
phase: Any
---

# Research — read it before you build on it

## Prime directive
Documentation and prior art come first; implementation theory comes second.

## Steps (in order)
1. **Docs on every dependency** — quickstart, API ref, pitfalls. Docs tools over parametric memory. Never write against an API from memory.
2. **Log every consultation** to `.turing/read.log` (what, when, why). Audit trail; feeds read-check hook.
3. **Prior art before invention** — "could an existing tool/model/service do this?" is required. Provider-managed over hand-rolled.
4. **Read before modifying** — file, imports/callers, tests.
5. **Carry sources forward** into plan citations.

## Cognitive traps
- "This pattern is standard" — version drift breaks "standard" code.
- "Searching wastes tokens" — a failed implement-debug-revert cycle costs ten times a read.
- "Reading code is researching" — code says what it does; docs say what it's supposed to do.

## Guardrails
- No API in a plan without docs consulted.
- No new dependency without existing-solution check.
