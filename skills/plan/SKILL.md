---
name: plan
description: Use to plan one milestone (or small task) into atomic steps: paths, outputs, pass/fail checks, rollback/dry-run for destructive steps, rerun-safe pipelining, budget lines for long-running/compute tasks, decision log, status footer. (Lineage: superpowers/writing-plans, godmode/task-planning)
phase: Plan
---

# Plan — decompose, prove, hand off

## Prime directive
A plan is atomic tasks scoped to ONE milestone.

## Steps (in order)
1. **Scope.** `.turing/plans/NN-<milestone>.md` per milestone. Small tasks: small plans, never none.
2. **Decompose** into 2–5 minute tasks: path, content, expected output, pass/fail check observable without source.
3. **Budget line for long tasks.** Anything >2 minutes of wall time (training runs, big migrations, bulk embedding) gets an explicit line: expected duration, expected cost if paid compute, and completion signal (file written, metric logged). Never let a multi-hour run start without one.
4. **Metric targets with tolerance.** Model/eval tasks: pass criterion is metric + band ("macro-F1 >= 0.82, dedupe on seed 42"), not a bare boolean.
5. **Rerun-safe** for pipeline/collection tasks: check passes when the task runs TWICE; name the idempotency mechanism.
6. **Rollback line + dry-run task** for destructive steps. MONEY-tier systems: the dry run IS paper-trading — live action is a separate, later milestone.
7. **Reuse list FIRST** with one-line justifications for new code.
8. **Decision log** in header (forks/who/why). **Status footer** (done/next/open).
9. **STE style** per `write-docs`. DRAFT until approved.

## Payments rule (hard)
Provider-hosted checkout only. A plan storing/processing raw card data is malformed, full stop.

## Autonomy rule (hard)
If anything in this plan runs unsupervised (bots, schedulers, daemons): decision policy must be codified as config/rules BEFORE code, and a kill-switch task exists. No checkpoint can sit inside a running process, so the design phase carries the judgment.

## Done when
- Tasks have path + output + observable check; destructive items have rollback + dry-run; long items have budget lines; eval items have metric bands.
- Reuse list, decision log, status footer present. Forks answered. APPROVED by Brad.

## Cognitive traps
- "One giant plan shows thoroughness" — roadmap holds the whole; plan holds one milestone.
- "Ran once = works" — survive the second run.
- "Rollbacks are implied" — write the line.

## Guardrails
- No Build before Done-when.
- Plans promising beyond the stated direction are defects.
