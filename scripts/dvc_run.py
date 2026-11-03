"""DVC autonomous run entry point — Define through Verify, zero human input.

One command takes a job description and drives the skeleton pipeline to
completion without stopping: no password prompt, no approval step, no
`input()` anywhere. The run ends by itself — it finishes (exit 0) or a
failed build command stops it (exit 1). It never waits for a human.

Order is Define → Plan → Build → Teardown(review) → Verify (fix A):
the goldfish reviews the build output, not a plan. A reviewer that never
sees what was built cannot review the build.

No build command means NOT BUILT (fix B): a run with no --build built
nothing, so it cannot pass — the run stops at Build with result
NOT BUILT, exit 2, and the goldfish never runs. Undeclared spec drift
at Verify fails gate G7 (fix B): a build that rewrites the spec to
"do nothing" is caught here, not waved through as SUCCEEDED. A declared
change (`spec_lock.py declare --by NAME --why REASON`) still passes.

The build can never hang on a prompt (fix B): stdin is closed
(subprocess.DEVNULL) and the command is killed after the timeout
(DVC_BUILD_TIMEOUT, default 30 min). A timed-out build fails the run.

Spec record (fix B amends the old advisory-only rule): the spec is
hashed at Define via `spec_lock.cmd_lock`, declared changes are
re-hashed with who/why, and Verify fails undeclared drift at gate G7.
Declared drift stays visibility, never a block — unless the declaration
was added during the Build window (fix E): the builder cannot declare
its own drift, so G7 fails that.

Gates (card 3): every gate the pipeline claims is evaluated by the run
itself via `dvc_gates.py` — G1 spec-locked, G2 rung-declared, G3
plan-shaped, G4 goldfish-pass, G5 proof-green, G6 done-claim-mapped,
G7 spec-stable (fix B). A failed gate stops the run and names the
gate. What no machine check can evaluate stays labelled ADVISORY in
the Verify output (A1-A6), with the plain reason why.

Report (card 4/4): every exit — success, FAILED, or NOT BUILT — writes
`.pipeline/run-report.md` via `dvc_report.py` and prints
`report: <path>` as the last line, so Brad can find what happened
without having watched. A stopped run says FAILED or NOT BUILT in
plain words, never "completed with notes".

History (fix C, hardened by fix F): every finished run appends to an
outside history file (`~/.dvc/history/<workdir-hash>.json`, hash-chained
so rewrites are detectable; `.pipeline/runs.json` keeps a mirror copy),
and the report cites all runs and names the history path. A
second run over a FAILED run refuses to start -- it names the prior
failure and exits 3 -- unless `--fresh` is passed. A crash writes a
FAILED report instead of leaving the previous run's report on disk.

Usage:
    python scripts/dvc_run.py --job "one-line job description"
    python scripts/dvc_run.py --job "..." --workdir PATH --build "make test"
    python scripts/dvc_run.py --job "..." --workdir PATH --fresh
"""

import argparse
import os
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


def _lock_decl_keys(workdir):
    """Declaration identities recorded before the Build window.

    G7 treats any declaration NOT in this pre-Build set as added during
    Build — the builder declaring its own drift (fix E). Tuple of
    (old, new) hash pairs, never raising: an unreadable lock just means
    an empty pre-Build set.
    """
    try:
        lock = spec_lock.read_lock(spec_lock.lock_path_for(workdir))
    except Exception:
        return ()
    decls = lock.get("declarations") or []
    keys = []
    for d in decls:
        if isinstance(d, dict):
            keys.append((d.get("old"), d.get("new")))
        else:
            keys.append((None, None))
    return tuple(keys)


def _define_spec_bytes(workdir):
    """Spec bytes as locked at Define; None when unreadable."""
    try:
        return (Path(workdir) / DEFAULT_SPEC).read_bytes()
    except OSError:
        return None


def cmd_teardown_review(workdir, run_id, define_spec):
    # Goldfish (fix A): the reviewer assembles a hash-locked packet of
    # spec + plan + BUILD OUTPUT and reviews it with one model call per
    # iteration (SDDA-shaped). It runs AFTER Build, because a reviewer
    # that never sees what was built cannot review the build. Rework =
    # new build output on disk; the loop never touches the spec.
    # The packet uses the spec as locked at Define (fix E), never the
    # current file: a build that hollowed the spec gets judged against
    # the real one.
    stage("Teardown")

    def elephant_respond(round_name, objections):  # noqa: ARG001
        return ("rework recorded as new build output on disk; "
                "spec untouched")

    state = dvc_goldfish.run_loop(workdir, elephant_respond, run_id,
                                  define_spec=define_spec)
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


