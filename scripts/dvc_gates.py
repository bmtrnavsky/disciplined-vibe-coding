"""Automatic gates for the autonomous DVC run (card 3/4).

Every gate the pipeline claims is listed here exactly once: either with
an automatic check the run evaluates itself (a failed gate stops the run
and names the gate), or labelled ADVISORY with the plain reason it cannot
be evaluated automatically. No gate is left as prose pretending to enforce.

Gate table (id, what it means, status, check):

  G1 define/spec-locked      to-spec exists and was hashed at Define
      AUTO: .pipeline/to-spec.md exists AND .pipeline/spec.lock exists
  G2 economy/rung-declared   one rung sentence in the to-spec
      AUTO: a "rung:" line is present in the to-spec
  G3 plan/shaped             plan file exists in fixed shape
      AUTO: .pipeline/plans/*.md exists with >= 3 non-empty lines
  G4 teardown/goldfish-pass  blind review raised no standing objection
      AUTO: dvc_goldfish.run_loop outcome is PASS (card 2 stop rules)
  G5 build/proof-green       the build proof passed
      AUTO: --build command exited 0. With no --build command the run
      FAILS as NOT BUILT: a run that built nothing must never read as a
      pass. A build that timed out fails and names the timeout.
  G6 verify/done-claim-mapped  the run may only finish via Verify
      AUTO: Verify is reached only if G1-G5 all passed (asserted from the
      in-run gate record, not assumed); drift line printed either way
  G7 verify/spec-stable      the spec still matches Define, or a mid-run
      change was declared via `spec_lock.py declare`
      AUTO: current spec hash equals the Define lock, or the lock was
      re-hashed with a declaration naming who and why. Undeclared drift
      fails the run at Verify. (Fix B: a build that rewrites the spec to
      "do nothing" no longer reads as SUCCEEDED.)

Advisory (evaluated by no machine check; labelled ADVISORY in run output):

  A1 spec-drift          a DECLARED mid-run change. Advisory by design
      (SKILL.md section 5c): declaring who/why is legitimate, so it stays
      visibility, never a block. UNDECLARED drift is not advisory — it
      fails gate G7 at Verify.
  A2 step-up/blast-radius  rung steps up when blast radius grows. Needs
      judgment of what counts as irreversible or production — the run
      cannot tell a workdir scratch file from a production touch.
  A3 intake interview     direction confirmed, destructive work interviewed.
      Needs a human; an autonomous run has none, so it records assumptions
      in the spec instead.
  A4 overseer pre-step    execute-skill step screening. Advisory and
      fail-open by design (exit always 0); it nudges, never blocks.
  A5 MONEY strong-review  strong-model review recommendation on MONEY tier.
      Needs a user plus a strong model; neither is in the run.
  A6 commit secret-scan   no keys/tokens in the diff. dvc_run performs no
      Commit stage, so there is nothing to scan; enforced where commits
      happen (version skill), not here.

Build invariants called out in SKILL.md ("builder habits, not gates":
working-tree-only, test-first) are deliberately NOT gates — the pipeline
says of them "nothing fires, nothing blocks" — so they appear in neither
list above.
"""

import re
from pathlib import Path

SPEC_REL = ".pipeline/to-spec.md"
LOCK_REL = ".pipeline/spec.lock"
PLANS_REL = ".pipeline/plans"
WAYFINDER_REL = ".pipeline/wayfinder.md"

# Longest a build may run before the run kills it and fails. An
# unattended overnight run must never hang on a prompt or a stuck
# command; override with DVC_BUILD_TIMEOUT (seconds) for probes.
BUILD_TIMEOUT_S = 1800

ADVISORIES = (
    ("A1", "spec-drift",
     "a DECLARED change (lock re-hashed with who/why) is visibility; "
     "undeclared drift fails gate G7 at Verify"),
    ("A2", "step-up/blast-radius",
     "judging irreversible/production blast radius needs a human; the run cannot tell"),
    ("A3", "intake interview",
     "needs a human; the autonomous run records assumptions instead"),
    ("A4", "overseer pre-step",
     "advisory and fail-open by design; nudges, never blocks"),
    ("A5", "MONEY strong-review",
     "needs a user plus a strong model; neither is in the run"),
    ("A6", "commit secret-scan",
     "dvc_run performs no Commit stage; enforced where commits happen"),
)


