---
name: grill-with-docs
description: Use at full-spec rung and above in an interactive session when the ask brings a new domain term or the repo uses a term two ways. A bounded interview that settles the vocabulary and the hard decisions before the to-spec. Fires on conditions; publishes nothing.
phase: Define
---

# Grill with docs — settle the words before you write the spec

## Prime directive

No spec is written until the words in it mean one thing to both of us.

## When this fires

It fires on its conditions, with no asking. All three must hold:

1. The rung is **full-spec or above**.
2. **An interactive session**: a human is present and can answer.
3. **Unsettled vocabulary**: the ask brings a new domain term, or the repo
   already uses a term two ways. Check the repo and `GLOSSARY.md` before
   calling a term settled.

Do not fire when:

- the rung is **below full-spec** — the overlay's 3-question docs check is the
  whole grill there;
- the session is **headless** (`dvc_run.py`) or a **Kanban worker** — nobody
  can answer; see §Where no human can answer and stop;
- the **vocabulary is settled** — every term already means one thing in the repo;
- the **plan is already approved** — grilling approved work re-litigates it.

## Budget

Cap: below full-spec the docs check plus at most 3 clarifying questions, then
proceed with stated assumptions; at full-spec and above the grill sets the
budget — 3 questions a round, 3 rounds a session, at most 9. Anything still open
after round three goes into the to-spec as a stated assumption, named plainly.
If you need a fourth question in one round, the ask is too big: step up the rung
or split the milestone. Do not ask more.

## Steps (in order)

Headless changes the shape: skip steps 3, 4 and the step-8 quiz, and go to
§Where no human can answer.

1. **Read before you ask.** Read the ask, any to-spec draft, the plan if one
   exists, `GLOSSARY.md` and `docs/adr/` if they exist, and the code the change
   touches. Log every read through `research` into `.pipeline/read.log`.
   Facts are your job. The user answers decisions only.

2. **Build a question tree, not a list.** Each decision opens the decisions that
   sit under it. Ask only what nothing above it still blocks; leave the rest for
   a later round. A question that depends on one still open belongs to the next
   round.

3. **Ask one round, then wait.** At most **3 questions per round**. Number
   them. Attach your recommended answer to each one. Phrase each question so a
   plain yes picks your recommendation. Then stop talking and wait.

4. **Count the rounds.** The budget in §Budget is the whole cap. Round four does
   not exist; what is still open becomes a stated assumption in the to-spec.

5. **Challenge the words.** When a term contradicts the glossary, show both
   meanings and ask which is right. When a term is vague or overloaded, propose
   one canonical word. When a relationship is being described, test it with a
   concrete edge-case scenario. When the code contradicts what the user just
   said, surface both and ask which is true.

6. **Write the vocabulary as it resolves.** One term, one write, immediately.
   Shape: `**Term**: one sentence.` then `_Avoid_: other words`. Only terms
   specific to this project. No implementation detail, no scope, no decision, no
   plan text. Create `GLOSSARY.md` at the first resolved term, never before. If
   one exists, match its format and append; never restructure it.

7. **Record decisions where decisions already live.** Default: the to-spec
   `Decisions` section, one line each — `Decision: / Why:`. An ADR only when all
   three gates hold (costly to undo, puzzling to a reader without the context, a
   real choice between real alternatives) and the rung is `project`; and only
   when the repo already has `docs/adr/`. No `docs/adr/` means the decision goes
   in the to-spec `Decisions` section. Never ask about it: a local markdown file
   is not spend, and a session with zero ADRs is working as designed.

8. **Close with a quiz, then hand off.** Three questions only:
   - Does the glossary now say what you meant?
   - Are the recorded decisions the ones you would hate to argue again?
   - What is still fuzzy enough to derail the plan?

   Then write the to-spec from `templates/to-spec.md` in the same session: the
   settled words into the goal and scope, the decisions into `Decisions`,
   anything still open into `Open questions` as a stated assumption — a named
   assumption only where the unanswered question still matters, otherwise the
   round's recommendation stands. Then leave the runner what it loads by: put
   `grilled-by: grill-with-docs` on its own line under the title, when the
   marker is absent, and set the answered round's single status line to
   `status: answered`, starting at column 0. A round left `status: open` parks
   the next run again. Hand to `plan` when done. This skill never plans and
   never builds.

## Where no human can answer

A headless run and a Kanban worker have nobody on the other end. Do not wait,
do not guess, and do not proceed on assumptions for grill content: the answers
are the material the decisions are made of, and a guess here is a decision
nobody made.

- **The grill writes no spec and no plan.** It writes
  `.pipeline/grill/<slug>-round-N.md`: the numbered questions, each with a
  recommendation, plus the read list. One file per round, and that file
  carries exactly one `status: open` line — one line for the round, never a
  status line per question. `<slug>` is `dvc_run`'s job slug: lowercased,
  non-alphanumerics become `-`, cut to 30 characters. The runner reads only
  the rounds for its own `--job`; another job's rounds are noted and ignored.
- **A Kanban worker** states plainly that the interview did not finish, names
  the round file, and parks its card: `kanban_block(kind="needs_input")`.
- **`dvc_run.py` writes no round file**, and no file of its own here. It has
  no LLM in Define, so the run walks away with exit 4 (NEEDS INPUT). The
  grill's round file is what parks the run; the runner only reads it.

The park lasts until an interactive session answers the rounds and writes the
spec: the rounds carry `status: answered` and the to-spec carries
`grilled-by: grill-with-docs`. Then `dvc_run` loads that spec instead of
overwriting it; only an explicit operator flag (`--overwrite-grilled-spec`)
replaces one, and it is logged as a bypass. A grilled spec above micro-spec
stops `dvc_run` with **OUT OF SCOPE** (exit 5): run it through the interactive
pipeline.

## Done when

- The tree is worked out, or three rounds are spent and the rest is written as
  assumptions.
- Every resolved term is in `GLOSSARY.md`, and the number of terms is named in
  the handoff.
- Decisions sit in the to-spec, or in an ADR that passed all three gates.
- The quiz is answered and the next step is named.

## Never

- Write code, tests, or a plan.
- Create a glossary before a term resolves, or restructure one that exists.
- Batch glossary writes at the end. The end is where files get lost.
- Offer an ADR that fails one of the three gates, or create `docs/adr/` in a repo
  that does not have one.
- Run the interview inside `dvc_run.py` or on a Kanban worker. The grill writes
  the round file; `dvc_run.py` writes no round file — it parks the run and
  exits without writing a spec.
- Ask the user for a fact the repo, the docs, or a tool can answer.
- Exceed 3 questions in a round or 3 rounds in a session.
- Publish anything. This skill has no spend and no approval gate.

## Cognitive traps

- **"More questions means more thorough."** A question the code can answer is a
  chore you handed the user.
- **"The term is obvious."** It is obvious to you today, and ambiguous in six
  weeks.
- **"This decision matters, so it needs an ADR."** Importance is not one of the
  three gates. Relevance and reversibility are.
- **"I will write the glossary at the end."** The end never comes, and the file
  never lands. That failure is already known upstream.
- **"The interview is the deliverable."** The spec is. Stop asking when the
  answers stop changing the plan.

## Guardrails

- A human present, or a round file, `needs_input` and a stop. The grill writes
  that round file; `dvc_run.py` writes no round file and no spec. Either path
  parks — it never proceeds on a guess.
- 3 questions a round, 3 rounds a session.
- No spec, no plan, no code from this skill.
- Glossary and ADRs only in the repo being worked on — never in DVC's own repo.
- Every question carries an answer. A bare question is a fork you dodged.
