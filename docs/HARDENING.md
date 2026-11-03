# Hardening note (engineers)

What the DVC runner guarantees, what it does not, and the suite that proves
each claim. For the product overview, see [README.md](../README.md).

## Runner design

`scripts/dvc_run.py` runs Define → Verify with no human in the loop. The
builder does the work; a blind goldfish reviewer judges one hash-locked
packet, one shot, objects only. Gates G1–G7 are automatic checks, not
prompts — see `plugins/disciplined-vibe-coding/SKILL.md` and
`scripts/dvc_gates.py` for the gate table.

`scripts/selfcheck.sh` is LINT-ONLY — its header says so. A green
selfcheck without a green behavioural run proves nothing.

## Behavior-to-test table (fixes A–G)

Every row is covered by `tests/dvc_behavioural.py` (26/26 green; run it
with `python tests/dvc_behavioural.py`). Fix details live in
`plugins/disciplined-vibe-coding/CHANGELOG.md` (fixes A–G, SHAs
b6668c8/75c31a0/adf1718/64841c0/2a6694c/e1146dd/74b6ca9).

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

## Accepted risks (not fixed, with revisit dates)

- Rework reroll: a retry resends a byte-identical packet, so a real-model
  FAIL could reroll into a PASS — accepted to 2026-11-16.
- Corrupt or deleted `runs.json` erases the FAIL record — accepted to
  2026-11-30.
- Verdict-grammar strip, workdir lock, Windows PID reuse — accepted to
  2026-12-01.
- LOW-3 (`spec_lock.py` accepts an arbitrary `--spec` path): not worth
  fixing.
