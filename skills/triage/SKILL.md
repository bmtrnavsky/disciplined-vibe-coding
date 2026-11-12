---
name: triage
description: Use at micro-spec rung and above when a request for work arrives. Decides whether it is already built, already rejected, or worth building, then writes the brief a worker can act on. Fires on conditions; publishes nothing.
phase: Define
---

# Triage — decide before you interview

## Prime directive

Nothing is interviewed until it has a verdict, and every verdict is written down.

## When this fires

It fires on its conditions, with no asking. All three must hold:

1. The rung is **micro-spec or above**.
2. The ask is **a request for work**: a change, a fix, a feature. Not a question,
   not a review, not a status check.
3. **No verdict exists for this ask in this session** — no brief, no rejection
   file, no question file already written for it.

Do not fire when:

- the rung is **one-liner** — the chat line is the intake and the verdict;
- a **plan is already approved and work is in flight** — triaging settled scope
  re-litigates a decision the user already made;
- the ask is a **question, a review, or a status check** — there is nothing to
  decide about whether to build it;
- a **verdict already exists** for this ask in this session — re-triaging is
  re-arguing, and the second pass never agrees with the first.

## The four verdicts

One verdict per ask. Pick it, write it, move.

| Verdict | Means | You write |
|---|---|---|
| `proceed` | worth doing, and not already done | the brief |
| `already built` | the behavior exists | one line naming where it lives |
| `out of scope` | not doing this, for a durable reason | `.out-of-scope/<concept>.md` |
| `needs info` | cannot be decided without an answer | the question file |

Two rules that keep the verdicts honest:

- **`already built` is not a rejection.** Never write it to `.out-of-scope/`.
  That store is for requests we turned down, not for features we shipped. Filing
  a built thing there poisons every later dedup check.
- **A deferral is not a verdict.** "Not now", "too busy", "later" means the ask
  has not been triaged yet. Say that, and leave no file behind.

## Steps, in order

1. **Read before you ask.** Read the ask in full, any existing brief or spec for
   it, then the code it touches, `GLOSSARY.md`, `docs/adr/` and
   `.out-of-scope/*.md` if they exist. Log every read through `research` into
   `.pipeline/read.log`. Facts are your job. The user answers decisions only.

2. **Look for it already existing.** Search the codebase by domain concept, not
   by the request's wording: "night theme" is dark mode. Record where you looked
   and what you ruled out. If the behavior is there, the verdict is
   `already built`, and step 8 is the rest of your job.

3. **Look for it already rejected.** Read every file in `.out-of-scope/`. Match
   by concept, not keyword. On a match, put both in front of the user and ask
   once whether the old decision still holds:
   - **Still holds** — append this request to that file's list, verdict
     `out of scope`.
   - **Changed their mind** — delete the file, and the ask goes back to step 2.
   - **Related but different** — carry on; the two are distinct.
   One question, three answers. Do not re-litigate the reason line by line.

4. **Name the category.** `bug` or `enhancement`, exactly one. A bug is something
   that should work and does not. An enhancement is something that never worked.
   The category changes what "done" means, so it is not cosmetic.

5. **Check the claim before you believe it.** For a bug, reproduce it from the
   stated steps. Reproduced means you have the code path; not reproduced but
   plausible means `needs info`; not reproduced and unclear means `needs info`
   with a specific question. For an enhancement, find the part the code already
   does and name it in the brief, so the worker does not rebuild it.

6. **Give the verdict.** One line, with the reason. **This is not a fork.** A fork
   is two real options where the choice is the user's. A verdict is what the
   evidence answers, so state it and move on. The one exception is step 3's
   reconsideration, which is genuinely the user's call.

7. **Write it where the next reader will look.** `proceed` → the brief, below.
   `out of scope` → `.out-of-scope/<concept>.md`. `needs info` → the question
   file, then a stop. `already built` → the one line, in the brief's `Searched`
   field or in the reply.

8. **Hand off.** `proceed` goes to intake's interview, which hands to
   `grill-with-docs` at full-spec and above, then to the to-spec, then to `plan`.
   This skill never gets past the brief.

## The brief — what a worker can pick up

The rung sets the size. At **full-spec and above**, the full shape below. At
**micro-spec**, three lines and no more: what changes, how you will know, what
not to touch. Below micro-spec this skill does not fire, so there is no brief.

