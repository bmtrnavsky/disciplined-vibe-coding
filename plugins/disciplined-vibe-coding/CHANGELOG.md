# Changelog

## 0.3.3 - 2026-11-11

The gates now tell the truth about what they prove, and every request gets a
verdict before it is interviewed. Shipped in a09b940 (gates, runner, skill
text) and eb2858d (triage). Covered by `tests/dvc_behavioural.py` (88/88);
`scripts/selfcheck.sh` passes 56/56 but is lint only and proves nothing on its
own.

Two changes bite on a workdir that already exists. An old grilled spec with no
`grilled-by: grill-with-docs` line is no longer recognised, so Define
overwrites it — the old detector (a round file newer than the runner's stamp)
missed every interactive grill, so that spec was never protected. And an old
grill round file with no `status:` line now reads as open, so the run stops at
Define with NEEDS INPUT (exit 4) until the round is answered or removed.

- Added: `triage` — one verdict per ask, written down, before any interview.
  `proceed` writes the brief; `already built` names where the behavior lives
  and is never filed as a rejection; `out of scope` appends the request to
  `.out-of-scope/<concept>.md`; `needs info` writes the question file. A
  deferral is not a verdict and leaves no file behind. It fires at micro-spec
  and above on a request for work with no verdict yet, and refuses on the
  one-liner rung, on asks that are questions or reviews, on work already
  approved and in flight, and on asks it already triaged this session.
- Changed: `intake` step 1 hands to `triage` at micro-spec and above, before
  the interview; the verdict comes back, then the interview runs.

- Fixed: grill trace (N3) — the mtime guess is deleted. The spec carries
  `grilled-by: grill-with-docs`; each round carries `status: open` or
  `status: answered`, and a round with no status line fails closed as open. An
  open round, or answered rounds with no grilled spec on disk, stops at Define
  with NEEDS INPUT (exit 4): no spec written, no plan, nothing built, and
  `--overwrite-grilled-spec` does not override it. Exit codes 0–5 are now
  documented in `dvc_run.py`.
- Fixed: grill skill honesty (N4) — `grill-with-docs` no longer claims
  `dvc_run` runs the interview. Headless stays a do-not-fire condition (a
  Kanban worker parks and blocks); the runner's honest half is honouring a
  parked grill, which N3 implements. A contract test holds the skill text to
  the code.
- Fixed: runner ceiling (N8) — the runner declares one-liner and micro-spec as
  its scope. A spec above it stops with OUT OF SCOPE (exit 5) before any gate,
  plan or build, and the spec is kept as written. This is a run result, not a
  gate; the gate list stays G1–G7.
- Fixed: G1 job line (N1) — G1 parses the first `Job:` line and compares it
  whitespace-normalised instead of matching a substring, and a missing line
  says so instead of "swapped or hollow". `--job` is written to the template as
  one line, so a multi-line job cannot inject `rung:` or `Result:` lines.
- Fixed: stage log loops (N2) — `dvc_stage.py check` reads the log as
  Define-to-Verify loops. A FAIL clears on a later PASS for the same gate (a
  fix) or a BYPASS (a waiver); a step back is legal only directly after a FAIL;
  every Build needs a Teardown PASS or BYPASS since the latest
  Define/Economy/Plan record, so a re-plan voids the old pass.
- Fixed: publish gate (N5) — `dvc_tickets.py check` reads the stage log as well
  as the approval: the latest Teardown PASS or BYPASS must carry the digest of
  the plan being published, and Teardown takes `--plan` to record it. An
  approval alone, a Teardown FAIL, a re-plan, or a plan body edit since
  teardown all refuse. This proves teardown was recorded on this plan, not that
  the review was good.
- Fixed: plan lifecycle (N6) — approval and teardown bind a plan digest that
  leaves out exactly two bookkeeping items: the `Status:` line (`DRAFT` or
  `APPROVED`), and `— card: <id>` on a ticket heading. Stamping APPROVED and
  writing card ids after approval no longer break the binding, so a ticketed
  plan reaches Build APPROVED with the gate green; any other body edit still
  fails. New records are `dvc-tickets-v2`; v1 records carry no digest and keep
  checking against the raw plan sha256.
- Fixed: grill rounds are per job (N14) — the runner parks only on rounds named
  for its own `--job` slug (`lowercase`, non-alphanumerics to `-`, 30 chars).
  A round filed under another job is noted and ignored, so a leftover file can
  no longer park every run in the workdir. The grill skill states the slug rule
  so an interactive session files its round where the runner looks.
- Fixed: round status lines (N16) — a round counts as answered only when it
  carries exactly one `status:` line and that line says `answered`. A second
  status line fails closed as open and the stop names how many it saw, instead
  of trusting the first one.
- Fixed: stage-loop FAIL clearing (N15) — a FAIL clears only on a later PASS or
  BYPASS for the same gate at the same stage. A PASS logged under another stage
  (Define clearing a Plan FAIL) no longer counts, and the check names the stage
  it wants. A fix logged under a different stage is now refused; that is the
  intent.
- Fixed: G3 plan shape (N7) — G3 matches section headings whole and reads their
  bodies, so "Planning microservices", "Stepsister", empty sections and
  template slots all fail, and the reason names the missing or empty section. A
  well-shaped sibling still masks a junk plan file: G3 returns on the first
  good file in `.pipeline/plans/` and that aggregation is unchanged, because
  older workdirs hold ticket files the stricter reading would fail.
- Fixed: grill skill handoff (N4) — step 8 now says where
  `grilled-by: grill-with-docs` goes (its own line under the title) and that the
  answered round's single status line must become `status: answered`, the flip
  that lets the next run past Define.

## 0.3.2 - 2026-11-10

Define gets an interview with teeth. Covered by `tests/dvc_behavioural.py`
(45/45); `scripts/selfcheck.sh` passes 56/56 but is lint only and proves
nothing on its own.

- Added (cfcbc13): `grill-with-docs` — a bounded interview that settles the
  vocabulary before a spec is written. It fires on three conditions (full-spec
  or above, an interactive session, unsettled vocabulary) without asking, and
  refuses on four (below full-spec, headless or Kanban, vocabulary settled,
  plan already approved). Each round lands under `.pipeline/grill/`; the cap
  is 3 questions a round, 3 rounds a session, 9 total.
- Changed (cfcbc13): at full-spec and above `intake` hands its questions to
  `grill-with-docs` — it is the interview's teeth at that rung — and the
  pipeline SKILL lists it as a Define skill and defers the Define budget to it.
- Fixed (cfcbc13): D6 — Define no longer overwrites a grilled spec. It loads
  and locks the grill's output instead, and `--overwrite-grilled-spec` is the
  only override, recording a BYPASS in `.pipeline/stages.jsonl`.

## 0.3.1 - 2026-11-10

Ticket-splitting lands as an opt-in skill, plus two Opus review rounds that
make the gates tell the truth. Covered by `tests/dvc_behavioural.py` (35/35);
`scripts/selfcheck.sh` passes 56/56 but is lint only and proves nothing on
its own.

- Added (b4455ba): `to-tickets` — an optional step after `plan` that cuts a
  full-spec plan into one build card per ticket with explicit `blocked by:`
  edges. Opt-in, full-spec and above only; plans that skip it are unchanged.
- Changed (e77ee1b, 88b773d): `plan` auto-fires `to-tickets` when it produces
  a full-spec plan, and publishing the ticket set is gated — the quiz is
  mandatory because publish dispatches workers, and
  `scripts/dvc_tickets.py check --tickets <ids>` is the gate that confirms
  approval was recorded. Headless runs draft under `.pipeline/tickets/` and
  stop.
- Fixed (e77ee1b): G3 grades real plan shape, so a junk ticket file FAILS and
  a real ticketed plan PASSES, instead of a word match. (Corrected in the
  Unreleased round: G3 now also matches headings whole and reads section
  bodies, so a heading prefix like "Planning microservices" no longer passes.
  It still accepts a plan when any file in `.pipeline/plans/` is well shaped,
  so a junk sibling beside a good plan stays masked.) Self-check gates stop
  claiming more than they check; the shipped `to-tickets` contradictions are
  resolved.
- Fixed (88b773d): pre-build gate — `scripts/dvc_stage.py` records a Teardown
  PASS and refuses Build ahead of it; `bypass` requires `--by` and `--why`, so
  the tool cannot write an unlogged bypass; publish requires a recorded
  approval. Six minors from the same round.

## 0.3.0 - 2026-11-02

Fixes A–G (runner hardening series, all covered by
`tests/dvc_behavioural.py`, 26/26):

- Fix A (b6668c8): SDDA-shaped real reviewer — hash-locked packet plus
  one-shot model call; the regex word-match judge is deleted.
- Fix B (75c31a0): no build is NOT BUILT (exit 2); builds run with stdin
  closed and a timeout tree-kill; undeclared spec drift fails at G7.
- Fix C (adf1718): run history — `.pipeline/runs.json` records every
  run; re-running over a FAILED latest run refuses (exit 3) unless
  `--fresh`; reports cite all runs; crashes write FAILED.
- Fix D (64841c0): real behavioural tests replacing the grep selfcheck
  (see the existing suite entry below); disabling the same-round rule
  and neutering the goldfish both make the suite FAIL.
- Fix E (2a6694c): a build cannot declare its own spec drift —
  Build-window self-declaration fails at G7 (lock-key delta
  before/after Build; only that delta fails, outside-Build declares
  still pass); the reviewer packet carries the Define spec.
- Fix F (e1146dd): workdir contents are not trusted — packet assembly
  rejects links escaping the workdir (symlink/hardlink/resolved path,
  O_NOFOLLOW open); run history lives outside the workdir, hash-chained,
  with a workdir mirror.
- Fix G (74b6ca9): runner hygiene — builds run with a minimal allowlist
  env (reviewer key unreachable); the reviewer stub needs the explicit
  `--test-mode` flag and every stubbed verdict is marked STUB on screen,
  in goldfish.json, the call record and the report; job/build text is
  collapsed to one line so a forged `Result: SUCCEEDED` cannot lead the
  report.

Added: behavioural test suite (DVC fix D) — `tests/dvc_behavioural.py`
runs the real runner (`python tests/dvc_behavioural.py`, stdlib unittest,
no new dependency) and asserts on real output: same-round stop at 2 with no
third attempt, total cap, count surviving spec amendment, re-run refusal
over a FAIL, NOT BUILT, prompt-build failing fast, undeclared drift FAIL,
named failing gate, vague artifact objected to and genuine artifact passing
(replayed recorded fix-A model calls through the real `parse_verdicts`).
Mutation-proved: disabling the same-round rule and neutering the goldfish
both make the suite FAIL. `scripts/selfcheck.sh` is now marked lint-only;
a green selfcheck without a green behavioural run proves nothing.

Added: goldfish loop in the autonomous run (card series DVC 2/4) —
`scripts/dvc_goldfish.py` runs the two micro-spec teardown rounds with a
blind reviewer (spec+plan bytes only; no approve verdict; silence = pass).
Objections return as new work; a pass resets the round. Same-round stop:
two straight failures, no third attempt. Total cap: 3 (rounds + 1) --
a converging run fails each round at most once on first sight, so the
3rd failure means cleared ground broke again. Failure counts live in
`.pipeline/goldfish.json` keyed (run_id -> round); the spec hash is
recorded per verdict, never a key, so mid-run amendments cannot reset the
count. Stub `DVC_GOLDFISH_STUB` honored only under `DVC_TEST_MODE=1`.
Covered by `selfcheck.sh`.

Changed: spec record made advisory (card series DVC 1/4) — the 8ba8aaa
`pre_tool_call` blocking hook is removed; `dvc_run.py` hashes the spec
at Define and prints a drift line at Verify. Kept: sha256/record logic
(`sha256_file`, `lock`/`check`/`declare`). Dropped: `on_pre_tool_call`,
`GATED_TOOLS`, `_workdir_from_args`, fail-closed blocking, hook
registration in `__init__.py`. Documented in `HOOKS.md` §2 and the
pipeline `SKILL.md` (§5c); covered by `selfcheck.sh`.

Fixed: gates enforced (a red gate blocks the next stage; user bypasses
logged in Wayfinder with who/what/why); teardown second failure stops
the pipeline (tried/learned/unexplained/options, wait for his call);
rung step-up rule (declare, confirm, backfill; never step down);
goldfish review hardened (spec plus linked sources only, sources stated
per round); 1.0 bar measurable (counted builds named in the changelog);
secret scan before every commit.

## 0.2.0 — 2026-10-27

Minor: teardown runs pre-build between Plan and Build (never post-build);
commit ceremony is rung-scaled (changelog at full-spec+, tags for
project-rung releases only); Wayfinder records a pass/fail gate result per
stage exit and Verify artifacts have named homes; pipeline skill registered
in `__init__.py`; every stage skill reads the economy-ladder rung;
`readcheck.sh` dependency-free (no jq) with valid JSON on all paths;
`update.sh` compares baseline-shipped vs new-shipped for conflicts and records
a shipped baseline so repeat updates compare shipped-then vs shipped-now (plus
optionally prunes files removed upstream); update contract: shipped files
read-only, user edits live in the `user/` overlay the updater never touches
(`UPDATE.md`, `scripts/update.sh`, `user/` with a template overlay example);
hook/attribution text corrected (four Hermes hook systems; MIT plus one
Apache-2.0 upstream).

## 0.1.0 — 2026-10-25

First versioned plugin. Folds five practices into the pipeline: brainstorming
intake, grill-with-docs plus to-spec Define artifact, writing-plans Plan
format, Wayfinder session tracking, economy ladder scoping gate.

Adopted resolutions: rung thresholds from reversibility plus file count plus
blast radius; to-spec lives in the workdir during builds; Wayfinder is a tiny
workdir file; 1.0 needs three real builds with zero bypasses.
