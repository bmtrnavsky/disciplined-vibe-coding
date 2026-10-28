# Changelog

## Unreleased

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