def _build_timeout():
    """Seconds before the build is killed. DVC_BUILD_TIMEOUT overrides."""
    try:
        return max(1, int(os.environ.get("DVC_BUILD_TIMEOUT", "") or
                          dvc_gates.BUILD_TIMEOUT_S))
    except ValueError:
        return dvc_gates.BUILD_TIMEOUT_S


def _kill_tree(proc):
    """Kill the build and anything it spawned.

    `shell=True` starts a shell with the real command as its child; on a
    timeout killing only the shell leaves the grandchild holding the
    pipes open, and the run waits anyway. So the whole tree dies:
    taskkill /T on Windows, killpg on POSIX.
    """
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           capture_output=True, timeout=30)
        else:
            os.killpg(proc.pid, 15)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def cmd_build(workdir, build_cmd):
    stage("Build")
    timeout = _build_timeout()
    if not build_cmd:
        # NOT BUILT (fix B): the "skeleton" run built nothing, so it
        # stops here. Returning a sentinel the gate refuses keeps the
        # "no builder in that path" case from ever reading as a pass.
        print("build: no --build command; NOT BUILT, stopping before "
              "Teardown(review)", flush=True)
        return "not-built"
    # Popen (not run): on timeout the tree must die before communicate()
    # returns, or a grandchild holding the pipes keeps the run waiting.
    new_session = os.name != "nt"
    flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) \
        if os.name == "nt" else 0
    proc = subprocess.Popen(build_cmd, shell=True, cwd=workdir,
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            start_new_session=new_session,
                            creationflags=flags)
    try:
        # stdin closed (fix B): a build asking for input gets EOF, never
        # an overnight hang. The timeout kills a stuck command instead of
        # waiting for morning.
        out, err = proc.communicate(timeout=timeout)
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        try:
            out, err = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            out, err = "", ""
        (workdir / "build-log.txt").write_text(
            f"$ {build_cmd}\nexit: timeout after {timeout}s\n"
            f"--- stdout ---\n{out or ''}"
            f"--- stderr ---\n{err or ''}", encoding="utf-8")
        print(f"build: TIMED OUT after {timeout}s; killed — failing the "
              f"run (DVC_BUILD_TIMEOUT={timeout})", flush=True)
        return "timeout"
    print(out, end="", flush=True)
    print(err, end="", file=sys.stderr, flush=True)
    print(f"build: exit {rc}", flush=True)
    # Execution evidence the reviewer can see: the packet carries the
    # build output, so the command and its captured output are recorded
    # as a workdir file (a reviewer that never sees what was built, or
    # that it ran at all, cannot review the build).
    (workdir / "build-log.txt").write_text(
        f"$ {build_cmd}\nexit: {rc}\n"
        f"--- stdout ---\n{out}"
        f"--- stderr ---\n{err}",
        encoding="utf-8",
    )
    return rc


def cmd_verify(workdir, rec, locked_hash, gates_passed, build_decls=()):
    # G6 done-claim-mapped: Verify is reached only because every earlier
    # gate passed. The caller asserts this from the in-run record; Verify
    # re-states it so a reader can see the mapping without trusting flow.
    # G7 spec-stable (fix B): undeclared drift FAILS the run here. A
    # build that rewrote the spec to "do nothing" is caught by this
    # gate — Verify returns False and the caller reports FAILED.
    # Fix E: a declaration added during the Build window fails too —
    # build_decls holds the pre-Build declaration keys, so G7 can tell
    # a legitimate mid-run amendment from the builder declaring itself.
    stage("Verify")
    gate_or_stop(workdir, rec, "G6", "verify/done-claim-mapped",
                 gates_passed,
                 "Define, Plan, Build, Teardown all passed; this Verify maps to them"
                 if gates_passed else
                 "Verify reached with an earlier gate unpassed",
                 "run end", record=False)
    if not gates_passed:
        # Unreachable through main() — earlier stops return first — but a
        # caller that bypasses the chain must still be named, not trusted.
        return False
    for line in advisory_lines():
        print(line, flush=True)
    ok, why = dvc_gates.check_spec_stable(workdir, locked_hash, build_decls)
    gate_or_stop(workdir, rec, "G7", "verify/spec-stable", ok, why,
                 "run end")
    if ok:
        print(f"spec stable: {why}", flush=True)
        return True
    print(f"spec drift: {why}", flush=True)
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(description="DVC autonomous run (no input)")
    ap.add_argument("--job", required=True, help="one-line job description")
    ap.add_argument("--workdir", default=".", help="build workdir")
    ap.add_argument("--build", default="", help="optional build command")
    ap.add_argument("--fresh", action="store_true",
                    help="start a new run even over a FAILED one; "
                         "the new run cites it in the history")
    ns = ap.parse_args(argv)

    workdir = Path(ns.workdir)
    t0 = time.time()
    # Refuse to start over a FAILED run (fix C): retrying with tweaked
    # text until green must not erase the failure from the record.
    if not ns.fresh:
        prior = dvc_report.last_failed_run(workdir)
        if prior is not None:
            print(dvc_report.refusal_text(prior), flush=True)
            print(f"prior report: {workdir / dvc_report.REPORT_REL}",
                  flush=True)
            return 3
    rec = dvc_report.new_record(ns.job)
    rec["advisories"] = dvc_gates.ADVISORIES
    rec["build_cmd"] = ns.build
    print(f"dvc_run: job={ns.job!r} workdir={workdir}", flush=True)
    try:
        return _run(ns, workdir, rec, t0)
    except Exception as exc:
        # A crash must not leave the previous run's report on disk as
        # the newest: write FAILED now, naming the crash.
        rec["stop"] = {
            "result": "FAILED",
            "sentence": (f"The run crashed before it could finish ({exc}); "
                         "nothing after this point ran.")}
        print(f"CRASH: {exc}; writing a FAILED report.", flush=True)
        return finish(workdir, rec, 1)


