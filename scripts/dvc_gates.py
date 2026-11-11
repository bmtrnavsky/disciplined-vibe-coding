"""Automatic gates for the autonomous DVC run (card 3/4).

Every gate the pipeline claims is listed here exactly once: either with
an automatic check the run evaluates itself (a failed gate stops the run
and names the gate), or labelled ADVISORY with the plain reason it cannot
be evaluated automatically. No gate is left as prose pretending to enforce.

Gate table (id, what it means, status, check):

  G1 define/spec-locked      the --job input is recorded in a locked spec
      AUTO: --job is non-empty, .pipeline/to-spec.md carries that exact
      job (whitespace-normalised) on its first "Job:" line, and
      .pipeline/spec.lock still hashes the spec. Grades Define's INPUT: a
      hollow or swapped spec fails here.
  G2 economy/rung-declared   the declared rung names a real ladder rung
      AUTO: a "rung:" line naming one-liner, micro-spec, full-spec or
      project (see references/economy-ladder.md). A junk value fails.
  G3 plan/shaped             a plan file, not a list of lines
      AUTO: .pipeline/plans/*.md in the writing-plan shape (Steps /
      Files touched / Verify / Rollback headings) or the ladder's micro
      shape ("# Plan ... micro"). A ticket file or junk fails here.
  G4 teardown/goldfish-pass  blind review raised no standing objection
      AUTO: dvc_goldfish.run_loop outcome is PASS (card 2 stop rules).
      This is the POST-BUILD DRIFT REVIEW (M1), not the doctrine's
      pre-build teardown (SKILL.md section 3.5a): the packet carries the
      build output, so it can only run after Build. The pre-build gate
      is interactive (`scripts/dvc_stage.py check --before Build`).
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
      "do nothing" no longer reads as SUCCEEDED. Fix E: a declaration
      added during the Build window fails too — the builder cannot
      declare its own drift.)

Runner scope (not a gate): `check_runner_rung` compares the declared rung
to the runner's ceiling, one-liner and micro-spec. A spec above it stops
the run as OUT OF SCOPE (exit 5) before any gate, plan or build runs. It
is a run result with its own exit code, not a gate, so the gate list
above stays exhaustive.

G1-G3 are SELF-CHECKS in the autonomous runner: `cmd_define` and
`cmd_plan` write the artifacts they grade, so a wrong shape stops the run
but no builder can turn them red. They grade the run's inputs (the job
line) and the artifact shapes. G4, G5 and G7 are the gates that grade work
the run did not do.

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


RUNG_NAMES = ("one-liner", "micro-spec", "full-spec", "project")

# What dvc_run can honor: it writes a micro plan and runs only a
# post-build review, so a spec above this stops OUT OF SCOPE (exit 5).
RUNNER_RUNGS = ("one-liner", "micro-spec")

RUNG_RE = re.compile(r"^rung\s*:\s*([a-z][a-z-]*)",
                     re.MULTILINE | re.IGNORECASE)
# G1 matches the line, never a substring: "Job: abcd" must not pass --job ab.
JOB_LINE_RE = re.compile(r"^Job:[ \t]*(.*?)[ \t]*$", re.MULTILINE)


def read_rung(text):
    """The first declared rung name, lower-cased; None when absent."""
    match = RUNG_RE.search(text or "")
    return match.group(1).lower() if match else None


# The plan shapes writing-plan.md and the economy ladder allow. A ticket
# list, a spec, or junk matches neither (C3).
PLAN_SECTIONS = ("steps", "files touched", "verify", "rollback")


def check_spec_locked(workdir, job):
    """G1: the --job input is recorded in a spec the lock still covers.

    Grades Define's input, not just the file the runner wrote (C1): the
    spec must carry the very job the operator passed, and the lock must
    still hash the spec on disk. A hollow or swapped spec fails here.
    """
    workdir = Path(workdir)
    if not (job or "").strip():
        return False, "no job input: --job was empty"
    spec = workdir / SPEC_REL
    if not spec.is_file():
        return False, f"{SPEC_REL} missing"
    if not (workdir / LOCK_REL).is_file():
        return False, f"{LOCK_REL} missing (spec never locked at Define)"
    try:
        text = spec.read_text(encoding="utf-8")
    except OSError as exc:
        return False, f"spec unreadable ({exc})"
    def norm(s):
        return " ".join(s.split())

    match = JOB_LINE_RE.search(text)
    if not match or not match.group(1).strip():
        return False, ('spec has no "Job:" line, so the --job input is not '
                       "recorded in it; a spec written from "
                       "templates/to-spec.md needs \"Job: <the exact --job "
                       'text>" under its title')
    if norm(match.group(1)) != norm(job):
        return False, (f"spec Job line {match.group(1)!r} differs from "
                       f"--job {norm(job)!r} (swapped spec, or the wrong "
                       "--job)")
    try:
        from spec_lock import sha256_file, read_lock, lock_path_for
        if read_lock(lock_path_for(workdir)).get("sha256") != sha256_file(spec):
            return False, "spec no longer matches its Define lock"
    except (ImportError, OSError, ValueError) as exc:
        return False, f"spec lock unreadable ({exc})"
    return True, "job recorded in the spec and the lock still hashes it"


def check_rung_declared(workdir):
    """G2: the declared rung names a real rung on the ladder.

    In dvc_run the runner writes this sentence itself, so the check grades
    the declaration's form, never a human's choice (C2). A junk value
    ("rung: probe") fails; an absent line fails.
    """
    try:
        text = (Path(workdir) / SPEC_REL).read_text(encoding="utf-8")
    except OSError as exc:
        return False, f"spec unreadable ({exc})"
    rung = read_rung(text)
    if rung is None:
        return False, 'no "rung:" sentence in to-spec'
    if rung not in RUNG_NAMES:
        return False, (f'rung "{rung}" is not on the ladder '
                       f"({', '.join(RUNG_NAMES)})")
    return True, f"rung declared: {rung}"


def check_runner_rung(workdir):
    """Not a gate: is the declared rung within what dvc_run can honor?

    The runner writes a micro plan and runs only a post-build review, so
    a full-spec or project spec would get micro ceremony. Above the
    ceiling, `_run` stops with OUT OF SCOPE (exit 5) before any gate,
    plan or build. Junk and unreadable specs pass here: G2 names them.
    """
    try:
        text = (Path(workdir) / SPEC_REL).read_text(encoding="utf-8")
    except OSError:
        return True, "rung not graded here; G2 grades it"
    rung = read_rung(text)
    if rung not in RUNG_NAMES:
        return True, "rung not graded here; G2 grades it"
    if rung in RUNNER_RUNGS:
        return True, f"rung {rung} is within the runner's ceiling"
    return False, (f"rung {rung} is above the runner's ceiling (micro-spec): "
                   "dvc_run writes a micro plan and runs only a post-build "
                   f"review; a {rung} spec needs the interactive pipeline "
                   "(full plan, five-round pre-build teardown, plan approval)")


# A micro plan's title: "# Plan (micro)" and variants. The prefix alone is
# not a shape ("# Planning microservices" is a different plan entirely).
MICRO_HEAD_RE = re.compile(r"^plan\b.*\bmicro\b", re.IGNORECASE)
BULLET_RE = re.compile(r"^([-*]|\d+\.)\s+")


def _sections(text):
    """[(heading text, body lines)] for each heading, lower-cased, no '#'."""
    sections = []
    for ln in text.splitlines():
        if ln.lstrip().startswith("#"):
            sections.append([ln.lstrip("#").strip().lower(), []])
        elif sections:
            sections[-1][1].append(ln)
    return sections


def _body_text(line):
    """True for a section body line that carries plan content.

    Blank lines, the template's `Purpose:` prose, and its bare "-" and
    "1. ..." slots are shape, not content.
    """
    s = line.strip()
    if not s or s.lower().startswith("purpose:"):
        return False
    return bool(BULLET_RE.sub("", s).strip(" .-"))


def _bullet(line):
    """True for a bullet or numbered line that names something."""
    return bool(BULLET_RE.match(line.strip())) and _body_text(line)


def _plan_shape(text):
    """(ok, why) for the two shapes the docs allow. See PLAN_SECTIONS.

    Headings match whole, so "Planning microservices" and "Stepsister" are
    not plans; every full-shape section also needs a body line that is not
    a template slot. Which one failed is always named.
    """
    sections = _sections(text)
    found = {}
    for head, body in sections:
        for name in PLAN_SECTIONS:
            if name not in found and (head == name
                                      or head.startswith(name + " ")):
                found[name] = body
    missing = [s for s in PLAN_SECTIONS if s not in found]
    empty = [s for s in PLAN_SECTIONS
             if s in found and not any(_body_text(ln) for ln in found[s])]
    if not missing and not empty:
        return True, "full plan shape (Steps/Files touched/Verify/Rollback)"
    micro = [body for head, body in sections if MICRO_HEAD_RE.match(head)]
    if micro and any(_bullet(ln) for body in micro for ln in body):
        return True, "micro plan shape (# Plan ... micro)"
    micro_why = ("micro plan heading with no bullet steps" if micro
                 else "no micro plan heading")
    gaps = [f"missing {', '.join(missing)}"] if missing else []
    if empty:
        gaps.append(f"empty {', '.join(empty)}")
    return False, f"not a plan: {'; '.join(gaps)} ({micro_why})"


def check_plan_shaped(workdir):
    """G3: a plan file in the fixed shape, not a list of non-empty lines.

    A ticket list, a copied spec, or junk written into .pipeline/plans/
    does not satisfy "a plan exists" (C3). In dvc_run the runner writes
    the plan, so this is a self-check on its artifact shape; a builder's
    plan meets the same bar.
    """
    plans = sorted((Path(workdir) / PLANS_REL).glob("*.md"))
    if not plans:
        return False, f"no plan file in {PLANS_REL}/"
    reasons = []
    for plan in plans:
        try:
            text = plan.read_text(encoding="utf-8")
        except OSError:
            continue
        ok, why = _plan_shape(text)
        if ok:
            return True, f"{plan.name}: {why}"
        reasons.append(f"{plan.name}: {why}")
    return False, "; ".join(reasons) or "plan files unreadable"


def check_build(returncode, had_command, timeout_s=None):
    """G5: build proof green. No build command is NOT BUILT (not a pass).

    timeout_s is the effective DVC_BUILD_TIMEOUT, so the message names the
    limit that actually applied (m2), not the shipped default.
    """
    if not had_command:
        return False, "NOT BUILT: no --build command; nothing executed"
    if returncode == "timeout":
        return False, (f"build timed out after {timeout_s or BUILD_TIMEOUT_S}s; "
                       "killed so an unattended run cannot hang")
    if returncode == 0:
        return True, "build command exit 0"
    return False, f"build command exit {returncode}"


def check_spec_stable(workdir, locked_hash, build_window=()):
    """G7: spec still matches Define, or a change was declared.

    Declared = the lock was re-hashed via `declare --by NAME --why REASON`
    (the lock carries who/when/why). Anything else that moves the spec
    mid-run — including a build that rewrites it — fails here.

    A declaration added during the Build window fails too (fix E): in
    an autonomous run nobody can legitimately declare during Build, so
    a builder that rewrites the spec and self-declares is caught here,
    never waved through as SUCCEEDED. build_window holds the keys of
    the declarations added while the builder held the workdir; only
    those fail — a declaration from outside Build stays a pass.
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
        # Build-window declarations are the builder declaring its own
        # drift (fix E): any lock entry whose recorded hash pair was
        # added while the builder held the workdir fails the run. A
        # declaration from outside that window stays a pass.
        bad = [d for d in decls
               if _decl_key(d) in set(build_window)]
        if bad:
            last_bad = bad[-1]
            by = last_bad.get("by") if last_bad.get("by") else "?"
            why = last_bad.get("why") if last_bad.get("why") else "?"
            return False, (f"spec changed mid-run and was declared during "
                           f"the Build window by {by}: {why} — the builder "
                           f"cannot declare its own drift")
        last = decls[-1]
        return True, (f"spec changed mid-run but declared by "
                      f"{last.get('by')}: {last.get('why')}")
    return False, (f"spec drift: spec changed mid-run "
                   f"(lock {_short(locked_hash)} != current "
                   f"{_short(current)}) with no declaration; "
                   f"declare it via `spec_lock.py declare --by NAME "
                   f"--why REASON`")


def _decl_key(d):
    """One declaration's identity: its recorded content hash pair."""
    if not isinstance(d, dict):
        return (None, None)
    return (d.get("old"), d.get("new"))


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
