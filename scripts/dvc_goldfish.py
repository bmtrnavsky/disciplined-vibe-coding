"""Blind goldfish review loop for the autonomous DVC run (card 2/4).

Contract (Brad's stop rules):

- Elephant builds to the spec (here: the spec + plan the run just wrote;
  no code exists yet at Teardown).
- Goldfish reviews blind after every round: ``judge_artifact`` receives
  ONLY the spec text, the plan text, and the round name. No workdir, no
  chat history, no implementation, no tools. It cannot amend the spec
  (read-only inputs), cannot run anything (this module has no subprocess,
  no exec, no input()), and cannot approve: there is no approve verdict.
  An empty objection list IS the pass. Only the absence of objection ends
  the loop.
- Objections return to the elephant as new work; review then restarts from
  the top round, because rework can break earlier passes and no human is
  around to judge the blast radius.

Stop rules:

1. Same-round rule (Brad's number: 2) -- two CONSECUTIVE failures on one
   round stop the run. Consecutive, not cumulative: a pass resets the
   round, because fail-then-fix-then-break-again is regression, not
   guessing. (A cumulative reading would make rule 2 dead math: with 2
   rounds any 3rd failure must repeat a round, so a total cap could never
   fire on its own.)
2. Total failure cap = number of rounds + 1 (micro-spec: 3). A converging
   run fails each round at most once on first sight; the (R+1)-th failure
   proves cleared ground broke again -- global thrash, not convergence.

On either stop the run reports FAILURE: the round that could not pass,
the objections verbatim, and what the elephant tried. No partial success,
no spec loosening, no advance to Build.

Count keying (the p_g3 bypass): failure counts live in
``.pipeline/goldfish.json`` keyed (run_id -> round). The spec hash is
recorded on every verdict for audit but NEVER used as a key, so a mid-run
amendment + re-lock cannot reset the count.

Test stub: ``DVC_GOLDFISH_STUB`` (comma-separated F/P verdicts consumed in
review-call order) is honored only when ``DVC_TEST_MODE=1`` -- the same
gating shape as the sibling project's provider stub. Production runs
ignore it and use the mechanical judge below.
"""

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
from pathlib import Path

ROUNDS = ("consequence", "alternatives")

# Brad's number: two straight failures on one round, no third attempt.
SAME_ROUND_LIMIT = 2
# Backstop for genuinely new failures on every round: R rounds can fail at
# most once each on first sight in a converging run, so failure R+1 means
# cleared ground broke again.
TOTAL_FAILURE_CAP = len(ROUNDS) + 1

STATE_REL = ".pipeline/goldfish.json"

ROUND_EXPECTED = {
    "consequence": "what happens if we build exactly this, and where it breaks",
    "alternatives": "what else solves it, and whether this is the strongest option",
}

# Micro-spec mechanical judge: each pass asks one question; the artifact
# (spec + plan) passes the round when it answers that question in words.
ROUND_PATTERNS = {
    "consequence": re.compile(
        r"consequence|if we build exactly|where it breaks|breaks if|blast radius|downside",
        re.IGNORECASE,
    ),
    "alternatives": re.compile(
        r"alternat|instead|option|considered|strongest|doing nothing",
        re.IGNORECASE,
    ),
}


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _short(h):
    return (h or "?")[:12]


def _stub_tokens():
    """Verdict script for tests; None in production (stub ignored there)."""
    if os.environ.get("DVC_TEST_MODE") != "1":
        return None
    raw = os.environ.get("DVC_GOLDFISH_STUB", "")
    tokens = [t.strip().upper() for t in raw.split(",") if t.strip()]
    return tokens or None


def judge_artifact(spec_text, plan_text, round_name, tokens=None):
    """Blind review of one round. Returns [objections]; [] = pass.

    Sees only the two texts plus the round name -- no workdir, no history,
    no implementation. Read-only: it cannot amend anything, run anything,
    or approve anything; silence is the only pass.
    """
    if round_name not in ROUND_PATTERNS:
        raise ValueError(f"unknown goldfish round {round_name!r} (rounds: {', '.join(ROUNDS)})")
    if tokens is not None and tokens:
        if tokens.pop(0).startswith("F"):
            return [f"OBJECTION {round_name}: stubbed objection -- "
                    f"artifact says nothing about {ROUND_EXPECTED[round_name]}."]
        return []
    artifact = f"{spec_text}\n{plan_text}"
    if not ROUND_PATTERNS[round_name].search(artifact):
        return [f"OBJECTION {round_name}: spec+plan say nothing about "
                f"{ROUND_EXPECTED[round_name]}."]
    return []


def state_path_for(workdir):
    return Path(workdir) / STATE_REL


def new_state(run_id):
    return {
        "run_id": run_id,
        "rounds": list(ROUNDS),
        "same_round_limit": SAME_ROUND_LIMIT,
        "total_failure_cap": TOTAL_FAILURE_CAP,
        "total_failures": 0,
        # Counts keyed by round within this run file -- never by spec hash,
        # so a mid-run amendment + re-lock cannot reset them (p_g3 bypass).
        "per_round": {
            r: {"fails_consec": 0, "attempts": 0} for r in ROUNDS
        },
        "verdicts": [],
        "outcome": None,
    }


