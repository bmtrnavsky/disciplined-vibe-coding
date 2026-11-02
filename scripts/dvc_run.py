"""DVC autonomous run entry point — Define through Verify, zero human input.

One command takes a job description and drives the skeleton pipeline to
completion without stopping: no password prompt, no approval step, no
`input()` anywhere. The run ends by itself — it finishes (exit 0) or a
failed build command stops it (exit 1). It never waits for a human.

Order is Define → Plan → Build → Teardown(review) → Verify (fix A):
the goldfish reviews the build output, not a plan. A reviewer that never
sees what was built cannot review the build.

Spec record is advisory only: the spec is hashed at Define via
`spec_lock.cmd_lock`, and Verify re-hashes and prints a drift line when
the spec moved mid-run. Drift is visibility, never a block.

Gates (card 3): every gate the pipeline claims is evaluated by the run
itself via `dvc_gates.py` — G1 spec-locked, G2 rung-declared, G3
plan-shaped, G4 goldfish-pass, G5 proof-green, G6 done-claim-mapped.
A failed gate stops the run and names the gate. What no machine check
can evaluate stays labelled ADVISORY in the Verify output (A1-A6),
with the plain reason why.

Report (card 4): every exit — success or stop — writes
`.pipeline/run-report.md` via `dvc_report.py` and prints
`report: <path>` as the last line, so Brad can find what happened
without having watched. A stopped run says FAILED in plain words,
never "completed with notes".

Usage:
    python scripts/dvc_run.py --job "one-line job description"
    python scripts/dvc_run.py --job "..." --workdir PATH --build "make test"
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import spec_lock  # noqa: E402  (stdlib-only sibling; hash/record logic reused)
import dvc_gates  # noqa: E402  (automatic checks for every pipeline gate)
import dvc_goldfish  # noqa: E402  (SDDA-shaped packet + one-shot review)
import dvc_report  # noqa: E402  (end-of-run report Brad reads afterwards)

STAGES = ("Define", "Plan", "Build", "Teardown", "Verify")
DEFAULT_SPEC = ".pipeline/to-spec.md"


def _slug(job):
    keep = "".join(c.lower() if c.isalnum() else "-" for c in job)[:30]
    return "-".join(filter(None, keep.split("-"))) or "job"


def stage(name):
    print(f"[{name}]", flush=True)


def finish(workdir, rec, code):
    """Write the run report and print its path; the run's last line."""
    path = dvc_report.write_report(workdir, rec)
    print(f"report: {path}", flush=True)
    return code


def cmd_define(workdir, job):
    stage("Define")
    spec_rel = DEFAULT_SPEC
    spec = workdir / spec_rel
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text(
        f"# To-spec (micro)\n\nJob: {job}\n\n"
        "rung: micro-spec, reversible single-file change inside the workdir.\n"
        "Assumptions: defaults taken, no questions asked (autonomous run).\n",
        encoding="utf-8",
    )
    rc = spec_lock.cmd_lock(str(workdir), spec_rel)
    if rc != 0:
        print("Define FAILED: could not hash spec; stopping.", flush=True)
        return None
    return spec_lock.sha256_file(spec)


def cmd_plan(workdir, job):
    stage("Plan")
    plans = workdir / ".pipeline" / "plans"
    plans.mkdir(parents=True, exist_ok=True)
    plan = plans / f"01-{_slug(job)}.md"
    plan.write_text(
        "# Plan (micro: 3 bullets)\n\n"
        "- Build exactly the to-spec, nothing more.\n"
        "- Prove it with one local check.\n"
        "- Verify against the spec; note drift, never block on it.\n",
        encoding="utf-8",
    )
    print(f"plan: {plan.relative_to(workdir).as_posix()}", flush=True)


def cmd_teardown_review(workdir, run_id):
    # Goldfish (fix A): the reviewer assembles a hash-locked packet of
    # spec + plan + BUILD OUTPUT and reviews it with one model call per
    # iteration (SDDA-shaped). It runs AFTER Build, because a reviewer
    # that never sees what was built cannot review the build. Rework =
    # new build output on disk; the loop never touches the spec.
    stage("Teardown")

    def elephant_respond(round_name, objections):  # noqa: ARG001
        return ("rework recorded as new build output on disk; "
                "spec untouched")

    state = dvc_goldfish.run_loop(workdir, elephant_respond, run_id)
    return state