```
## Triage brief

**Verdict:** proceed
**Category:** bug | enhancement
**Stakes:** TOY | WORKFLOW | MONEY
**Rung:** micro-spec | full-spec | project

**Problem:** one sentence, in observable terms.

**Current behavior:**
What happens now. For a bug, the broken behavior and how to see it. For an
enhancement, the status quo it builds on.

**Desired behavior:**
What happens after the work. Include the edge cases and the error conditions.

**Acceptance criteria:**
- [ ] A check someone can run, or see happen
- [ ] Another one, independently checkable
- [ ] The failure case, named

**Out of scope:**
- The adjacent thing that must not be touched
- The related feature that is separate work

**Searched:** where you looked, and what you ruled out.
```

Brief rules, all of them load-bearing:

- **No file paths and no line numbers.** The brief may be picked up weeks later,
  after the files have moved. Name types, functions, commands and config shapes
  instead. The plan carries the paths, because the plan is written today from a
  read of today's code.
- **Behavior, not procedure.** "The `SkillConfig` type accepts an optional
  `schedule` field" is a brief. "Open the types file and add a field" is a
  procedure, and it will be wrong by the time anyone reads it.
- **Acceptance criteria must be checkable.** "Triage works correctly" is not a
  criterion. "Running the ticket check with an unapproved plan exits 2" is.
- **Out of scope must be stated.** It is what stops a worker gold-plating.
- **Where it goes.** The brief is the card body. With no card yet, write
  `.pipeline/triage/<slug>-brief.md`.

## Where no human can answer

A headless run and a Kanban worker have nobody on the other end. Do not wait, and
do not guess a verdict: a guessed verdict decides what gets built, and that is not
a guess anyone is allowed to make.

1. Write `.pipeline/triage/<slug>-needs-info.md`: what is established, then the
   numbered questions, each with a recommended answer.
2. State plainly that the pass did not finish, and name the file.
3. Stop. A Kanban worker calls `kanban_block(kind="needs_input")`. A `dvc_run`
   run writes the file and stops without writing a spec.

A one-line `dvc_run --job` has no room for a brief. There, run the two cheap
checks — already built, already rejected — and write the result at the top of the
generated spec. If either check lands on `needs info`, write the question file and
stop instead of building something unspecified.

## Done when

- Exactly one verdict is chosen and written down.
- The file that verdict calls for exists and is named in the handoff: the brief,
  the rejection file, the question file, or the one `already built` line.
- Where you looked is named, so a human can check the search instead of trusting
  it.
- The next step is named: intake's interview, the grill, the plan, or a stop.

## Never

- Mutate a board status, create a card, dispatch a worker, or publish anything.
  The dispatcher owns `ready`; triage sits on the free side of the spend line.
- Close a card. Write the verdict and the filed reason, then stop; the board
  owner closes.
- Write `.out-of-scope/` for something that is already built.
- Write a file path or a line number into a brief.
- Interview, grill, plan or build before the verdict is written.
- Guess a verdict when no human can answer. Write the question file and stop.
- Record a deferral as a rejection. "Not now" is not "no".
- Ask permission. This skill publishes nothing and spends nothing, so there is
  nothing to approve.

## Cognitive traps

- **"This is a new request."** Most are not. Check `.out-of-scope/` and the
  codebase before believing it is new.
- **"The reporter said it is broken."** A claim is not a symptom. Reproduce it, or
  ask the one question that makes it reproducible.
- **"Out of scope sounds decisive."** A rejection without a durable reason is a
  deferral wearing a suit. If the reason would expire, do not write the file.
- **"More searching looks thorough."** Name where you looked and stop. A search
  with no stopping rule becomes an afternoon.
- **"The brief is a plan."** The brief says what should be true. The plan says
  where and in what order. Writing the plan here steals `plan`'s job and freezes
  paths that are about to change.
- **"Two verdicts are safer."** Two verdicts is no verdict. If they genuinely
  conflict, say both out loud and stop; do not pick silently.

## Guardrails

- One verdict per ask. Conflicting verdicts get stated, not resolved alone.
- At most 3 questions for `needs info`, each with a recommended answer.
- Prose only: no code, no test, no gate, no hook, no dependency.
- `.out-of-scope/` and `GLOSSARY.md` live in the repo being worked on, at
  micro-spec and above, with a target repo present — never in DVC's own repo.
- Every verdict is written where the next reader will look. An unwritten verdict
  did not happen.
