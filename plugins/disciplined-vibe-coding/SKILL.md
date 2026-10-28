---
name: disciplined-vibe-coding
description: Run any coding task through Intake, Define, Economy gate, Plan, Teardown, Build, Verify, Commit — with Wayfinder tracking riding along. Use at the start of any build, fix, or multi-session project.
phase: Any
version: 0.2.0
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
Intake --> Define --> Economy gate --> Plan --> Teardown --> Build --> Verify --> Commit
Wayfinder rides along all stages (one-line status plus gate result at each stage exit).
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
Small work gets less ceremony, never more.

## Gate enforcement (hard rule)

A failed gate blocks the next stage. The builder cannot advance past
a red gate on its own authority. The only way past a red gate without
fixing it is an explicit user bypass, logged in the Wayfinder result
line: who approved, what was red, and why it was waived. An unlogged
bypass is a pipeline defect, counted the same as a skipped stage. A
gate that slows the builder gets fixed; it never gets silently skipped.

## Stage map (pipeline stage → skill that owns it)

| Stage | Skill | Artifact |
|---|---|---|
| 0. Intake (brainstorming capture) | `intake` | intake block atop the to-spec, or a one-liner in chat |
| 1. Define (grill-with-docs → to-spec) | `intake`, `brainstorm`, `research` | `.pipeline/to-spec.md` (workdir; vault note only if durable) |
| 2. Economy gate (scope rung) | this file, `references/economy-ladder.md` | one declared sentence in the to-spec |
| 3. Plan (writing-plans format) | `plan` | `.pipeline/plans/NN-<milestone>.md`, or 3 bullets at micro-spec |
| 3.5. Teardown (goldfish pre-build review) | this file §3.5 | round notes in plan/to-spec + wayfinder pass/fail |
| 4. Build (working-tree-only, test-first) | `execute`, `test-first`, `debug` | code + failing-then-passing tests |
| 5. Verify (local proof + drift) | `verify` | fresh evidence, compact report, plan-file table |
| 6. Commit (one feature, one build, one commit) | `version` | narrative commit; changelog at full-spec+, tag at project |
| Rides along: Wayfinder | this file, `templates/wayfinder.md` | `.pipeline/wayfinder.md`, one line plus gate result per stage exit |

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

The rung also sets teardown depth (see §3.5): micro-spec gets the
two-pass teardown; full-spec and above get all five rounds.

Step-up rule: the builder declares a higher rung the moment the blast
radius grows past the declared one (more files, a new dependency, an
irreversible or production touch, a MONEY-tier surface). The user
confirms at the next stop — immediately for MONEY-tier touches.
Stepping up backfills the new rung's missing artifacts (spec, plan
shape, evidence) before Build continues. A rung never steps down
mid-build.

## 3. Plan — fixed shape, rung-scaled

Full format at full-spec rung and above (`templates/writing-plan.md`):
steps, files touched, test strategy, verify criteria, commit message draft.
At micro-spec rung it collapses to 3 bullets. Never freeform
"I'll figure it out as I go."

## 3.5. Teardown — goldfish review before code counts

Teardown happens here, between Plan and Build: it reviews the spec and plan
before any code is written. Reviewing the spec after the build would only
find problems already cemented in code. Post-build checking belongs to
Verify (local proof) and drift, not to teardown.

Run the teardown with goldfish eyes: spec plus linked sources only,
earlier conversation ignored. The reviewer opens only the spec plus
its linked sources: no chat memory, no hallway context, no "you know
what I meant." Each round note states the sources opened. Similar is
not same: a look-alike precedent that answers a different question
does not pass. Rung-scaled:

- **Micro-spec and below (two passes):** consequence pass asks what
  happens if we build exactly this and where it breaks; alternatives pass
  asks what else solves it and whether this is the strongest option.