def gate_or_stop(workdir, rec, gate_id, name, ok, reason, next_stage,
                 record=True):
    """Evaluate one gate: pass records PASS, fail records FAIL and stops.

    record=False prints the line without touching the report record --
    for Verify's own mapping line, which main() already recorded.
    """
    if record:
        rec["gates"].append({"id": gate_id, "name": name,
                            "outcome": "PASS" if ok else "FAIL",
                            "reason": reason})
    dvc_gates.wayfinder_append(workdir, gate_id, "PASS" if ok else "FAIL", reason)
    if ok:
        print(f"GATE PASS: {gate_id} {name} — {reason}.", flush=True)
        return True
    print(dvc_gates.fail_report(gate_id, name, reason, next_stage), flush=True)
    return False


def advisory_lines():
    return [f"ADVISORY {aid} {name}: {why}."
            for aid, name, why in dvc_gates.ADVISORIES]


def cmd_build(workdir, build_cmd):
    stage("Build")
    if not build_cmd:
        print("build: no --build command (skeleton); nothing executed", flush=True)
        return 0
    proc = subprocess.run(build_cmd, shell=True, cwd=workdir,
                          capture_output=True, text=True)
    print(proc.stdout, end="", flush=True)
    print(proc.stderr, end="", file=sys.stderr, flush=True)
    print(f"build: exit {proc.returncode}", flush=True)
    # Execution evidence the reviewer can see: the packet carries the
    # build output, so the command and its captured output are recorded
    # as a workdir file (a reviewer that never sees what was built, or
    # that it ran at all, cannot review the build).
    (workdir / "build-log.txt").write_text(
        f"$ {build_cmd}\nexit: {proc.returncode}\n"
        f"--- stdout ---\n{proc.stdout}"
        f"--- stderr ---\n{proc.stderr}",
        encoding="utf-8",
    )
    return proc.returncode


