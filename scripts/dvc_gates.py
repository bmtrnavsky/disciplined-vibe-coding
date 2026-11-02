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
      AUTO: --build command exited 0; with no --build command the run
      records pass-with-note "skeleton; nothing executed" (nothing to prove)
  G6 verify/done-claim-mapped  the run may only finish via Verify
      AUTO: Verify is reached only if G1-G5 all passed (asserted from the
      in-run gate record, not assumed); drift line printed either way

Advisory (evaluated by no machine check; labelled ADVISORY in run output):

  A1 spec-drift          spec changed mid-run. Advisory by design (SKILL.md
      section 5c): a legitimate change may be declared mid-run, so drift
      is visibility, never a block.
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

ADVISORIES = (
    ("A1", "spec-drift",
     "drift is visibility by design (SKILL.md 5c); a declared change is legitimate"),
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
    """G5: build proof green (or honestly skeleton)."""
    if not had_command:
        return True, "no --build command (skeleton); nothing executed"
    if returncode == 0:
        return True, "build command exit 0"
    return False, f"build command exit {returncode}"


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
