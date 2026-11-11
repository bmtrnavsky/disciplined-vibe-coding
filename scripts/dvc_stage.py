"""Stage-gate record for interactive DVC sessions (M1 pre-build gate, M2).

The skills say a failed gate blocks the next stage. In an interactive
session nothing enforced that: the gate list was prose. This makes the
sequence a record a machine can check.

    python scripts/dvc_stage.py --workdir . log --stage Plan --gate G3 \
        --result PASS --reason "plan file is in writing-plan shape"
    python scripts/dvc_stage.py --workdir . bypass --stage Teardown \
        --gate G4 --by Brad --why "small reversible change, review skipped"
    python scripts/dvc_stage.py --workdir . check            # whole pipeline
    python scripts/dvc_stage.py --workdir . check --before Build

`check` (run by `verify`, before any done-claim) reads the log as a sequence
of loops, one per Define-to-Verify pass, and exits 1 on any of:

1. a stage in STAGES with no PASS or logged BYPASS line in its loop — a
   skipped stage cannot be told from a silent bypass, so it counts as an
   UNLOGGED BYPASS and is a pipeline defect (SKILL.md, Gate enforcement);
2. a FAIL line that the same gate at the same stage never clears with a
   later PASS (the fix) or BYPASS (the waiver);
3. a step backward that is not rework: rework may step back only right after
   a FAIL, and a new loop starts with Define right after a Verify pass;
4. a Build with no Teardown PASS or BYPASS since the last Define, Economy or
   Plan record — the pre-build review gate the doctrine requires, so a
   re-plan needs a fresh teardown.

Every PASS is still self-attested: `check` proves a record was written, not
that the review behind it was good.

A malformed or unknown line is a defect too: the log is an audit trail,
not advice. `bypass` requires --by and --why, so the tool itself cannot
write an unlogged bypass; not running the tool is the only silent path,
and `check` reports every stage it has no line for.
"""

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

STAGES = ("Define", "Economy", "Plan", "Teardown", "Build", "Verify")
SPEC_OR_PLAN = ("Define", "Economy", "Plan")
LOG_REL = ".pipeline/stages.jsonl"
FORMAT = "dvc-stage-v1"

# The plan digest leaves out exactly two kinds of bookkeeping: the Status
# line and the card id published on a ticket heading. Both are strictly
# patterned, so any other edit still changes the digest.
PLAN_STATUS_RE = re.compile(r"^Status:[ \t]*(?:DRAFT|APPROVED)[ \t]*(?:\n|$)",
                            re.MULTILINE)
PLAN_CARD_RE = re.compile(
    r"^(###[ \t]+T\d+\b.*?)[ \t]+(?:—|--)[ \t]+card:[ \t]*[A-Za-z0-9_-]+[ \t]*$",
    re.MULTILINE)


