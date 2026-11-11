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

## Behavior-to-test table (fixes A–G and N1–N8)

Every row is covered by `tests/dvc_behavioural.py` (88/88 green; run it
with `python tests/dvc_behavioural.py`). Fix details live in
`plugins/disciplined-vibe-coding/CHANGELOG.md` (fixes A–G, SHAs
b6668c8/75c31a0/adf1718/64841c0/2a6694c/e1146dd/74b6ca9; the N1–N8 round
is under `## Unreleased`).

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
| Grill trace is the spec marker, not a timestamp; a grilled spec loads with no round file at all | `test_grilled_by_line_loads_without_any_round_file` |
| An open grill round stops the run at Define: exit 4, spec bytes unchanged, no Plan, report says NEEDS INPUT | `test_open_round_file_parks_the_run_before_define` |
| A round file with no `status:` line fails closed as open, and the stop names the file | `test_round_file_without_a_status_line_counts_as_open` |
| Answered rounds with no grilled spec on disk still stop the run, and the reason names `grilled-by` | `test_answered_round_with_no_grilled_spec_parks_too` |
| Answered rounds plus a grilled spec get past Define, so the stop is not sticky | `test_answered_round_with_grilled_spec_runs_past_define` |
| `--overwrite-grilled-spec` does not override an open round | `test_overwrite_flag_does_not_override_an_open_round` |
| The grill skill's claims about `dvc_run` are asserted against the runner's own text | `test_runner_half_matches_the_code` |
| Runner ceiling: full-spec stops OUT OF SCOPE before Build (no `out.txt`, no plan, G1 never runs, report says OUT OF SCOPE, a re-run is not refused) | `test_full_spec_stops_out_of_scope_before_build` |
| Project rung also stops at the ceiling | `test_project_rung_also_stops` |
| A grilled micro-spec is let through the ceiling (NOT BUILT, exit 2) | `test_grilled_micro_spec_runs` |
| A template-shaped grilled spec stops at the ceiling, not at G1 with "swapped or hollow" | `test_template_shaped_grilled_spec_stops_out_of_scope_not_g1` |
| G1 names a missing `Job:` line instead of blaming a swapped spec | `test_missing_job_line_names_itself` |
| G1 compares the `Job:` line whole: `Job: abcd` does not pass `--job ab` | `test_prefix_job_no_longer_passes` |
| A multi-line `--job` is written as one line and cannot inject a `rung:` line | `test_multiline_job_is_written_as_one_line` |
| A fix is a new PASS for the same gate at the same stage; no bypass needed | `test_fail_then_pass_clears`, `test_pass_at_wrong_stage_does_not_clear` |
| A failed Teardown, a re-plan and a second pass is a legal rework loop | `test_teardown_rework_loop` |
| A second Define after a Verify pass starts a new loop (a second milestone) | `test_two_loops` |
| A step back with no FAIL before it is an order defect | `test_rewind_without_fail_is_defect` |
| A re-plan after Build needs a fresh Teardown | `test_replan_after_build_needs_fresh_teardown` |
| A Build logged during a failed Verify is not "ahead" on the rework check | `test_before_build_during_verify_rework` |
| A defect in an earlier loop is reported, not hidden by the last loop | `test_closed_loop_defect_is_reported` |
| `dvc_stage.py check` exit codes for the loop rules | `test_cli_exit_codes` |
| Publish: approval alone does not publish; a recorded Teardown pass is required | `test_check_fails_without_teardown` |
| Publish: a Teardown pass with no plan digest refuses | `test_teardown_without_plan_digest_fails` |
| Publish: a later Teardown FAIL, or a re-plan, voids the pass | `test_failed_or_stale_teardown_fails` |
| Publish: a plan body edit after teardown refuses | `test_plan_body_edit_after_teardown_fails` |
| The plan reaches Build APPROVED with card ids written and the gate green | `test_full_lifecycle_closes` |
| Only an exact `Status: DRAFT` or `Status: APPROVED` line is bookkeeping; a longer Status line is content | `test_status_line_carrying_content_counts` |
| A body edit after approval still breaks the binding | `test_body_edit_still_breaks_binding` |
| CRLF line endings do not move the digest | `test_crlf_does_not_change_digest` |
| A pre-v2 approval record (no digest) still checks by raw plan sha256 | `test_v1_record_still_checks` |
| A grill round filed under another job's slug is noted and ignored, not a park | `test_foreign_job_round_does_not_park` |
| A round with two status lines counts as open, and the stop names the count | `test_two_status_lines_count_as_open` |
| The grill skill says where `grilled-by` goes and that the answered round flips its status line | `test_step_8_says_where_the_marker_and_the_answer_go` |
| The grill skill states the job-slug rule and that a run reads only its own rounds | `test_round_file_slug_is_the_runners_own` |
| G3 rejects prefix headings, empty sections and template slots; the runner's micro plan and a filled full plan pass | `test_prefix_heading_is_not_a_micro_plan`, `test_empty_micro_plan_heading_fails`, `test_stepsister_heading_is_not_steps`, `test_all_headings_empty_fails`, `test_template_slots_only_fail`, `test_purpose_only_section_fails`, `test_runner_micro_plan_passes`, `test_filled_full_plan_passes` |

## Accepted risks (not fixed, with revisit dates)

- Rework reroll: a retry resends a byte-identical packet, so a real-model
  FAIL could reroll into a PASS — accepted to 2026-11-16.
- Corrupt or deleted `runs.json` erases the FAIL record — accepted to
  2026-11-30.
- Verdict-grammar strip, workdir lock, Windows PID reuse — accepted to
  2026-12-01.
- LOW-3 (`spec_lock.py` accepts an arbitrary `--spec` path): not worth
  fixing.