def _run(ns, workdir, rec, t0):
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
    # Fix E: snapshot before Build. The declaration keys recorded here
    # are the only ones G7 counts as legitimate; anything added while
    # the builder holds the workdir is the builder declaring itself.
    # The Define spec bytes travel to the reviewer for the same reason:
    # the packet judges the locked spec, never the hollowed file.
    pre_decls = _lock_decl_keys(workdir)
    define_spec = _define_spec_bytes(workdir)
    rc = cmd_build(workdir, ns.build)
    rec["build_rc"] = rc
    # The Build window delta: declarations the builder added while it
    # held the workdir. G7 fails on any of these; a declaration from
    # outside this window stays a pass.
    build_window = tuple(k for k in _lock_decl_keys(workdir)
                         if k not in set(pre_decls))
    if rc == "not-built":
        # NOT BUILT (fix B): no builder in this path, so nothing may
        # pass. Exit 2 (not 1) so it never reads as a build failure
        # either — it is the absence of a build. The goldfish never runs.
        gate_or_stop(workdir, rec, "G5", "build/proof-green", False,
                     "NOT BUILT: no --build command; nothing executed",
                     "Teardown(review)")
        rec["stop"] = {
            "result": "NOT BUILT",
            "sentence": ("The run built nothing: no --build command was "
                         "given, so no builder ran. It stopped at Build "
                         "before the goldfish review.")}
        print("STOP: NOT BUILT — no --build command; run ends here.",
              flush=True)
        return finish(workdir, rec, 2)
    if rc == "timeout":
        gate_or_stop(workdir, rec, "G5", "build/proof-green", False,
                     f"build timed out after {_build_timeout()}s; killed "
                     "so an unattended run cannot hang",
                     "Teardown(review)")
        rec["stop"] = {
            "result": "FAILED",
            "sentence": (f"The run failed at Build: the build command "
                         f"timed out after {_build_timeout()}s and was "
                         f"killed. It stopped before the goldfish review.")}
        print("STOP: build timed out; run ends here.", flush=True)
        return finish(workdir, rec, 1)
    ok, why = dvc_gates.check_build(rc, bool(ns.build))
    if not gate_or_stop(workdir, rec, "G5", "build/proof-green",
                        ok, why, "Teardown(review)"):
        rec["stop"] = {"result": "FAILED",
                       "sentence": "The run failed at Build: the build "
                                   f"command exited {rc}. "
                                   "It stopped before the goldfish review."}
        print("STOP: build command failed; run ends here.", flush=True)
        return finish(workdir, rec, 1)
    state = cmd_teardown_review(workdir, run_id, define_spec)
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
    if not cmd_verify(workdir, rec, locked_hash, True, build_window):
        # G7 spec-stable (fix B): undeclared drift — e.g. a build that
        # rewrote the spec to "do nothing" — fails the run at Verify.
        # Fix E: a Build-window self-declaration fails here too.
        rec["stop"] = {"result": "FAILED",
                       "sentence": "The run failed at Verify: the spec "
                                   "moved mid-run with no legitimate "
                                   "declaration. "
                                   "It stopped at the end, not as a pass."}
        print("STOP: undeclared spec drift; run ends here as FAILED.",
              flush=True)
        return finish(workdir, rec, 1)
    rec["stop"] = {"result": "SUCCEEDED",
                   "sentence": "The run succeeded: all seven gates passed "
                               "and the goldfish raised no standing "
                               "objection."}
    print(f"[Verify] done in {time.time() - t0:.1f}s — "
          f"Define through Verify, zero human input.", flush=True)
    return finish(workdir, rec, 0)


if __name__ == "__main__":
    sys.exit(main())
