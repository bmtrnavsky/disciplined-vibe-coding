---
name: test-first
description: Use during Build for testable logic. Failing test before implementation (light RGR). Declared exemptions over faked tests. (Lineage: superpowers/test-driven-development, godmode/test-first)
phase: Build
---

# Test-first — RED before GREEN

## Prime directive
The test exists and fails before the passing code exists.

## Steps
1. **RED:** one test, one behavior; watch it fail.
2. **GREEN:** smallest passing change.
3. **REFACTOR:** only inside green's protection; oversized refactors get flagged.
4. **Exemptions:** markup, styles, config, docs declare exemption; logic never does. Model tasks: the "test" is the pre-registered metric band from the plan.

## Cognitive traps
- "Tests after" — they test what you wrote, not what you promised.
- "One big test" — one behavior per test.

## Guardrails
- Never implement first to "check the plan."
- Never weaken a failing test to reach green.

## Rung scaling (economy ladder)

Full-spec and above: RED then GREEN, no exceptions. Micro-spec: one
failing check before the fix. One-liner: a smoke check after the change
suffices, declared in chat. Declared exemptions beat faked tests at every
rung.
