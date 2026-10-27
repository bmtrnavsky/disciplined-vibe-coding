---
name: disciplined-vibe-coding
description: Run any coding task through Intake, Define, Economy gate, Plan, Build, Verify, Commit — with Wayfinder tracking riding along. Use at the start of any build, fix, or multi-session project.
phase: Any
version: 0.1.0
---

# Disciplined vibe-coding pipeline — end to end

> Narrative framing adapted from Google's Elephant-Goldfish Model (Apache 2.0) —
> <https://github.com/google/elephant-goldfish-model>.
> Role names (elephant / goldfish), teardown, drift, and the five review-round
> names travel from EGM; all prose here is original. Pipeline mechanics
> (Define/Plan/Build/Verify, gates, friction contract) remain our own.

One loop per small task, or per milestone of a larger project.
Same stages, same words, every time.

```text
Intake --> Define --> Economy gate --> Plan --> Build --> Verify --> Commit
Wayfinder rides along all stages (one-line status at each stage exit).
```

## Cast: elephant, goldfish, you

- **Elephant** holds full context — your project, requirements, earlier
  decisions — and drafts the spec. That is you plus the builder agent
  working from the whole conversation.
- **Goldfish** sees only the spec plus the sources it links to, with no
  memory of the earlier chat. That fresh-eyes read is what catches
  unstated assumptions. Simulate it by re-reading the spec cold, or hand
  the spec alone to a second session.
- **You** resolve trade-offs and approve the spec before any code exists.

Design with the elephant. Review with the goldfish. You decide.

## Friction contract (hard rule)

Every gate below fires as a **fast check plus one-line reason**.
No multi-step friction. No blocking prompts for routine moves.
A gate that slows the builder gets bypassed; a gate that rides along gets
followed. Small work gets less ceremony, never more.

## Stage map (pipeline stage → skill that owns it)

| Stage | Skill | Artifact |
|---|---|---|
| 0. Intake (brainstorming capture) | `intake` | intake block atop the to-spec, or a one-liner in chat |
| 1. Define (grill-with-docs → to-spec) | `intake`, `brainstorm`, `research` | `.pipeline/to-spec.md` (workdir; vault note only if durable) |
| 2. Economy gate (scope rung) | this file, `references/economy-ladder.md` | one declared sentence in the to-spec |
| 3. Plan (writing-plans format) | `plan` | `.pipeline/plans/NN-<milestone>.md`, or 3 bullets at micro-spec |
| 4. Build (working-tree-only, test-first) | `execute`, `test-first`, `debug` | code + failing-then-passing tests |
| 5. Verify (teardown review + local proof + drift) | `verify`, `code-comment-hygiene` | fresh evidence, compact report |
| 6. Commit (one feature, one build, one commit) | `version` | narrative commit; changelog entry when changes happen |
| Rides along: Wayfinder | this file, `templates/wayfinder.md` | `.pipeline/wayfinder.md`, one line per stage exit |

## 0. Intake — 5-minute structured capture

Record problem, desired outcome, constraints, non-goals. Raw, no judging.
Trivial asks skip it: a one-liner in chat *is* the intake.
Then hand to `intake` for direction confirmation and stakes tier
(TOY / WORKFLOW / MONEY).

## 1. Define — grill-with-docs, then to-spec

Interrogate the request against the relevant docs and skill references
*first*, then write the spec before any code. The grill is doc-grounded,
not open-ended questioning: check indexed sources, surface contradictions
and missing decisions, record them in the spec.

Cap: docs check plus at most 3 clarifying questions, then proceed with
stated assumptions. Routine moves (obvious fix, single-file change) get a
3-line micro-spec, not the full artifact.
Template: `templates/to-spec.md`.

The elephant drafts here. The goldfish has not entered yet.

## 2. Economy gate — declare the rung, in one sentence

Read `references/economy-ladder.md`. Declare one sentence, for example:
"rung: micro-spec, reversible single-file change."
The rung sets the ceremony for every later stage. This gate removes
friction by downgrading ceremony for small work.

The rung also sets teardown depth (see Verify): micro-spec gets the
two-pass teardown; full-spec and above get all five rounds.

## 3. Plan — fixed shape, rung-scaled

Full format at full-spec rung and above (`templates/writing-plan.md`):
steps, files touched, test strategy, verify criteria, commit message draft.
At micro-spec rung it collapses to 3 bullets. Never freeform
"I'll figure it out as I go."

## 4. Build — working-tree-only, test-first

Unchanged builder invariants: all edits in the working tree, tests written
before or with the code (`test-first`), local proof before claiming done.
These are builder habits, not gates. Nothing fires, nothing blocks.

## 5. Verify — teardown review, local proof, drift check

Three jobs, in this order: teardown the spec before trusting it, prove the
code locally, then note drift for later.

### 5a. Teardown — goldfish review before code counts

Run the teardown with goldfish eyes: spec plus linked sources only,
earlier conversation ignored. Similar is not same. Rung-scaled:

- **Micro-spec and below (two passes):** consequence pass asks what
  happens if we build exactly this and where it breaks; alternatives pass
  asks what else solves it and whether this is the strongest option.
- **Full-spec and above (five rounds):** run all five, in order —
  1. initial zoom-out (does the whole shape hang together),
  2. comprehension (could a stranger follow it cold),
  3. design critique (trade-offs, edge cases, weakest points),
  4. intermediate zoom-out (does it still fit the codebase after the critique),
  5. implementation readiness (is the plan concrete enough to build from).

One line per round in the verify report. Fix the spec, not the code,
when a round fails — then re-run only the failed round (max one re-run
per round at micro-spec; full-spec may re-run the full five once).

### 5b. Local proof, then hygiene

Run the real thing locally. Then the `code-comment-hygiene` pass
(report-only, owned by the builder). Proof is the job, not overhead.

### 5c. Drift — later check after the build

After proof, compare the approved spec against what actually shipped and
record divergences only: missing pieces, shortcuts, or a different shape
than planned. If nothing diverged, write "no drift." File it with the
verify report so a later session can spot spec-code drift without
re-reading the whole build.

## 6. Commit — one feature, one build, one commit

Commit convention `type: concise subject`. The to-spec acceptance criteria
are the commit's proof statement. Single commit, no release dance for
routine work.

## Wayfinder — one line per stage exit

At each stage exit, update `.pipeline/wayfinder.md`: stage, decisions,
next step (`templates/wayfinder.md`). Read-on-resume only. No prompts,
no forms. Any session or profile resumes mid-pipeline with zero re-brief.

## v0.1.0 resolutions (adopted from the proposal)

- Rung thresholds: reversibility plus file count plus blast radius
  (see `references/economy-ladder.md`).
- To-spec home: workdir file during build; vault note only if durable.
- Wayfinder store: tiny human-readable file in workdir.
- 1.0 bar: three real builds through the full pipeline, zero bypasses.