def save_state(workdir, state):
    path = state_path_for(workdir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def format_failure(state, rule, round_name):
    """Failure report: the round, verbatim objections, elephant's tries."""
    fails = [v for v in state["verdicts"]
             if v["round"] == round_name and v["verdict"] == "FAIL"]
    lines = [
        f"STOP: goldfish loop ends -- FAILURE ({rule}).",
        f"round that could not pass: {round_name}",
        f"run: {state['run_id']} "
        f"(failures total {state['total_failures']}, "
        f"cap {TOTAL_FAILURE_CAP}; round consecutive {fails[-1]['round_fails_consec'] if fails else '?'} "
        f"of {SAME_ROUND_LIMIT})",
        "objections (verbatim):",
    ]
    for v in fails:
        for ob in v["objections"]:
            lines.append(f"  - {ob}")
    lines.append("what the elephant tried in response:")
    for i, v in enumerate(fails, 1):
        lines.append(f"  - after '{round_name}' failure {i} of {len(fails)}: "
                     f"{v['elephant_response']}")
    hashes = ", ".join(_short(v["spec_sha"]) for v in fails)
    lines.append(f"spec hashes across these failures: {hashes} "
                 f"(count keyed by round within run {state['run_id']}; "
                 f"amendment does not reset it)")
    return "\n".join(lines)


def run_loop(workdir, read_artifact, elephant_respond, run_id):
    """Run rounds until no objections (PASS) or a stop rule fires (FAIL).

    ``read_artifact`` -> (spec_text, plan_text), re-read fresh every review.
    ``elephant_respond``(round, objections) -> response text; it may append
    to the plan/teardown notes but MUST NOT touch the spec.
    Returns the state dict (outcome.result is PASS or FAIL).
    """
    workdir = Path(workdir)
    tokens = _stub_tokens()
    state = new_state(run_id)
    seq = 0
    while True:
        for rnd in ROUNDS:
            spec_text, plan_text = read_artifact()
            objections = judge_artifact(spec_text, plan_text, rnd, tokens)
            st = state["per_round"][rnd]
            st["attempts"] += 1
            seq += 1
            spec_sha = _sha(spec_text)
            if not objections:
                st["fails_consec"] = 0
                state["verdicts"].append({
                    "seq": seq, "round": rnd, "verdict": "PASS",
                    "spec_sha": spec_sha, "objections": [],
                    "elephant_response": None,
                })
                save_state(workdir, state)
                print(f"goldfish {rnd}: no objection "
                      f"(attempt {st['attempts']}, spec {_short(spec_sha)})",
                      flush=True)
                continue
            st["fails_consec"] += 1
            state["total_failures"] += 1
            for ob in objections:
                print(ob, flush=True)
            response = elephant_respond(rnd, objections)
            state["verdicts"].append({
                "seq": seq, "round": rnd, "verdict": "FAIL",
                "spec_sha": spec_sha, "objections": list(objections),
                "elephant_response": response,
                "round_fails_consec": st["fails_consec"],
            })
            save_state(workdir, state)
            if st["fails_consec"] >= SAME_ROUND_LIMIT:
                state["outcome"] = {"result": "FAIL", "rule": "same-round",
                                    "round": rnd, "run_id": run_id,
                                    "failures_total": state["total_failures"]}
                save_state(workdir, state)
                print(format_failure(state, "same-round rule: "
                                     f"'{rnd}' failed twice, no third attempt",
                                     rnd), flush=True)
                return state
            if state["total_failures"] >= TOTAL_FAILURE_CAP:
                state["outcome"] = {"result": "FAIL", "rule": "total-cap",
                                    "round": rnd, "run_id": run_id,
                                    "failures_total": state["total_failures"]}
                save_state(workdir, state)
                print(format_failure(state, "total failure cap: "
                                     f"{state['total_failures']} failures "
                                     f"(cap {TOTAL_FAILURE_CAP})", rnd),
                      flush=True)
                return state
            print(f"elephant responds on {rnd} (attempt {st['attempts']}); "
                  f"re-reviewing from the top", flush=True)
            break  # rework may have broken earlier passes: restart
        else:
            state["outcome"] = {"result": "PASS", "run_id": run_id,
                                "rounds": list(ROUNDS),
                                "failures_total": state["total_failures"]}
            save_state(workdir, state)
            print(f"goldfish loop: PASS -- {len(ROUNDS)} rounds, "
                  f"{state['total_failures']} objection(s) answered, "
                  f"run {run_id}", flush=True)
            return state


def make_run_id():
    return (f"{int(time.time())}x{os.getpid()}x{random.randint(0, 65535):04x}")


def cmd_review(args):
    """Ad-hoc blind review: reads ONLY the two given files, prints
    objections (or nothing = pass). Always exits 0 -- a review objects,
    it never fails."""
    spec_text = Path(args.spec).read_text(encoding="utf-8")
    plan_text = Path(args.plan).read_text(encoding="utf-8")
    for ob in judge_artifact(spec_text, plan_text, args.round):
        print(ob)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Blind goldfish review (no approve)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("review", help="blind-review two files for one round")
    p.add_argument("--round", required=True, choices=list(ROUNDS))
    p.add_argument("--spec", required=True)
    p.add_argument("--plan", required=True)
    ns = ap.parse_args(argv)
    if ns.cmd == "review":
        return cmd_review(ns)
    return 2


if __name__ == "__main__":
    sys.exit(main())
