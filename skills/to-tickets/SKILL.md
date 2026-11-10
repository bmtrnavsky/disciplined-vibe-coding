---
name: to-tickets
description: Use at full-spec rung and above, after a milestone plan is approved, to cut it into tickets with explicit blocked-by edges and publish them as Kanban cards. Opt-in; the plain plan-then-execute path stays the default.
phase: Plan
---

# To tickets — one approved plan, many grabbable tickets

## Prime directive

A plan is a map. A ticket is one promise a single builder can keep in one
sitting. Hand out promises, not maps.

## When this fires

All four must be true. If any is false, do not fire — plan and execute are
already enough:

1. The rung is full-spec or above.
2. A milestone plan exists and is **approved**.
3. The work is big enough to need the split: 8 or more plan steps, or 2 or more
   workers, or work that will not finish in this session.
4. You are in an interactive session, so you can ask before publishing.

Never fire automatically after `plan`. Brad (or the operator) asks for tickets.

## Steps, in order

### 1. Read the plan you were given

Read the whole plan file, its to-spec, and the files-touched list. The plan is
the only source of truth for scope: if the plan does not say it, it is not a
ticket.

Refuse and say why if: no plan exists, the plan is still DRAFT, or teardown has
not passed. Tickets cut from an unreviewed plan multiply an unexamined idea.

You may read code to understand the plan. You may not change it. Nothing is
built in this skill.

### 2. Cut the plan into tickets

Each ticket is a **vertical slice**: a narrow path that runs all the way through
the work and leaves something a person can see working. A ticket that only
changes a layer is a horizontal slice — that is a step, not a ticket.

Rules for the cut:

- A ticket sweeps 2–6 plan steps. Fewer is a step wearing a costume; more will
  not fit one sitting.
- A finished ticket is demoable or checkable on its own, with its own verify
  command from the plan.
- A ticket fits one fresh context window. That is the real size limit.
- Every plan step lands in exactly one ticket. A step in no ticket is a hole; a
  step in two is a merge waiting to happen.
- Keep the plan's exact paths in the plan. The ticket carries behavior and its
  verify command; its first instruction is "read plan section T<n>".

Number tickets `T1…Tn` so blockers come first. A reader should be able to go
top to bottom.

### 3. Declare the edges

Every ticket gets exactly one line: `blocked by: <ticket ids>` or
`blocked by: none`.

An edge is real only if the blocker's *output* is needed as input. "It feels
later" is not an edge; neither is "same area of the code". Over-declaring edges
serializes work that could run in parallel, which is the exact cost tickets are
meant to remove.

Two tickets that touch the same file are **not** blocked — they are serialized
by execute's shared-file rule. Do not express file contention as a dependency.

A cyclic set of edges means the cut is wrong. Re-cut; do not publish.

### 4. Wide refactor? Sequence it, do not slice it

A wide refactor is one mechanical change whose blast radius covers the codebase,
so no slice can land green. Do not force it into a vertical ticket. Use three
ticket kinds, in this order:

- **expand** — add the new form beside the old. Nothing breaks.
- **migrate** — move call sites over in batches sized by blast radius (per
  package, per directory). One batch, one ticket, each `blocked by: expand`.
  The old form still exists, so each batch can stay green.
- **contract** — delete the old form. `blocked by:` every migrate ticket.

If even the batches cannot stay green alone, they share an integration branch
and one final integrate-and-verify ticket that all of them block. Green is
promised only there. Say that out loud in the quiz so nobody is surprised.

### 5. Quiz before publishing

Present the ticket set as a numbered list. Per ticket show only:

- **Title**
- **blocked by** (or `none`)
- **What it delivers** — the behaviour that becomes true, from the user's side
- **Its verify command**

Then ask exactly three questions:

1. Is the size right — any ticket too coarse or too fine?
2. Are the edges right — does each ticket depend only on what truly gates it?
3. Merge or split anything?

Iterate until approved. On the third pass with no agreement, stop and report
what is unresolved: size questions are usually a scope question in disguise.

### 6. Publish to the board

Publish only after approval, and only as cards:

- One card per ticket. Never one card holding a list.
- `parents=[...]` carries the blocking edges. The board already promotes a child
  to ready only when every parent is done — that is the frontier, and nothing
  needs to store it.
- Publish in dependency order so every parent id exists before it is referenced.
- Assign the right profile. A card without an assignee is never dispatched, so an
  unassigned card is an unfinished publish.
- Link the milestone card as the parent of the fan-out, or note it in the body
  when the milestone has no card.
- The card body is the ticket: what to build, acceptance checks, verify command,
  rollback line, and the plan section to read first.

If publishing fails partway, report the cards created so far and stop. Do not
retry into a half-published graph — duplicates in a dependency graph are worse
than a pause.

### 7. Hand off

State which tickets are on the frontier right now, and which are waiting. From
here `execute` owns the build and the books: the orchestrator alone touches git,
plan files, statuses, and gates. This skill does not track the work it published.

## The card body

```
## What to build
<the behaviour that becomes true, from the user's side. No layer-by-layer list.>

## Plan section
Read plan section <T<n>> before starting: it holds the exact paths.

## Acceptance checks
- [ ] <check 1>
- [ ] <check 2>

## Verify
<the exact re-runnable command from the plan>

## Rollback
Revert this ticket's commit (<sha> is recorded at commit time).
```

No absolute file paths in the card body. The plan holds them, the card points at
the plan section. A card that survives a file move is worth more than one that
saves a hop.

## Vocabulary (the whole change)

| Word | Meaning |
|---|---|
| ticket | a named group of 2–6 plan steps, demoable alone, one context window |
| blocked by | the tickets whose output this ticket needs as input |
| frontier | derived, never stored: tickets whose blockers are done |
| expand / contract | the three-part sequence used only for a wide refactor |

At ticket rung the commit unit is **one ticket, one build, one commit**, which
makes rollback a revert and makes cross-session resume a named thing.

## What this skill never does

- Never writes code, tests, or plan edits.
- Never publishes without approval, and never publishes from a headless run —
  it writes a DRAFT under `.pipeline/tickets/` and stops.
- Never writes card status, closes a parent, or touches git.
- Never puts ticket files in `.pipeline/plans/` — that directory is what proves
  a plan was shaped, and a stray file there can satisfy the check.
- Never invents scope the plan does not contain. Discoveries go back to the plan.

## Done when

- Every plan step sits in exactly one ticket; every ticket has an edge line, a
  verify command, and a rollback line.
- The user approved size and edges.
- Cards exist, each with a parent set and an assignee, and the frontier was named.
- Nothing outside the board and `.pipeline/tickets/` was written.

## Cognitive traps

- "More tickets looks thorough" — a ticket nobody can demo is a step.
- "This depends on that area of code" — edges are about needed output, not
  proximity.
- "I'll publish now and fix the graph later" — a broken graph dispatches wrong
  work at once; the quiz is cheaper than the cleanup.
- "The skill should also track progress" — the board tracks progress. One hand
  writes the books.

## Guardrails

- No plan, no tickets. No approval, no publish. No human, no publish.
- Cyclic edges stop the run.
- One card per ticket, one assignee per card.
