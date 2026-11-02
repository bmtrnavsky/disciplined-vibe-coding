"""DVC autonomous run entry point — Define through Verify, zero human input.

One command takes a job description and drives the skeleton pipeline to
completion without stopping: no password prompt, no approval step, no
`input()` anywhere. The run ends by itself — it finishes (exit 0) or a
failed build command stops it (exit 1). It never waits for a human.

Spec record is advisory only: the spec is hashed at Define via
`spec_lock.cmd_lock`, and Verify re-hashes and prints a drift line when
the spec moved mid-run. Drift is visibility, never a block.

Later cards own the rest: goldfish review loop (card 2), stop rules and
gates (card 3), run report (card 4). Teardown below is a two-line stub
until card 2 replaces it.

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
import spec_lock  # noqa: E402  (stdlib-only sibling; hash/record logic reused)

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


def cmd_teardown(workdir):
    # shortcut: stub two-pass notes; card 2 builds the real goldfish loop.
    stage("Teardown")
    (workdir / ".pipeline" / "teardown.md").write_text(
        "# Teardown (stub — card 2 owns the goldfish loop)\n\n"
        "- consequence: building exactly this spec changes only the workdir.\n"
        "- alternatives: none considered at skeleton rung.\n",
        encoding="utf-8",
    )
    print("teardown: stub passes recorded (advisory)", flush=True)


def cmd_build(workdir, build_cmd):
    stage("Build")
    if not build_cmd:
        print("build: no --build command (skeleton); nothing executed", flush=True)
        return True
    proc = subprocess.run(build_cmd, shell=True, cwd=workdir,
                           capture_output=True, text=True)
    print(proc.stdout, end="", flush=True)
    print(proc.stderr, end="", file=sys.stderr, flush=True)
    print(f"build: exit {proc.returncode}", flush=True)
    return proc.returncode == 0


def cmd_verify(workdir, locked_hash):
    stage("Verify")
    try:
        current = spec_lock.sha256_file(workdir / DEFAULT_SPEC)
    except OSError as exc:
        # Advisory: a missing spec is reported, never blocks the run end.
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
    cmd_plan(workdir, ns.job)
    cmd_teardown(workdir)
    if not cmd_build(workdir, ns.build):
        print("STOP: build command failed; run ends here.", flush=True)
        return 1
    cmd_verify(workdir, locked_hash)
    print(f"[Verify] done in {time.time() - t0:.1f}s — "
          f"Define through Verify, zero human input.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