def cmd_verify(workdir, rec, locked_hash, gates_passed):
    # G6 done-claim-mapped: Verify is reached only because every earlier
    # gate passed. The caller asserts this from the in-run record; Verify
    # re-states it so a reader can see the mapping without trusting flow.
    stage("Verify")
    if gates_passed:
        gate_or_stop(workdir, rec, "G6", "verify/done-claim-mapped", True,
                     "Define, Plan, Build, Teardown all passed; this Verify maps to them",
                     "run end", record=False)
    else:
        # Unreachable through main() — earlier stops return first — but a
        # caller that bypasses the chain must still be named, not trusted.
        gate_or_stop(workdir, rec, "G6", "verify/done-claim-mapped", False,
                     "Verify reached with an earlier gate unpassed", "run end",
                     record=False)
        return
    for line in advisory_lines():
        print(line, flush=True)
    try:
        current = spec_lock.sha256_file(workdir / DEFAULT_SPEC)
    except OSError as exc:
        # A1 advisory: a missing spec is reported, never blocks the run end.
        print(f"spec drift: spec unreadable ({exc}); "
              f"lock was {spec_lock._short(locked_hash)}", flush=True)
        return
    if current != locked_hash:
        print(f"spec drift: spec changed mid-run "
              f"(lock {spec_lock._short(locked_hash)} != "
              f"current {spec_lock._short(current)})", flush=True)
    else:
        print(f"spec clean sha256:{spec_lock._short(current)}", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description="DVC autonomous run (no input)")
    ap.add_argument("--job", required=True, help="one-line job description")
    ap.add_argument("--workdir", default=".", help="build workdir")
    ap.add_argument("--build", default="", help="optional build command")
    ns = ap.parse_args(argv)

    workdir = Path(ns.workdir)
    t0 = time.time()
    rec = dvc_report.new_record(ns.job)
    rec["advisories"] = dvc_gates.ADVISORIES
    rec["build_cmd"] = ns.build
    print(f"dvc_run: job={ns.job!r} workdir={workdir}", flush=True)

    locked_hash = cmd_define(workdir, ns.job)
    if locked_hash is None:
        rec["stop"] = {"result": "FAILED",
                       "sentence": "The run failed at Define: the spec "
                                   "could not be hashed, so nothing else ran."}
        return finish(workdir, rec, 1)
    rec["locked_hash"] = locked_hash
    run_id = dvc_goldfish.make_run_id()
    rec["run_id"] = run_id
    print(f"run: {run_id}", flush=True)
    ok, why = dvc_gates.check_spec_locked(workdir)
    if not gate_or_stop(workdir, rec, "G1", "define/spec-locked",
                        ok, why, "Plan"):
        rec["stop"] = {"result": "FAILED",
                       "sentence": "The run failed at gate G1 "
                                   f"(define/spec-locked): {why}. "
                                   "It stopped before Plan."}
        return finish(workdir, rec, 1)
    ok, why = dvc_gates.check_rung_declared(workdir)
    if not gate_or_stop(workdir, rec, "G2", "economy/rung-declared",
                        ok, why, "Plan"):
        rec["stop"] = {"result": "FAILED",
                       "sentence": "The run failed at gate G2 "
                                   f"(economy/rung-declared): {why}. "
                                   "It stopped before Plan."}
        return finish(workdir, rec, 1)
    cmd_plan(workdir, ns.job)
    ok, why = dvc_gates.check_plan_shaped(workdir)
    if not gate_or_stop(workdir, rec, "G3", "plan/shaped",
                        ok, why, "Teardown"):
        rec["stop"] = {"result": "FAILED",
                       "sentence": "The run failed at gate G3 "
                                   f"(plan/shaped): {why}. "
                                   "It stopped before Teardown."}
        return finish(workdir, rec, 1)
    rc = cmd_build(workdir, ns.build)
    rec["build_rc"] = rc
    ok, why = dvc_gates.check_build(rc, bool(ns.build))
    if not gate_or_stop(workdir, rec, "G5", "build/proof-green",
                        ok, why, "Teardown(review)"):
        rec["stop"] = {"result": "FAILED",
                       "sentence": "The run failed at Build: the build "
                                   f"command exited {rc}. "
                                   "It stopped before the goldfish review."}
        print("STOP: build command failed; run ends here.", flush=True)
        return finish(workdir, rec, 1)
    state = cmd_teardown_review(workdir, run_id)
    rec["goldfish_state"] = state
    if state["outcome"]["result"] != "PASS":
        gate_or_stop(workdir, rec, "G4", "teardown/goldfish-pass", False,
                     "goldfish loop ended in FAILURE (see objections above)",
                     "Verify")
        rule = state["outcome"].get("rule", "?")
        rnd = state["outcome"].get("round", "?")
        rec["stop"] = {"result": "FAILED",
                       "sentence": "The run failed at Teardown: the goldfish "
                                   f"stopped it by the {rule} rule on round "
                                   f"'{rnd}'. It stopped before Verify."}
        print("STOP: goldfish loop ended in FAILURE; Verify never runs.",
              flush=True)
        return finish(workdir, rec, 1)
    gate_or_stop(workdir, rec, "G4", "teardown/goldfish-pass", True,
                 "goldfish loop PASS, no standing objection", "Verify")
    rec["gates"].append({"id": "G6", "name": "verify/done-claim-mapped",
                        "outcome": "PASS",
                        "reason": "Define, Plan, Build, Teardown all passed; "
                                  "this Verify maps to them"})
    cmd_verify(workdir, rec, locked_hash, True)
    rec["stop"] = {"result": "SUCCEEDED",
                   "sentence": "The run succeeded: all six gates passed "
                               "and the goldfish raised no standing "
                               "objection."}
    print(f"[Verify] done in {time.time() - t0:.1f}s — "
          f"Define through Verify, zero human input.", flush=True)
    return finish(workdir, rec, 0)


if __name__ == "__main__":
    sys.exit(main())
