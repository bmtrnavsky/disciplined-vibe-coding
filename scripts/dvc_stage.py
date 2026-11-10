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

`check` (run by `verify`, before any done-claim) exits 1 on any of:

1. a stage in STAGES with no PASS or logged BYPASS line — a skipped stage
   cannot be told from a silent bypass, so it counts as an UNLOGGED BYPASS
   and is a pipeline defect (SKILL.md, Gate enforcement);
2. a FAIL line with no later BYPASS line for the same gate;
3. stages out of order, and in particular a Build line recorded before a
   Teardown pass — the pre-build review gate the doctrine requires.

A malformed or unknown line is a defect too: the log is an audit trail,
not advice. `bypass` requires --by and --why, so the tool itself cannot
write an unlogged bypass; not running the tool is the only silent path,
and `check` reports every stage it has no line for.
"""

import argparse
import json
import sys
import time
from pathlib import Path

STAGES = ("Define", "Economy", "Plan", "Teardown", "Build", "Verify")
LOG_REL = ".pipeline/stages.jsonl"
FORMAT = "dvc-stage-v1"


def _path(workdir):
    return Path(workdir) / LOG_REL


def _append(workdir, rec):
    path = _path(workdir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
    return rec


def log(workdir, stage_name, gate, result, reason="", by="", why=""):
    """Record one stage exit. Returns the record written."""
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

    if before is not None:
        ahead = [r["stage"] for r in records if STAGES.index(r["stage"]) >= limit]
        if ahead:
            return False, (f"{ahead[0]} is recorded while checking the stages "
                           f"before {before}; the gate was not asked before "
                           "the stage ran")

    build_at = next((i for i, r in enumerate(records) if r["stage"] == "Build"), None)
    if build_at is not None and not any(
            r["stage"] == "Teardown" and r["result"] in ("PASS", "BYPASS")
            for r in records[:build_at]):
        return False, ("pre-build gate: Build was recorded before Teardown "
                       "passed; teardown reviews spec and plan before code")

    idx = [STAGES.index(r["stage"]) for r in records]
    for a, b in zip(idx, idx[1:]):
        if b < a:
            return False, (f"stage order defect: {STAGES[b]} recorded after "
                           f"{STAGES[a]}; a stage cannot precede its gate")

    for i, r in enumerate(records):
        if r["result"] != "FAIL":
            continue
        gate = r.get("gate")
        if not any(x["result"] == "BYPASS" and x.get("gate") == gate
                   for x in records[i + 1:]):
            return False, (f"gate {gate} FAILED at {r['stage']} and no bypass "
                           "was logged; a failed gate blocks the next stage")

    passed = {r["stage"] for r in records if r["result"] in ("PASS", "BYPASS")}
    missing = [s for s in required if s not in passed]
    if missing:
        return False, ("unlogged stage(s)" + (f" before {before}" if before else "")
                       + ": " + ", ".join(missing)
                       + " — no PASS or logged bypass, so it reads as an "
                       "unlogged bypass")
    bypasses = sum(1 for r in records if r["result"] == "BYPASS")
    scope = f"before {before}" if before else "whole pipeline"
    return True, (f"{scope}: {len(required)} stage(s) passed or bypassed "
                  f"({bypasses} logged bypass(es))")


def main(argv=None):
    ap = argparse.ArgumentParser(description="DVC interactive stage-gate record")
    ap.add_argument("--workdir", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("log", help="record one stage exit")
    p.add_argument("--stage", required=True)
    p.add_argument("--gate", required=True)
    p.add_argument("--result", required=True, choices=("PASS", "FAIL"))
    p.add_argument("--reason", default="")

    p = sub.add_parser("bypass", help="record a user-approved waiver")
    p.add_argument("--stage", required=True)
    p.add_argument("--gate", required=True)
    p.add_argument("--by", required=True, help="who approved the waiver")
    p.add_argument("--why", required=True, help="why it was waived")
    p.add_argument("--reason", default="")

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
              ns.reason, getattr(ns, "by", ""), getattr(ns, "why", ""))
    print(f"{rec['result']} recorded: {rec['stage']} {rec['gate']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
