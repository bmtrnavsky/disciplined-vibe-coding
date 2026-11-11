---
name: execute
description: Use in Build to run an approved plan. Direct work or up to 5 workers; orchestrator exclusively owns git, plan/roadmap files, status, gates. Workers write only assigned files. (Lineage: agent-skills/incremental-implementation, godmode/task-runner)
phase: Build
---

# Execute — approved plan, checked landing, orchestrator owns the books

## Prime directive
Workers write assigned files only. The orchestrator alone touches git, plans, statuses, and gates.

## Steps (in order)
1. **Gate before Build, not after:** run `python scripts/dvc_stage.py check
   --before Build`. Exit 1 means a stage is unlogged or a gate is red — stop
   and fix it. Fixing it means logging a new PASS for the same gate at the
   same stage. Rework may step back to an earlier stage only right after a
   FAIL, and any Build after a new Define/Economy/Plan record needs a fresh
   Teardown pass. The log line at each stage exit is `dvc_stage.py log --stage
   <stage> --gate <id> --result PASS|FAIL --reason "..."`.
2. **Direct execute** small/single-file tasks.
3. **Workers (max 5)** for independent mechanical/long items: briefs carry requirements, constraints, decision-log lines, acceptance criteria. Workers: assigned files only; no git; no plan edits; no gates; no sub-workers. Shared files serialize.
4. **Merge + review** each worker diff vs acceptance criteria, THEN commit (per `version`).

**Frontier — parallel workers from the plan's `blocked by:` lines.**
Read the ticket groups in the plan file: a ticket is on the frontier when every
ticket in its `blocked by:` line is done. Derive it at each dispatch and never
store it. For published cards the board's `parents=` is the same frontier, and
Kanban enforces that half; inside a run these lines are the only frontier there
is, so read them instead of guessing independence from prose.

5. **Checkpoint report** plainly: built/where/what passed/what owes. Offer continue/adjust/stop. Wait on structural.
6. **Long-running tasks** (training, bulk jobs): start them, report the job id/log path, and DON'T block the checkpoint loop — queue completion review as a task with its metric band from the budget line.
7. **Session close:** status footer update + commit + one-sentence stopping point.
8. **Diff-size flag** at ~2x estimate: stop; report growth.

## Cognitive traps
- "Workers can run their own git" — one hand writes the books.
- "Launch-and-pray is parallelism" — long jobs are launched with completion reviews queued.
- "Checkpoints slow him down" — checkpoints are his control.

## Guardrails
- Workers never hold approval power.
- No code outside the approved plan; discoveries go back to the plan.

## Rung scaling (economy ladder)

One-liner and micro-spec: direct execute, no workers. Workers exist for
full-spec and above. Session-close commit applies at every rung.
