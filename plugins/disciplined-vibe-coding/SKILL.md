---
name: disciplined-vibe-coding
description: Run any coding task through Intake, Define, Economy gate, Plan, Build, Verify, Commit — with Wayfinder tracking riding along. Use at the start of any build, fix, or multi-session project.
phase: Any
version: 0.1.0
---

# Disciplined vibe-coding pipeline — end to end

One loop per small task, or per milestone of a larger project.
Same stages, same words, every time.

```text
Intake --> Define --> Economy gate --> Plan --> Build --> Verify --> Commit
Wayfinder rides along all stages (one-line status at each stage exit).
```

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
| 5. Verify (local proof + hygiene) | `verify`, `code-comment-hygiene` | fresh evidence, compact report |
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

## 2. Economy gate — declare the rung, in one sentence

Read `references/economy-ladder.md`. Declare one sentence, for example:
"rung: micro-spec, reversible single-file change."
The rung sets the ceremony for every later stage. This gate removes
friction by downgrading ceremony for small work.

## 3. Plan — fixed shape, rung-scaled

Full format at full-spec rung and above (`templates/writing-plan.md`):
steps, files touched, test strategy, verify criteria, commit message draft.
At micro-spec rung it collapses to 3 bullets. Never freeform
"I'll figure it out as I go."

## 4. Build — working-tree-only, test-first

Unchanged builder invariants: all edits in the working tree, tests written
before or with the code (`test-first`), local proof before claiming done.
These are builder habits, not gates. Nothing fires, nothing blocks.

## 5. Verify — local proof, then hygiene

Run the real thing locally. Then the `code-comment-hygiene` pass
(report-only, owned by the builder). Proof is the job, not overhead.

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
