"""End-of-run report for the autonomous DVC run (card 4/4).

Brad is not watching while the run goes, so this file is the only thing
he sees afterwards. It answers eight questions in plain words:

1. What was built -- the job, the spec that governed it, what came out.
2. What the goldfish objected to -- every objection, quoted verbatim.
3. What the elephant changed in response to each objection.
4. How many rounds it took, and which stop rule fired (if any).
5. Which gates ran and the outcome of each (pass, fail, advisory).
6. Whether the spec moved mid-run -- when and by how much.
7. Why the run stopped, in one plain sentence.
8. Which runs came before -- every run in this workdir, oldest first.

The report never overstates: a run stopped by a stop rule says FAILED,
never "completed with notes". It is written to
`.pipeline/run-report.md` inside the workdir, and the run prints
`report: <path>` as its last line so it can be found later.
"""

import hashlib
import json
import time
from pathlib import Path

REPORT_REL = ".pipeline/run-report.md"
SPEC_REL = ".pipeline/to-spec.md"
LOCK_REL = ".pipeline/spec.lock"
PLANS_REL = ".pipeline/plans"
GOLDFISH_REL = ".pipeline/goldfish.json"
TEARDOWN_REL = ".pipeline/teardown.md"  # legacy scratch file (pre-fix-A runs only)
PACKETS_REL = ".pipeline/packets"
REVIEWS_REL = ".pipeline/reviews/goldfish"
WAYFINDER_REL = ".pipeline/wayfinder.md"
RUNS_REL = ".pipeline/runs.json"  # fix C: append-only run history
GATE_ORDER = ("G1", "G2", "G3", "G4", "G5", "G6", "G7")


def new_record(job):
    """Blank run record; dvc_run fills it in as stages complete."""
    return {
        "job": job,
        "run_id": None,
        "t0": time.time(),
        "elapsed_s": None,
        "locked_hash": None,
        "gates": [],             # dicts: id, name, outcome PASS/FAIL, reason
        "advisories": (),        # (aid, name, why); dvc_run fills from dvc_gates
        "goldfish_state": None,  # dvc_goldfish state dict, once Teardown runs
        "build_cmd": "",
        "build_rc": None,        # None = Build never ran
        "stop": {"result": "FAILED", "sentence": "The run never started."},
    }


def _short(h):
    return (h or "?")[:12]


def _sha_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rung_line(spec_text):
    for ln in spec_text.splitlines():
        if ln.strip().lower().startswith("rung:"):
            return ln.strip()
    return ""


def _section1(workdir, rec):
    lines = ["## 1. What was built", ""]
    lines.append(f"- Job: {rec['job']}")
    spec = workdir / SPEC_REL
    try:
        spec_text = spec.read_text(encoding="utf-8")
    except OSError as exc:
        spec_text = ""
        lines.append(f"- Spec: {SPEC_REL} unreadable ({exc})")
    if spec_text:
        rung = _rung_line(spec_text)
        lines.append("- Spec: " + SPEC_REL +
                     f" (locked sha256:{_short(rec['locked_hash'])})")
        lines.append(f"  Rung: {rung}" if rung else
                     "  Rung: no rung sentence in the spec")
    plans = sorted((workdir / PLANS_REL).glob("*.md"))
    if plans:
        lines.append("- Plan: " + ", ".join(p.name for p in plans) +
                     f" in {PLANS_REL}/")
    else:
        lines.append("- Plan: none written (the run stopped before Plan)")
    if rec["build_rc"] is None:
        lines.append("- Build: never ran")
    elif rec["build_rc"] == "not-built":
        lines.append("- Build: NOT BUILT -- no --build command given; "
                     "nothing executed, the goldfish never ran")
    elif rec["build_rc"] == "timeout":
        lines.append(f"- Build: `{rec['build_cmd']}` TIMED OUT and was "
                     f"killed (DVC_BUILD_TIMEOUT)")
    elif not rec["build_cmd"]:
        lines.append("- Build: no --build command (skeleton); "
                     "nothing executed")
    else:
        lines.append(f"- Build: `{rec['build_cmd']}` "
                     f"exited {rec['build_rc']}")
    made = [p for p in (SPEC_REL, LOCK_REL, GOLDFISH_REL,
                        WAYFINDER_REL)
            if (workdir / p).is_file()]
    made += [f"{PLANS_REL}/{p.name}" for p in plans]
    packets = sorted((workdir / PACKETS_REL).iterdir()) if (workdir / PACKETS_REL).is_dir() else []
    made += [f"{PACKETS_REL}/{p.name}/" for p in packets if p.is_dir()]
    calls = sorted((workdir / REVIEWS_REL).glob("call-*.json")) if (workdir / REVIEWS_REL).is_dir() else []
    made += [f"{REVIEWS_REL}/{c.name}" for c in calls]
    # The report itself: it exists by the time anyone reads this.
    made.append(REPORT_REL)
    lines.append(f"- Outputs on disk: {', '.join(made) if made else 'none'}")
    return lines


