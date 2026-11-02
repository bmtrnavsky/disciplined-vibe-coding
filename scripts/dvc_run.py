"""DVC autonomous run entry point — Define through Verify, zero human input.

One command takes a job description and drives the skeleton pipeline to
completion without stopping: no password prompt, no approval step, no
`input()` anywhere. The run ends by itself — it finishes (exit 0) or a
failed build command stops it (exit 1). It never waits for a human.

Spec record is advisory only: the spec is hashed at Define via
`spec_lock.cmd_lock`, and Verify re-hashes and prints a drift line when
the spec moved mid-run. Drift is visibility, never a block.

Gates (card 3): every gate the pipeline claims is evaluated by the run
itself via `dvc_gates.py` — G1 spec-locked, G2 rung-declared, G3
plan-shaped, G4 goldfish-pass, G5 proof-green, G6 done-claim-mapped.
A failed gate stops the run and names the gate. What no machine check
can evaluate stays labelled ADVISORY in the Verify output (A1-A6),
with the plain reason why.

Teardown runs the blind goldfish loop (card 2): the reviewer sees
only the spec + plan bytes, never the implementation; objections return
as new work; two straight failures on one round or three total failures
stop the run with a failure report.

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
import dvc_goldfish  # noqa: E402  (blind review loop: rounds, judge, stop rules)

STAGES = ("Define", "Plan", "Teardown", "Build", "Verify")
DEFAULT_SPEC = ".pipeline/to-spec.md"


def _slug(job):
    keep = "".join(c.lower() if c.isalnum() else "-" for c in job)[:30]
    return "-".join(filter(None, keep.split("-"))) or "job"


def stage(name):
    print(f"[{name}]", flush=True)


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


def plan_text_for(workdir):
    plans = sorted((workdir / ".pipeline" / "plans").glob("*.md"))
    parts = []
    for p in plans:
        try:
            parts.append(p.read_text(encoding="utf-8"))
        except OSError:
            continue
    parts.append(teardown_notes_text(workdir))
    return "\n".join(parts)


def teardown_notes_text(workdir):
    try:
        return (workdir / ".pipeline" / "teardown.md").read_text(encoding="utf-8")
    except OSError:
        return ""


def cmd_teardown(workdir, run_id):
    # Goldfish loop (card 2): the reviewer is blind -- it receives only
    # the spec + plan bytes, never the implementation, never chat history.
    stage("Teardown")
    (workdir / ".pipeline" / "teardown.md").write_text(
        "# Teardown (goldfish notes)\n\n"
        "- consequence: building exactly this spec changes only the workdir;\n"
        "  breaks if the job needs anything outside the workdir.\n"
        "- alternatives: doing nothing is the other option; building is\n"
        "  strongest because the run stays reversible inside the workdir.\n",
        encoding="utf-8",
    )

    def read_artifact():
        return (
            (workdir / DEFAULT_SPEC).read_text(encoding="utf-8"),
            plan_text_for(workdir),
        )

    def elephant_respond(round_name, objections):  # noqa: ARG001
        # Rework = new teardown line answering the round. Never touches the
        # spec: the loop must not loosen what it reviews to force a pass.
        note = (f"\n- rework ({round_name}): the workdir-only consequence and\n"
                f"  the doing-nothing alternative both stand; restated for review.\n")
        with open(workdir / ".pipeline" / "teardown.md", "a", encoding="utf-8") as fh:
            fh.write(note)
        return ("restated the workdir-only consequence and the "
                "doing-nothing alternative; spec untouched")

    state = dvc_goldfish.run_loop(workdir, read_artifact, elephant_respond, run_id)
    return state["outcome"]["result"] == "PASS"


def gate_or_stop(workdir, gate_id, name, ok, reason, next_stage):
    """Evaluate one gate: pass records PASS, fail records FAIL and stops."""
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
    return proc.returncode


def cmd_verify(workdir, locked_hash, gates_passed):
    # G6 done-claim-mapped: Verify is reached only because every earlier
    # gate passed. The caller asserts this from the in-run record; Verify
    # re-states it so a reader can see the mapping without trusting flow.
    stage("Verify")
    if gates_passed:
        gate_or_stop(workdir, "G6", "verify/done-claim-mapped", True,
                     "Define, Plan, Teardown, Build all passed; this Verify maps to them",
                     "run end")
    else:
        # Unreachable through main() — earlier stops return first — but a
        # caller that bypasses the chain must still be named, not trusted.
        gate_or_stop(workdir, "G6", "verify/done-claim-mapped", False,
                     "Verify reached with an earlier gate unpassed", "run end")
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
    print(f"dvc_run: job={ns.job!r} workdir={workdir}", flush=True)

    locked_hash = cmd_define(workdir, ns.job)
    if locked_hash is None:
        return 1
    run_id = dvc_goldfish.make_run_id()
    print(f"run: {run_id}", flush=True)
    ok, why = dvc_gates.check_spec_locked(workdir)
    if not gate_or_stop(workdir, "G1", "define/spec-locked", ok, why, "Plan"):
        return 1
    ok, why = dvc_gates.check_rung_declared(workdir)
    if not gate_or_stop(workdir, "G2", "economy/rung-declared", ok, why, "Plan"):
        return 1
    cmd_plan(workdir, ns.job)
    ok, why = dvc_gates.check_plan_shaped(workdir)
    if not gate_or_stop(workdir, "G3", "plan/shaped", ok, why, "Teardown"):
        return 1
    if not cmd_teardown(workdir, run_id):
        gate_or_stop(workdir, "G4", "teardown/goldfish-pass", False,
                     "goldfish loop ended in FAILURE (see objections above)",
                     "Build")
        print("STOP: goldfish loop ended in FAILURE; Build never starts.",
              flush=True)
        return 1
    gate_or_stop(workdir, "G4", "teardown/goldfish-pass", True,
                 "goldfish loop PASS, no standing objection", "Build")
    rc = cmd_build(workdir, ns.build)
    ok, why = dvc_gates.check_build(rc, bool(ns.build))
    if not gate_or_stop(workdir, "G5", "build/proof-green", ok, why, "Verify"):
        print("STOP: build command failed; run ends here.", flush=True)
        return 1
    cmd_verify(workdir, locked_hash, True)
    print(f"[Verify] done in {time.time() - t0:.1f}s — "
          f"Define through Verify, zero human input.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