def plan_digest(path):
    """sha256 of a plan file with its Status line and card ids left out."""
    # read_text normalises CRLF to LF, so line endings cannot move the digest.
    text = Path(path).read_text(encoding="utf-8")
    text = PLAN_CARD_RE.sub(r"\1", text)
    text = PLAN_STATUS_RE.sub("", text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _ix(rec):
    return STAGES.index(rec["stage"])


def _path(workdir):
    return Path(workdir) / LOG_REL


def _append(workdir, rec):
    path = _path(workdir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
    return rec


def log(workdir, stage_name, gate, result, reason="", by="", why="", plan=None):
    """Record one stage exit. Returns the record written.

    plan= binds the record to a plan file's digest, which is how a Teardown
    pass proves it reviewed this plan body (to-tickets check reads it).
    """
    if stage_name not in STAGES:
        raise SystemExit(f"unknown stage {stage_name!r}; one of {', '.join(STAGES)}")
    if result not in ("PASS", "FAIL", "BYPASS"):
        raise SystemExit(f"unknown result {result!r}; PASS, FAIL or BYPASS")
    if result == "BYPASS" and not (by.strip() and why.strip()):
        raise SystemExit("a bypass needs --by and --why: an unlogged bypass is a "
                         "pipeline defect")
    rec = {"format": FORMAT, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "stage": stage_name, "gate": gate, "result": result,
           "reason": reason}
    if by or why:
        rec["by"], rec["why"] = by, why
    if plan:
        p = Path(plan)
        p = p if p.is_absolute() else Path(workdir) / p
        if not p.is_file():
            raise SystemExit(f"plan not found: {p}")
        rec["plan"] = p.name
        rec["plan_digest"] = plan_digest(p)
    return _append(workdir, rec)


def _read(workdir):
    path = _path(workdir)
    if not path.is_file():
        return None
    records = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except ValueError as exc:
            return False, f"stage log line {n} is not JSON ({exc}); the log is not advisory"
        if not isinstance(rec, dict) or rec.get("stage") not in STAGES:
            return False, f"stage log line {n} names no real stage: {line.strip()[:60]}"
        records.append(rec)
    return records, None


def _loops(records):
    """Split the log into Define-to-Verify loops. Each loop is a list."""
    loops = [[]]
    for rec in records:
        prev = loops[-1][-1] if loops[-1] else None
        if (prev is not None and rec["stage"] == "Define"
                and prev["stage"] == "Verify"
                and prev.get("result") in ("PASS", "BYPASS")):
            loops.append([])
        loops[-1].append(rec)
    return loops


def _check_loop(loop, required, limit=None, before=None):
    """Return (ok, why) for one loop. The rule order is deliberate."""
    if limit is not None:
        fails = [i for i, r in enumerate(loop) if r.get("result") == "FAIL"]
        tail = loop[fails[-1] + 1:] if fails else loop
        ahead = [r["stage"] for r in tail if _ix(r) >= limit]
        if ahead:
            return False, (f"{ahead[0]} is recorded while checking the stages "
                           f"before {before}; the gate was not asked before "
                           "the stage ran")

    for i, r in enumerate(loop):
        if r["stage"] != "Build":
            continue
        j = next((k for k in range(i - 1, -1, -1)
                  if loop[k]["stage"] in SPEC_OR_PLAN), -1)
        if not any(loop[k]["stage"] == "Teardown"
                   and loop[k].get("result") in ("PASS", "BYPASS")
                   for k in range(j + 1, i)):
            return False, ("pre-build gate: Build was recorded with no Teardown "
                           "pass since the last Define/Economy/Plan record; "
                           "teardown reviews spec and plan before code")

    for k in range(1, len(loop)):
        if _ix(loop[k]) < _ix(loop[k - 1]) and loop[k - 1].get("result") != "FAIL":
            return False, (f"stage order defect: {loop[k]['stage']} recorded "
                           f"after {loop[k - 1]['stage']} with no failed gate "
                           "before it; rework may step back only right after a "
                           "FAIL, and a new loop starts with Define after a "
                           "Verify pass")

    for i, r in enumerate(loop):
        if r.get("result") != "FAIL":
            continue
        if limit is not None and _ix(r) >= limit:
            continue
        gate = r.get("gate")
        if not any(x.get("gate") == gate and x.get("stage") == r["stage"]
                   and x.get("result") in ("PASS", "BYPASS")
                   for x in loop[i + 1:]):
            return False, (f"gate {gate} FAILED at {r['stage']} and no later "
                           f"PASS at {r['stage']}; a failed gate blocks the "
                           "next stage")

    passed = {r["stage"] for r in loop if r.get("result") in ("PASS", "BYPASS")}
    missing = [s for s in required if s not in passed]
    if missing:
        return False, ("unlogged stage(s)" + (f" before {before}" if before else "")
                       + ": " + ", ".join(missing)
                       + " — no PASS or logged bypass, so it reads as an "
                       "unlogged bypass")
    return True, None


def check(workdir, before=None):
    """Return (ok, one-line reason). The caller prints and maps the exit code.

    before=STAGE checks only the stages that must be done before that one,
    which is how a stage exit asks "may I advance?" (execute runs
    `check --before Build`). No `before` checks the whole pipeline, which
    is what `verify` runs.
    """
    if before is not None and before not in STAGES:
        raise SystemExit(f"unknown stage {before!r}; one of {', '.join(STAGES)}")
    limit = STAGES.index(before) if before else len(STAGES)
    required = STAGES[:limit]

    read = _read(workdir)
    if read is None:
        return False, (f"no stage log ({LOG_REL}): every stage is unlogged, "
                       "which counts as an unlogged bypass")
    records, bad = read
    if bad:
        return False, bad
    if not records:
        return False, "stage log is empty: every stage is unlogged"

    loops = _loops(records)
    n = len(loops)
    for num, loop in enumerate(loops[:-1], 1):
        ok, why = _check_loop(loop, STAGES)
        if not ok:
            return False, f"loop {num} of {n}: {why}"
    ok, why = _check_loop(loops[-1], required, limit if before else None, before)
    if not ok:
        return False, (f"loop {n} of {n}: {why}" if n > 1 else why)

    bypasses = sum(1 for r in records if r.get("result") == "BYPASS")
    scope = f"before {before}" if before else "whole pipeline"
    return True, (f"{scope}: {len(required)} stage(s) passed or bypassed "
                  f"({bypasses} logged bypass(es)); {n} loop(s)")


def teardown_for_plan(workdir, plan_path):
    """Return (ok, why): was a Teardown pass recorded against this plan body?

    It proves the pass was logged on this exact plan (digest match), not that
    the review behind it was good. Only the newest loop counts: an earlier
    loop's teardown belongs to the previous milestone.
    """
    read = _read(workdir)
    if read is None:
        return False, "no stage log: teardown was never recorded"
    records, bad = read
    if bad:
        return False, bad

    last_td = None
    for r in _loops(records)[-1]:
        if r["stage"] in SPEC_OR_PLAN:
            last_td = None
        elif r["stage"] == "Teardown":
            last_td = r if r.get("result") in ("PASS", "BYPASS") else None
    if last_td is None:
        return False, ("no Teardown pass since the last Define/Economy/Plan "
                       "record in the current loop, or the latest Teardown "
                       "record is a FAIL")
    if not last_td.get("plan_digest"):
        return False, ("the Teardown pass carries no plan digest; log it with "
                       "--plan <plan file>")
    d = plan_digest(plan_path)
    if last_td["plan_digest"] != d:
        return False, ("plan changed since Teardown passed; re-run teardown "
                       "and log it with --plan")
    return True, f"teardown {last_td['result']} on this plan (digest {d[:12]})"


def main(argv=None):
    ap = argparse.ArgumentParser(description="DVC interactive stage-gate record")
    ap.add_argument("--workdir", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("log", help="record one stage exit")
    p.add_argument("--stage", required=True)
    p.add_argument("--gate", required=True)
    p.add_argument("--result", required=True, choices=("PASS", "FAIL"))
    p.add_argument("--reason", default="")
    p.add_argument("--plan", default=None,
                   help="bind this record to a plan file's digest")

    p = sub.add_parser("bypass", help="record a user-approved waiver")
    p.add_argument("--stage", required=True)
    p.add_argument("--gate", required=True)
    p.add_argument("--by", required=True, help="who approved the waiver")
    p.add_argument("--why", required=True, help="why it was waived")
    p.add_argument("--reason", default="")
    p.add_argument("--plan", default=None,
                   help="bind this record to a plan file's digest")

    p = sub.add_parser("check", help="fail on a skipped, failed or out-of-order stage")
    p.add_argument("--before", default=None,
                   help="check only the stages that must pass before this one")

    ns = ap.parse_args(argv)
    if ns.cmd == "check":
        ok, why = check(ns.workdir, ns.before)
        print(f"{'stage gates: OK' if ok else 'STAGE GATE DEFECT'}: {why}",
              flush=True)
        return 0 if ok else 1
    rec = log(ns.workdir, ns.stage, ns.gate,
              "BYPASS" if ns.cmd == "bypass" else ns.result,
              ns.reason, getattr(ns, "by", ""), getattr(ns, "why", ""),
              ns.plan)
    print(f"{rec['result']} recorded: {rec['stage']} {rec['gate']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