def _fail_verdicts(state):
    return [v for v in state.get("verdicts", [])
            if v.get("verdict") == "FAIL"]


def _section2(state):
    lines = ["## 2. What the goldfish objected to", ""]
    if state is None:
        lines.append("Teardown never ran, so the goldfish reviewed nothing.")
        return lines
    fails = _fail_verdicts(state)
    if not fails:
        lines.append("Nothing. The goldfish reviewed "
                     f"{len(state.get('rounds', []))} round(s) "
                     "and raised no objection.")
        return lines
    for rnd in state.get("rounds", []):
        vs = [v for v in fails if v.get("round") == rnd]
        if not vs:
            continue
        n = sum(len(v.get("objections", [])) for v in vs)
        lines.append(f"### Round '{rnd}' -- {n} objection(s)")
        lines.append("")
        for v in vs:
            for ob in v.get("objections", []):
                lines.append(f"- Review #{v.get('seq')}, quoted verbatim:")
                lines.append(f"  > {ob}")
        lines.append("")
    return lines


def _section3(state):
    lines = ["## 3. What changed in response", ""]
    if state is None:
        lines.append("Teardown never ran, so nothing changed.")
        return lines
    fails = _fail_verdicts(state)
    if not fails:
        lines.append("Nothing needed changing -- there were no objections.")
        return lines
    seen = {}
    for v in fails:
        seen.setdefault(v.get("round"), []).append(v)
    for rnd, vs in seen.items():
        for i, v in enumerate(vs, 1):
            lines.append(f"- After '{rnd}' failure {i} of {len(vs)} "
                         f"(review #{v.get('seq')}): "
                         f"{v.get('elephant_response')
                              or 'no response recorded'}")
    lines.append("- The spec itself was never touched to force a pass "
                 "(the loop forbids it).")
    return lines


def _section4(state):
    lines = ["## 4. How many rounds it took", ""]
    if state is None:
        lines.append("No rounds ran -- the run stopped before Teardown.")
        return lines
    rounds = state.get("rounds", [])
    verdicts = state.get("verdicts", [])
    passes = sum(1 for v in verdicts if v.get("verdict") == "PASS")
    fails = sum(1 for v in verdicts if v.get("verdict") == "FAIL")
    per = ", ".join(
        f"'{r}': {state.get('per_round', {}).get(r, {}).get('attempts', '?')}"
        " review(s)" for r in rounds)
    lines.append(f"- Rounds: {', '.join(rounds)} ({len(rounds)} rounds).")
    lines.append(f"- Reviews: {len(verdicts)} total "
                 f"({passes} pass(es), {fails} failure(s); {per}).")
    out = state.get("outcome") or {}
    if out.get("result") == "PASS":
        lines.append(f"- Ending: success -- all rounds passed after "
                     f"{out.get('failures_total', fails)} "
                     "objection(s) answered.")
    elif out.get("rule") == "same-round":
        lines.append(f"- Ending: stopped by the same-round rule -- "
                     f"'{out.get('round')}' failed "
                     f"{state.get('same_round_limit', 2)} times in a row, "
                     "no third attempt.")
    elif out.get("rule") == "review-error":
        lines.append("- Ending: stopped by a review error -- the packet or "
                     "provider was unusable, so the round could not pass "
                     "(fail closed, never a silent pass).")
    else:
        lines.append("- Ending: stopped by the total cap -- "
                     f"{out.get('failures_total', fails)} failures "
                     f"(cap {state.get('total_failure_cap', '?')}).")
    return lines


def _section5(rec):
    lines = ["## 5. Gates", ""]
    ran = {g["id"] for g in rec["gates"]}
    for g in rec["gates"]:
        lines.append(f"- {g['id']} {g['name']}: "
                     f"{g['outcome']} -- {g['reason']}")
    for gid in GATE_ORDER:
        if gid not in ran:
            lines.append(f"- {gid}: never ran -- the run stopped before it")
    lines.append("")
    lines.append("Advisory (no machine check can evaluate these; "
                 "they never block):")
    lines.append("")
    for aid, name, why in rec["advisories"]:
        lines.append(f"- {aid} {name}: ADVISORY -- {why}")
    return lines