- **Full-spec and above (five rounds):** run all five, in order —
  1. initial zoom-out (does the whole shape hang together),
  2. comprehension (could a stranger follow it cold),
  3. design critique (trade-offs, edge cases, weakest points),
  4. intermediate zoom-out (does it still fit the codebase after the critique),
  5. implementation readiness (is the plan concrete enough to build from).

One line per round in the plan file (full-spec and above) or the to-spec
(micro-spec); one-liners record pass/fail in chat. Fix the spec, not the
code — no code exists yet — when a round fails, then re-run only the
failed round (max one re-run per round at micro-spec; full-spec may re-run
the full five once). A second failure on the same round stops the
pipeline: no third attempt without a user direction change. Report
tried / learned / unexplained / options and wait for his call (same
stop shape as `debug`). Wayfinder records pass/fail plus the one-line reason
that fired the gate.

## 4. Build — working-tree-only, test-first

Unchanged builder invariants: all edits in the working tree, tests written
before or with the code (`test-first`), local proof before claiming done.
These are builder habits, not gates. Nothing fires, nothing blocks. Build
starts only after Teardown passes (§3.5) — no code exists before review.

## 5. Verify — local proof, then drift

Two jobs, in this order: prove the code works locally, then check you built
what was spec'd. Teardown already ran pre-build (§3.5); Verify trusts the
reviewed spec and checks the code against it.

### 5a. Local proof

Run the real thing locally. Proof is the job, not overhead.

### 5b. Drift — check after the build

After proof, compare the approved spec against what actually shipped and
record divergences only: missing pieces, shortcuts, or a different shape
than planned. If nothing diverged, write "no drift." File it with the
verify report so a later session can spot spec-code drift without
re-reading the whole build.

## 6. Commit — one feature, one build, one commit

Commit convention `type: concise subject`. The to-spec acceptance criteria
are the commit's proof statement. Secret scan before every commit: search
the staged diff for keys, tokens, passwords, and connection strings. A hit
blocks the commit until the secret is revoked or moved out of the tree.
One feature, one build, one commit —
with rung-scaled ceremony: one-liner and micro-spec ship as a single
commit with no changelog or tag; full-spec adds a changelog entry
(`write-docs`); only project-rung releases earn a tag. Routine work gets
no release dance because routine work is not a release.

## Wayfinder — one line plus gate result per stage exit

At each stage exit, update `.pipeline/wayfinder.md`: stage, decisions,
next step, and the gate result — pass/fail plus the one-line reason that
fired the gate (`templates/wayfinder.md`). The result line is what makes
each gate checkable after the fact: a later session can see not just where
the run stopped but why each prior gate let it through. Read-on-resume
only. No prompts, no forms. Any session or profile resumes mid-pipeline
with zero re-brief.

## Verify artifacts — where the proof lives

- Evidence table: appended to the plan file (`verify`), chat-only at
  one-liner rung (no plan file exists there).
- Teardown round notes: plan file (full-spec+) or to-spec (micro-spec).
- Gate results: one result line per stage exit in `.pipeline/wayfinder.md`.
- Research trail: `.pipeline/read.log` entries (`research`).

## v0.2.0 resolutions

- Teardown runs pre-build (§3.5), between Plan and Build — never post-build.
- Commit ceremony is rung-scaled: changelog at full-spec+, tags for
  project-rung releases only; routine work ships as one commit, no release.
- Gates are checkable: Wayfinder records a pass/fail result per stage exit;
  Verify artifacts have named homes (see Verify artifacts above).

## v0.1.0 resolutions (adopted from the proposal)

- Rung thresholds: reversibility plus file count plus blast radius
  (see `references/economy-ladder.md`).
- To-spec home: workdir file during build; vault note only if durable.
- Wayfinder store: tiny human-readable file in workdir.
- 1.0 bar: three real builds through the full pipeline, zero bypasses.
  A build counts when it runs every stage for its rung, files its
  evidence table and Wayfinder gate lines, and logs zero bypasses.
  The three builds are named in the changelog entry that claims 1.0.