def check_spec_locked(workdir):
    """G1: spec file present and lock record present."""
    workdir = Path(workdir)
    if not (workdir / SPEC_REL).is_file():
        return False, f"{SPEC_REL} missing"
    if not (workdir / LOCK_REL).is_file():
        return False, f"{LOCK_REL} missing (spec never locked at Define)"
    return True, "spec present and lock recorded"


def check_rung_declared(workdir):
    """G2: one rung sentence in the to-spec."""
    try:
        text = (Path(workdir) / SPEC_REL).read_text(encoding="utf-8")
    except OSError as exc:
        return False, f"spec unreadable ({exc})"
    if re.search(r"^rung\s*:", text, re.MULTILINE | re.IGNORECASE):
        return True, "rung sentence declared in to-spec"
    return False, 'no "rung:" sentence in to-spec'


def check_plan_shaped(workdir):
    """G3: a plan file exists with at least 3 non-empty lines."""
    plans = sorted((Path(workdir) / PLANS_REL).glob("*.md"))
    if not plans:
        return False, f"no plan file in {PLANS_REL}/"
    for plan in plans:
        try:
            lines = [ln for ln in plan.read_text(encoding="utf-8").splitlines()
                     if ln.strip()]
        except OSError:
            continue
        if len(lines) >= 3:
            return True, f"{plan.name}: {len(lines)} non-empty lines"
    return False, "plan file exists but has fewer than 3 non-empty lines"


def check_build(returncode, had_command):
    """G5: build proof green. No build command is NOT BUILT (not a pass)."""
    if not had_command:
        return False, "NOT BUILT: no --build command; nothing executed"
    if returncode == "timeout":
        return False, (f"build timed out after {BUILD_TIMEOUT_S}s; "
                       "killed so an unattended run cannot hang")
    if returncode == 0:
        return True, "build command exit 0"
    return False, f"build command exit {returncode}"


def check_spec_stable(workdir, locked_hash):
    """G7: spec still matches Define, or a change was declared.

    Declared = the lock was re-hashed via `declare --by NAME --why REASON`
    (the lock carries who/when/why). Anything else that moves the spec
    mid-run — including a build that rewrites it — fails here.
    """
    workdir = Path(workdir)
    try:
        from spec_lock import sha256_file, read_lock, lock_path_for, _short
    except ImportError:  # pragma: no cover - repo layout broken
        return False, "spec lock module unavailable"
    try:
        current = sha256_file(workdir / SPEC_REL)
    except OSError as exc:
        return False, f"spec unreadable ({exc})"
    if current == locked_hash:
        return True, f"spec unchanged since Define (sha256:{_short(current)})"
    try:
        lock = read_lock(lock_path_for(workdir))
    except (OSError, ValueError):
        return False, (f"spec drift: spec changed mid-run "
                       f"(lock {_short(locked_hash)} != "
                       f"current {_short(current)}) with no declaration")
    decls = lock.get("declarations") or []
    if lock.get("sha256") == current and decls:
        last = decls[-1]
        return True, (f"spec changed mid-run but declared by "
                      f"{last.get('by')}: {last.get('why')}")
    return False, (f"spec drift: spec changed mid-run "
                   f"(lock {_short(locked_hash)} != current "
                   f"{_short(current)}) with no declaration; "
                   f"declare it via `spec_lock.py declare --by NAME "
                   f"--why REASON`")


def wayfinder_append(workdir, stage, result, reason):
    """One result line per stage exit; the audit trail gates leave behind."""
    path = Path(workdir) / WAYFINDER_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        path.write_text("# Wayfinder — dvc_run\n\n", encoding="utf-8")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(f"- {stage}: {result} — {reason}\n")


def fail_report(gate_id, name, reason, next_stage):
    """The line a failing gate stops the run with: names the gate."""
    return (f"GATE FAIL: {gate_id} {name} — {reason}. "
            f"Stopping before {next_stage}.")
