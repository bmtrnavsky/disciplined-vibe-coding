---
name: debug
description: Use whenever behavior is wrong, tests fail, or the user reports a bug. Docs-first root-cause triage, observation mode, two-failure stop. (Lineage: superpowers/systematic-debugging, godmode/error-recovery, godmode/fault-diagnosis)
phase: Build
---

# Debug — docs before theory, cause before fix

## Prime directive
Never patch a symptom you haven't explained.

## Steps (in order)
1. **Reproduce** if you can; else observation mode (his symptoms, exact errors, timing). No blind coding.
2. **Docs ALWAYS** via `research` docs step; vendor changelogs count as docs for post-update breakage. Log it.
3. **Ranked falsifiable theories**, each one-step checkable.
4. **Isolate cause.** "Fix worked" without "cause is X" is not done.
5. **Fix + guard** where guardable; unguardable stacks get honest declaration + recorded manual check.
6. **Two-failure stop:** tried / learned / unexplained / options. His call.

## Cognitive traps
- "I know this stack" — confident wrong fixes are born there. Docs.
- "One more edit" — the counter exists for this.
- "Can't reproduce = guess" — live-system guesses break more than they fix.

## Guardrails
- Third same-shape attempt prohibited.
- Never silence warnings or catch-alls as a "fix."
- No live-production edits without understood cause and rollback path.