def _section6(workdir, rec):
    lines = ["## 6. Did the spec move", ""]
    try:
        current = _sha_file(workdir / SPEC_REL)
    except OSError as exc:
        lines.append(f"- The spec is unreadable now ({exc}); "
                     f"lock was sha256:{_short(rec['locked_hash'])}.")
        return lines
    lines.append(f"- Lock at Define: sha256:{_short(rec['locked_hash'])}; "
                 f"now: sha256:{_short(current)}.")
    try:
        raw = (workdir / LOCK_REL).read_text(encoding="utf-8")
        decls = json.loads(raw).get("declarations", [])
    except (OSError, ValueError):
        decls = None
    if decls is None:
        lines.append("- The lock is missing or unreadable; "
                     "no declarations could be read.")
        return lines
    if current != rec["locked_hash"]:
        lines.append("- The spec moved mid-run.")
    else:
        lines.append("- The spec did not move during the run.")
    if not decls:
        lines.append("- Declarations: none recorded in the lock.")
        if current != rec["locked_hash"]:
            lines.append("- It moved without a declaration -- "
                         "no by/why was recorded.")
    else:
        lines.append(f"- Declarations: {len(decls)} recorded:")
        for d in decls:
            when = time.strftime("%Y-%m-%d %H:%M",
                                 time.localtime(d.get("at", 0)))
            lines.append(f"  - {when} by {d.get('by')}: {d.get('why')} "
                         f"(sha256:{_short(d.get('old'))} -> "
                         f"sha256:{_short(d.get('new'))})")
    return lines


def render(workdir, rec):
    """Full report text for a finished or stopped run."""
    workdir = Path(workdir)
    res = rec["stop"]["result"]
    when = time.strftime("%Y-%m-%d %H:%M", time.localtime(rec["t0"]))
    el = rec.get("elapsed_s") or 0.0
    head = [f"# Run report -- {rec['job']}", "",
            f"Result: {res}",
            rec["stop"]["sentence"],
            "",
            f"Run: {rec['run_id'] or 'never started'} - {when} - "
            f"took {el:.1f}s - workdir {workdir}",
            ""]
    parts = [head,
             _section1(workdir, rec), [""],
             _section2(rec["goldfish_state"]), [""],
             _section3(rec["goldfish_state"]), [""],
             _section4(rec["goldfish_state"]), [""],
             _section5(rec), [""],
             _section6(workdir, rec), [""],
             ["## 7. Why it stopped", "", rec["stop"]["sentence"], ""],
             [""],
             _section8_history(rec.get("history") or []), [""]]
    out = []
    for p in parts:
        out.extend(p)
    return "\n".join(out).rstrip() + "\n"


def load_history(workdir):
    """Every recorded run in this workdir, oldest first. Never raises."""
    try:
        raw = (Path(workdir) / RUNS_REL).read_text(encoding="utf-8")
        rows = json.loads(raw)
    except (OSError, ValueError):
        return []
    return rows if isinstance(rows, list) else []


def last_failed_run(workdir):
    """The latest run if it failed, else None.

    Only the newest entry blocks: a SUCCEEDED run after an old FAIL
    clears the coast. Anything else lets a stale FAIL block fresh
    work forever, which is a different bug.
    """
    rows = [r for r in load_history(workdir) if isinstance(r, dict)]
    if not rows:
        return None
    latest = rows[-1]
    return latest if latest.get("outcome") == "FAILED" else None


def refusal_text(prior):
    """What a re-run over a FAILED run must print and then stop on."""
    return (f"REFUSED: workdir holds a FAILED run ({prior.get('run_id')}; "
            f"job {prior.get('job')!r}, rule {prior.get('rule')}, "
            f"{prior.get('rounds', '?')} rounds). It stays on the record. "
            "Re-run with --fresh to start a new run that cites this one.")


def _section8_history(entries):
    lines = ["## 8. Run history in this workdir", ""]
    if not entries:
        lines.append("This is the first recorded run here.")
        return lines
    lines.append(f"- Runs recorded: {len(entries)} (oldest first).")
    for e in entries:
        lines.append(f"- {e.get('run_id')}: {e.get('outcome')} -- "
                     f"{e.get('job')} "
                     f"({e.get('rounds', '?')} rounds, rule {e.get('rule')}, "
                     f"{e.get('when', '?')})")
    return lines


def append_history(workdir, entry):
    """Append one run to the workdir history; the list only ever grows."""
    path = Path(workdir) / RUNS_REL
    rows = load_history(workdir)
    rows.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return rows


def history_entry(rec):
    """One readable line of history from a finished run record."""
    state = rec.get("goldfish_state") or {}
    out = (state.get("outcome") or {}) if isinstance(state, dict) else {}
    if isinstance(state, dict) and state.get("rounds"):
        rounds = len(state["rounds"])
    else:
        rounds = 0
    return {
        "run_id": rec.get("run_id") or "never started",
        "job": rec.get("job"),
        "outcome": rec["stop"]["result"],
        "rule": out.get("rule", "-"),
        "rounds": rounds,
        "when": time.strftime("%Y-%m-%d %H:%M", time.localtime(rec["t0"])),
    }


def write_report(workdir, rec):
    """Render the report, write it under the workdir, return its path."""
    workdir = Path(workdir)
    rec["elapsed_s"] = time.time() - rec["t0"]
    # The report carries the history including this run, so a re-run can
    # never overwrite the past — it cites it. Refusals never reach here.
    entries = load_history(workdir) + [history_entry(rec)]
    rec["history"] = entries
    path = workdir / REPORT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(workdir, rec), encoding="utf-8")
    append_history(workdir, history_entry(rec))
    return path
