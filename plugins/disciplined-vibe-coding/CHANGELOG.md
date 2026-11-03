# Changelog

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
