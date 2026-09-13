---
name: execute
description: Use in Build to run an approved plan. Direct work or up to 5 workers; orchestrator exclusively owns git, plan/roadmap files, status, gates. Workers write only assigned files. (Lineage: agent-skills/incremental-implementation, godmode/task-runner)
phase: Build
---

# Execute — approved plan, checked landing, orchestrator owns the books

## Prime directive
Workers write assigned files only. The orchestrator alone touches git, plans, statuses, and gates.

## Steps (in order)
1. **Direct execute** small/single-file tasks.
2. **Workers (max 5)** for independent mechanical/long items: briefs carry requirements, constraints, decision-log lines, acceptance criteria. Workers: assigned files only; no git; no plan edits; no gates; no sub-workers. Shared files serialize.
3. **Merge + review** each worker diff vs acceptance criteria, THEN commit (per `version`).
4. **Checkpoint report** plainly: built/where/what passed/what owes. Offer continue/adjust/stop. Wait on structural.
5. **Long-running tasks** (training, bulk jobs): start them, report the job id/log path, and DON'T block the checkpoint loop — queue completion review as a task with its metric band from the budget line.
6. **Session close:** status footer update + commit + one-sentence stopping point.
7. **Diff-size flag** at ~2x estimate: stop; report growth.

## Cognitive traps
- "Workers can run their own git" — one hand writes the books.
- "Launch-and-pray is parallelism" — long jobs are launched with completion reviews queued.
- "Checkpoints slow him down" — checkpoints are his control.

## Guardrails
- Workers never hold approval power.
- No code outside the approved plan; discoveries go back to the plan.
