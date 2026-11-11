---
name: disciplined-vibe-coding
description: Run any coding task through Intake, Define, Economy gate, Plan, Teardown, Build, Verify, Commit — with Wayfinder tracking riding along. Use at the start of any build, fix, or multi-session project.
phase: Any
version: 0.3.2
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
who approved, what was red, and why it was waived. An unlogged
bypass is a pipeline defect, counted the same as a skipped stage. A
gate that slows the builder gets fixed; it never gets silently skipped.
Interactive sessions carry that rule in a checkable form:
`scripts/dvc_stage.py log` records each stage exit (stage, gate,
PASS/FAIL, one-line reason), `scripts/dvc_stage.py bypass --by NAME
--why REASON` records a waiver — both flags required, so the tool
cannot write an unlogged bypass — and `scripts/dvc_stage.py check`
fails on a missing stage record, a FAIL with no later bypass, or a
Build recorded before a Teardown pass. A FAIL clears when the same gate
later logs PASS (the fix) or BYPASS (the waiver). Rework steps back only
right after a FAIL. A re-plan needs a fresh Teardown pass before Build.
A new milestone is a new loop: Define after a Verify pass. `verify` runs
that check before any done-claim. A stage with no record at all cannot be
told from a silent bypass, so it counts as one: that is the defect the
log exists to make countable.
Since card series DVC 1/4 the spec record is hashed at Define, and fix B
made it a gate: `dvc_run.py` hashes the spec at Define, declared drift
stays advisory, and undeclared drift fails the run at Verify (G7).
Fix C keeps a run history: re-running over a FAILED run refuses to
start unless `--fresh` is passed, and the report cites every run in
the workdir. Fix E closes the self-declare hole: a build that rewrites
the spec and declares it fails at G7 (only the Build-window delta
fails; declares outside Build still pass), and the reviewer packet
carries the Define spec. Fix F distrusts the workdir: packet assembly
rejects links escaping it, and history lives outside the workdir,
hash-chained. Fix G hardens the runner: builds get a minimal env, the
reviewer stub needs `--test-mode` and is marked STUB everywhere.

G1-G3 are **self-checks** in the autonomous runner: the runner writes the spec
and the plan they grade, so they stop a malformed run but no builder can turn
them red. G4, G5 and G7 grade work the run did not do. In an interactive
session the same shapes are checked by the builder, where a human writes the
artifact.

## Stage map (pipeline stage → skill that owns it)

| Stage | Skill | Artifact |
|---|---|---|
| 0. Intake (brainstorming capture) | `intake` | intake block atop the to-spec, or a one-liner in chat |
| 1. Define (grill-with-docs → to-spec) | `grill-with-docs`, `intake`, `brainstorm`, `research` | `.pipeline/to-spec.md` (workdir; vault note only if durable) |
| 2. Economy gate (scope rung) | this file, `references/economy-ladder.md` | one declared sentence in the to-spec |
| 3. Plan (writing-plans format) | `plan` | `.pipeline/plans/NN-<milestone>.md`, or 3 bullets at micro-spec |
| 3.5. Teardown (goldfish pre-build review; headless is post-build, §3.5a) | this file §3.5 | round notes in plan/to-spec + wayfinder pass/fail |
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

Cap: below full-spec the docs check plus at most 3 clarifying questions, then
proceed with stated assumptions; at full-spec and above `grill-with-docs` sets
the budget — 3 questions a round, 3 rounds a session, at most 9. Routine moves
(obvious fix, single-file change) get a 3-line micro-spec, not the full
artifact.
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
`to-tickets` fires on its conditions, not on request: at full-spec rung and above, with an approved plan, when the work needs the split (8+ steps, 2+ workers, or multi-session), it cuts ticket groups with explicit `blocked by:` edges inside this plan file. Draft before teardown; publish only after teardown passes and the quiz is approved — the quiz stays mandatory because publishing dispatches workers, and `scripts/dvc_tickets.py check --tickets <ids>` is the gate that tells the skill approval **and teardown** were recorded on this plan. Headless runs draft under `.pipeline/tickets/` and stop: with no `--interactive` approval they cannot pass that check. Do not fire below full-spec, on a plan already ticketed, or to publish from a headless run.

## 3.5. Teardown — goldfish review before code counts

Teardown happens here, between Plan and Build: it reviews the spec and plan
before any code is written. Reviewing the spec after the build would only
find problems already cemented in code. Post-build checking belongs to
Verify (local proof) and drift, not to teardown.

### 3.5a Pre-build or post-build: the one place the runner differs

The rule above is the interactive rule, and it is the one this doctrine
runs on. `dvc_run.py` cannot hold it: its reviewer reads the build output,
so that pass runs after Build and is the **post-build drift review**
(gate G4), a different job with a different name. Both halves are stated:

- **Interactive (this doctrine):** teardown reviews spec and plan before
  code exists. Exit it with `scripts/dvc_stage.py log --stage Teardown
  --gate G4 --result PASS --plan <plan file> --reason "..."` (required when
  `to-tickets` will publish from this plan); `dvc_stage.py check` then
  refuses any log where Build comes before a Teardown pass.
- **Headless (`dvc_run.py`):** G4 is the post-build drift review; the
  post-build checks the doctrine already assigns to Verify are G5 (proof
  green) and G7 (spec stable). **No pre-build review gate exists there.**

That gap is stated, not implied. An autonomous run has no human and no
pre-build plan it did not write itself, so it substitutes the post-build
drift review. Interactive sessions carry the pre-build gate because that
is where a plan worth reviewing exists.

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
starts only after Teardown passes (§3.5; headless: the post-build drift
review in §3.5a) — no code exists before review.

## 5. Verify — local proof, then drift

Two jobs, in this order: prove the code works locally, then check you built
what was spec'd. Teardown already ran pre-build (§3.5; headless: its
post-build drift review is §3.5a); Verify trusts the reviewed spec and
checks the code against it. First run `scripts/dvc_stage.py check`: a
missing or red stage record means the done-claim is not verifiable yet.

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
- Gate results: one result line per stage exit in `.pipeline/wayfinder.md`,
  and the machine-checkable copy in `.pipeline/stages.jsonl`
  (`scripts/dvc_stage.py log|bypass|check`).
- Ticket approval: `.pipeline/ticket-approval.json` — who approved which
  ticket set, bound to the plan digest (Status line and card ids excluded;
  `scripts/dvc_tickets.py approve --interactive --by NAME`).
- Research trail: `.pipeline/read.log` entries (`research`).
- Spec lock: `.pipeline/spec.lock` — sha256 at Define, declarations on
  change (`spec_lock.py lock` / `declare --by NAME --why REASON`).

### 5c. Spec record (declared drift is advisory; undeclared drift fails)

`dvc_run.py` hashes the to-spec at Define (`spec_lock.py lock`).
A mid-run change declared (`declare --by NAME --why REASON`) re-hashes
and appends who/when/why to the lock — advisory, never a block, and
Verify quotes the result. A change with no declaration fails the run
at Verify (gate G7 spec-stable): a build that rewrites the spec to
"do nothing" is caught there, never waved through as a pass.

## v0.2.0 resolutions

- Teardown runs pre-build (§3.5), between Plan and Build — never post-build
  in an interactive session. The headless runner's post-build goldfish pass
  is the drift review, and §3.5a names it as such instead of calling it
  teardown.
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
