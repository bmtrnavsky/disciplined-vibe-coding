# A coding agent for non-engineers and vibe coders

![Disciplined Vibe Coding](docs/social-preview.png)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Hermes Plugin](https://img.shields.io/badge/Hermes-Plugin-teal.svg)](https://hermes-agent.nousresearch.com/docs)
[![Version](https://img.shields.io/badge/version-0.2.0-orange.svg)](plugins/disciplined-vibe-coding/CHANGELOG.md)

> Advisory spec record (card series DVC 1/4): `dvc_run.py` hashes the spec
> at Define and prints a drift line at Verify when it moved mid-run.
> Nothing blocks; see `HOOKS.md` §2.

A lean skill pack + persona for any coding agent (built for Hermes;
portable to any agent that supports skill files). For someone who wants to
build real software — small fixes through multi-week projects — without
being a software engineer, with lead-dev discipline explained in plain
language at every step.

This isn't a shortcut around learning. It's scaffolding: the same rigor a
senior engineer would insist on (define before building, test before
shipping, verify before claiming done), applied consistently so you can lean
on it instead of having to already know it.

Sibling project:
[spec-driven-data-analysis](https://github.com/bmtrnavsky/spec-driven-data-analysis)
applies the same discipline to data work — lock the spec before touching
the data, verify every run.

## The loop

    Define (intake -> brainstorm) -> Plan (research <-> plan) -> Teardown -> Build (test-first -> execute <-> debug) -> Verify (verify -> version)

Full pipeline with gates and artifacts: `plugins/disciplined-vibe-coding/SKILL.md`
(Intake → Define → Economy gate → Plan → Teardown → Build → Verify → Commit, Wayfinder
riding along). Using another agent? See `READERS.md`.

One loop per small task, or per milestone of a larger project. Same four
words every time — the repetition is deliberate. You learn the shape of good
engineering practice by watching it applied the same way, over and over,
not by reading a lecture about it once.

## What it actually stops you from doing

- Building before anyone (you or the agent) has said out loud what "done"
  looks like.
- Shipping a destructive change with no rollback plan.
- Claiming something works because a command didn't error, rather than
  because someone actually checked the output.
- Storing payment card data instead of using a provider-hosted checkout.
- Running something autonomous (a bot, a scheduler) with no kill-switch.
- A near-miss on a metric getting quietly rounded up to "good enough."
- Moving past a failed gate without a logged bypass (who approved, what
  was red, why it was waived).
- Committing secrets: a secret scan runs before every commit.

## Stakes-aware, not one-size-fits-all

Every task gets a tier: **TOY** (learning, nothing at risk), **WORKFLOW**
(your own systems could break), or **MONEY** (payments, live trading,
anything public-facing). The tier changes what gets asked, what gets a
rollback plan, and whether a stronger model reviews the work before it's
called finished.

## Layout

    SOUL.md              the persona — how it talks, what it never compromises on
    USER.md.template      fill in your own background, environment, and preferences
    UPDATE.md             update contract: shipped paths read-only to you, user edits in user/
    scripts/update.sh     updater for manual checkouts only (catalog installs: `hermes plugins update disciplined-vibe-coding`)
    user/                 your overlay — customizations live here, never touched by updates
    scripts/selfcheck.sh  lint-only string checks (proves nothing alone)
    tests/dvc_behavioural.py  behavioural tests: runs the real runner,
                              asserts on real output (`python tests/dvc_behavioural.py`)
    HOOKS.md              optional shell hook for research-freshness nudges
    hooks/                the one hook this pack ships
    skills/               the ten skills that make up the loop
    plugins/disciplined-vibe-coding/
                          v0.2.0 pipeline overlay (stages, gates, rung rules),
                          economy ladder, to-spec/plan/wayfinder templates,
                          changelog
    READERS.md            use this pack from any agent with a skill loader
                          (or none — paste-per-stage fallback included)
    ATTRIBUTIONS.md        what this pack draws from, and where
    SOURCE-LICENSES.md    full license text and copyright lines for every source
    CATALOG.md            draft entry for the Hermes plugin catalog

## Runner status (as built, fixes A–G)

`scripts/dvc_run.py` runs Define → Verify with no human in the loop.
The builder (elephant) does the work; a blind goldfish reviewer judges
one hash-locked packet, one shot, objects only. Gates G1–G7 are automatic
checks, not prompts. Every row below is covered by
`tests/dvc_behavioural.py` (26/26 green; run it with
`python tests/dvc_behavioural.py`). `scripts/selfcheck.sh` is LINT-ONLY
— its header says so, and a green selfcheck without a green behavioural
run proves nothing.

| Built behavior | Test |
|---|---|
| End-to-end pass with stubbed reviewer | `test_end_to_end_pass_with_stubbed_reviewer` |
| Vague artifact objected to; genuine artifact passes, no trigger words | `test_vague_artifact_is_objected_to`, `test_genuine_artifact_passes_without_trigger_words` |
| Word-match judge deleted; real parser disagrees with word-match | `test_word_match_disagrees_with_real_parser` |
| Failing gate stops the run and is named | `test_failing_gate_stops_and_is_named` |
| No `--build` → NOT BUILT, exit 2 | `test_no_build_reports_not_built` |
| Build stdin closed; input-hungry build fails fast (timeout tree-kill) | `test_build_needing_input_fails_fast` |
| Undeclared spec drift fails at G7 | `test_undeclared_spec_drift_fails` |
| Build-window self-declare fails G7; outside-Build declare still passes | `test_build_rewrite_plus_self_declare_fails_at_g7`, `test_declare_outside_build_still_passes` |
| Reviewer packet carries the Define spec, not the current file | `test_packet_carries_define_spec` |
| Packet assembly rejects links escaping the workdir (symlink, hardlink, resolved path) | `test_symlink_to_outside_secret_is_rejected`, `test_hardlink_to_outside_is_rejected`, `test_escaping_resolved_path_is_rejected` |
| Same-round stop at 2, total cap, counts survive spec amendment | `test_same_round_stops_at_two`, `test_total_cap_stops_the_loop`, `test_failure_count_survives_spec_amendment` |
| Re-run over FAIL refused unless `--fresh`; history lives outside the workdir, hash-chained, with a workdir mirror | `test_rerun_over_fail_is_refused_and_cited`, `test_erased_workdir_history_still_refuses`, `test_history_lives_outside_the_workdir` |
| Minimal build env: reviewer key unreachable from builds | `test_build_env_hides_reviewer_key` |
| Reviewer stub needs `--test-mode`; stub env without the flag is ignored | `test_stub_env_without_flag_is_ignored`, `test_stub_with_flag_is_marked_stub_everywhere` |
| Every stubbed verdict marked STUB (screen, goldfish.json, call record, report) | `test_stub_with_flag_is_marked_stub_everywhere` |
| Report fields collapsed to one line; forged `Result: SUCCEEDED` cannot lead | `test_forged_job_cannot_lead_with_succeeded` |
| Mutation sentinels: disabling same-round or neutering the goldfish turns the suite red | `test_same_round_disabled_would_be_caught`, `test_never_object_would_be_caught` |

Accepted risks (not fixed, with revisit dates):

- Rework reroll: a retry resends a byte-identical packet, so a real-model
  FAIL could reroll into a PASS — accepted to 2026-11-16.
- Corrupt or deleted `runs.json` erases the FAIL record — accepted to
  2026-11-30.
- Verdict-grammar strip, workdir lock, Windows PID reuse — accepted to
  2026-12-01.
- LOW-3 (`spec_lock.py` accepts an arbitrary `--spec` path): not worth
  fixing.

## Install

**Hermes:** `SOUL.md` → your profile's `SOUL.md`; `skills/` → your profile's
skills directory (or a shared skills path referenced via
`skills.external_dirs`); `USER.md.template` → fill in and save as `USER.md`;
`hooks/` → optional, wire into `config.yaml` per `HOOKS.md` if you want the
research-freshness nudge.

**Pipeline orchestrator:** `plugins/disciplined-vibe-coding/SKILL.md` is the
entry skill that runs the whole loop; the root `__init__.py` registers it as
`disciplined-vibe-coding:disciplined-vibe-coding` alongside the ten stage
skills. Load this repo as a Hermes plugin (or point your loader at that
`SKILL.md`) so the loop has a driver — the stage skills alone have none.

**Elsewhere:** `SOUL.md` → your system prompt; the `SKILL.md` files → wherever
your tool loads skills from.

## License

MIT for everything original to this pack (`SOUL.md`, `USER.md.template`,
`HOOKS.md`, this README). The ten skills derive from several MIT-licensed
sources, and the pipeline's elephant/goldfish framing is adapted from
Google's Elephant-Goldfish Model (Apache-2.0). See `ATTRIBUTIONS.md` for
lineage and `SOURCE-LICENSES.md` for the full license text and copyright
line of every upstream project. Those notices travel with this pack per
their license terms; keep them if you fork or redistribute.
