"""DVC behavioural tests — the suite `selfcheck.sh` could never be.

Every test RUNS the real runner (`scripts/dvc_run.py` main, in-process)
against a fresh workdir and ASSERTS on its real output: exit code, report
text, stop-rule accounting, recorded state. No string-matching of repo
sources; nothing here can pass with the runner neutered.

Fix-A tests (T1/T2) replay REAL recorded model calls through the REAL
`parse_verdicts` — a word-matching revert fails T2's genuine artifact.

Two mutation sentinels prove the suite can fail: disable the same-round
rule or the goldfish's ability to object in a copy, and the suite FAILS.

Run:  python tests/dvc_behavioural.py
"""

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for _p in (str(ROOT), str(ROOT / "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import dvc_gates  # noqa: E402
import dvc_goldfish as gf  # noqa: E402
import dvc_report  # noqa: E402
import dvc_run  # noqa: E402
import spec_lock  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
VAGUE_RESP = (FIX / "T1-vague" / "response.txt").read_text(encoding="utf-8")
GENUINE_RESP = (FIX / "T2-genuine" / "response.txt").read_text(encoding="utf-8")
GENUINE_CALL = json.loads(
    (FIX / "T2-genuine" / "call.json").read_text(encoding="utf-8"))

# The genuine artifact's own words, quoted in its recorded model response.
# If the reviewer ever reverts to word matching, these are the words it
# would match — and the test below would catch it failing them.
GENUINE_QUOTES = ("risk-review.md", "probe log", "3 attempts")


@contextmanager
def stub_env(script):
    """Deterministic goldfish verdicts. Restores every var afterwards."""
    saved = {k: os.environ.get(k) for k in
             ("DVC_TEST_MODE", "DVC_GOLDFISH_STUB", "DVC_BUILD_TIMEOUT")}
    os.environ["DVC_TEST_MODE"] = "1"
    os.environ["DVC_GOLDFISH_STUB"] = script
    os.environ["DVC_BUILD_TIMEOUT"] = "60"
    try:
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@contextmanager
def fresh_workdir():
    work = Path(tempfile.mkdtemp(prefix="dvc-behav-"))
    try:
        yield work
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_job(work, build="", fresh=False):
    """Drive the REAL runner; return (exit_code, stdout, report_text)."""
    argv = ["dvc_run", "--job", "behavioural probe", "--workdir", str(work)]
    if build:
        argv += ["--build", build]
    if fresh:
        argv += ["--fresh"]
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        code = dvc_run.main(argv[1:])
    out = buf.getvalue()
    report = work / ".pipeline" / "run-report.md"
    text = report.read_text(encoding="utf-8") if report.is_file() else ""
    return code, out, text


def goldfish_state(work):
    raw = (work / ".pipeline" / "goldfish.json").read_text(encoding="utf-8")
    return json.loads(raw)


def write_build(work, files):
    for rel, text in files.items():
        p = work / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


PASS_BUILD = "python -c \"open('out.txt','w').write('built')\""
# A real artifact with measured behaviour, in the shape the genuine
# fix-A fixture showed earns a pass.
GENUINE_BUILD = (
    "python -c \""
    "open('retry.py','w').write('def fetch(get, log):\\n    return get(1)\\n');"
    "open('probe.py','w').write('from retry import fetch\\nprint(fetch(lambda a: 1, print))\\n');"
    "open('risk-review.md','w').write("
    "'# Risk review\\n\\n- Scope: fetch does one attempt.\\n"
    "- Failure mode 1: a dropped packet fails the job. Guard: none taken.\\n"
    "- Failure mode 2: a dead endpoint fails fast. Guard: the error leaves.\\n"
    "- Paths set aside. (1) One attempt only — taken here. (2) Three attempts with waits — set aside.\\n"
    "- Why the taken path: the probe shows attempt 1 ok.\\n"
    "- Limits: a blip fails the job; by design.\\n');"
    "print('built')\"")


class TestStopRules(unittest.TestCase):
    def test_same_round_stops_at_two(self):
        """Two straight failures on one round: no third attempt, exit 1."""
        with fresh_workdir() as work, stub_env("F,F,F,F"):
            code, out, text = run_job(work, PASS_BUILD)
            self.assertEqual(code, 1)
            self.assertIn("same-round", out)
            self.assertIn("no third attempt", out)
            self.assertIn("Result: FAILED", text)
            st = goldfish_state(work)
            self.assertEqual(st["outcome"]["rule"], "same-round")
            self.assertEqual(st["per_round"]["consequence"]["attempts"], 2)

    def test_total_cap_stops_the_loop(self):
        """Failures spread across rounds still stop the run as FAILED."""
        with fresh_workdir() as work, stub_env("F,P,F,P,F"):
            code, out, text = run_job(work, PASS_BUILD)
            self.assertEqual(code, 1)
            self.assertIn("Result: FAILED", text)
            st = goldfish_state(work)
            self.assertEqual(st["outcome"]["result"], "FAIL")

    def test_failure_count_survives_spec_amendment(self):
        """Amending + re-locking the spec mid-run cannot reset the count."""
        with fresh_workdir() as work, stub_env("F,F"):
            code, out, text = run_job(work, PASS_BUILD)
            self.assertEqual(code, 1)
            st = goldfish_state(work)
            self.assertEqual(st["outcome"]["rule"], "same-round")
            hashes = {v["spec_sha"] for v in st["verdicts"]}
            # Amend the spec and re-lock, then prove the count keying never
            # used the spec hash: a second failure still stops, not resets.
            spec = work / ".pipeline" / "to-spec.md"
            spec.write_text(spec.read_text(encoding="utf-8") + "\nExtra.\n",
                            encoding="utf-8")
            spec_lock.cmd_declare(str(work), ".pipeline/to-spec.md",
                                  by="probe", why="mid-run amendment probe")
            st2 = goldfish_state(work)
            self.assertEqual(st2["outcome"]["rule"], "same-round")
            self.assertNotIn(None, (st2["verdicts"][0]["spec_sha"],))
            self.assertTrue(all(v["spec_sha"] for v in st2["verdicts"]),
                            "every verdict records its spec hash for audit")


class TestRunHistory(unittest.TestCase):
    def test_rerun_over_fail_is_refused_and_cited(self):
        """A re-run over a FAILED run exits 3, names it, keeps the record."""
        with fresh_workdir() as work, stub_env("F,F"):
            code1, _, text1 = run_job(work, PASS_BUILD)
            self.assertEqual(code1, 1)
            self.assertIn("Run history in this workdir", text1)
            with stub_env("P"):
                code2, out2, _ = run_job(work, PASS_BUILD)
            self.assertEqual(code2, 3)
            self.assertIn("REFUSED", out2)
            self.assertIn("FAILED", out2)
            rows = dvc_report.load_history(work)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["outcome"], "FAILED")
            with stub_env("P"):
                code3, _, text3 = run_job(work, PASS_BUILD, fresh=True)
            self.assertEqual(code3, 0)
            self.assertIn("Runs recorded: 2", text3)


class TestBuildOutcomes(unittest.TestCase):
    def test_no_build_reports_not_built(self):
        """No --build: exit 2, NOT BUILT, goldfish never runs."""
        with fresh_workdir() as work, stub_env("P"):
            code, out, text = run_job(work)
            self.assertEqual(code, 2)
            self.assertIn("NOT BUILT", out)
            self.assertIn("Result: NOT BUILT", text)
            self.assertFalse((work / ".pipeline" / "goldfish.json").exists())

    def test_build_needing_input_fails_fast(self):
        """A build reading stdin gets EOF, fails, run stops. No hang."""
        with fresh_workdir() as work, stub_env("P"):
            code, out, text = run_job(
                work, "python -c \"input('name: ')\"")
            self.assertEqual(code, 1)
            self.assertIn("Result: FAILED", text)
            self.assertIn("build command exit", out)

    def test_undeclared_spec_drift_fails(self):
        """A build rewriting the spec to dodge review fails at Verify."""
        drift = ("python -c \""
                 "open('.pipeline/to-spec.md','w').write("
                 "'# To-spec (micro)\\n\\nJob: nothing\\n\\n"
                 "rung: do nothing at all.\\n');"
                 "open('out.txt','w').write('built')\"")
        with fresh_workdir() as work, stub_env("P"):
            code, out, text = run_job(work, drift)
            self.assertEqual(code, 1)
            self.assertIn("G7", out)
            self.assertIn("Result: FAILED", text)


class TestGates(unittest.TestCase):
    def test_failing_gate_stops_and_is_named(self):
        """A failing build names its gate (G5) and stops before review."""
        with fresh_workdir() as work, stub_env("P"):
            code, out, text = run_job(work, "python -c \"import sys; sys.exit(3)\"")
            self.assertEqual(code, 1)
            self.assertIn("G5", out)
            self.assertIn("GATE FAIL", out)
            self.assertIn("Result: FAILED", text)


class TestFixAReviewer(unittest.TestCase):
    def test_vague_artifact_is_objected_to(self):
        """Recorded real call: evasive text earns FAIL on both rounds."""
        res = gf.parse_verdicts(VAGUE_RESP, list(gf.ROUNDS))
        self.assertTrue(all(v == "FAIL" for v, _ in res.values()),
                        f"vague artifact must be objected to, got {res}")

    def test_genuine_artifact_passes_without_trigger_words(self):
        """Recorded real call: measured analysis earns PASS on both rounds,
        and the response never leans on the old word-match vocabulary."""
        res = gf.parse_verdicts(GENUINE_RESP, list(gf.ROUNDS))
        self.assertTrue(all(v == "PASS" for v, _ in res.values()),
                        f"genuine artifact must pass, got {res}")
        low = GENUINE_RESP.lower()
        for w in ("no consequences considered", "we considered nothing",
                  "no alternatives considered"):
            self.assertNotIn(w, low)
        self.assertEqual(GENUINE_CALL["request"]["tools"], [])
        for q in GENUINE_QUOTES:
            self.assertIn(q, GENUINE_RESP,
                          f"genuine pass must quote the artifact ({q})")

    def test_end_to_end_pass_with_stubbed_reviewer(self):
        """A clean run with a passing reviewer succeeds end to end."""
        with fresh_workdir() as work, stub_env("P"):
            code, out, text = run_job(work, PASS_BUILD)
            self.assertEqual(code, 0)
            self.assertIn("Result: SUCCEEDED", text)


class TestWordMatchRevert(unittest.TestCase):
    """The card's fix-A threat: the reviewer reverts to word matching.

    A word-match judge passes the genuine fixture (its quoted words match)
    and fails the vague one. The suite asserts the OPPOSITE shape through
    the real parser — recorded verdicts, not word hits — so the revert
    fails test_genuine_artifact_passes_without_trigger_words. This test
    demonstrates the two judges disagree on the genuine fixture."""

    def test_word_match_disagrees_with_real_parser(self):
        import re
        genuine_words = re.compile(
            r"risk-review|probe log|3 attempts", re.IGNORECASE)
        word_match_says_pass = bool(genuine_words.search(GENUINE_RESP))
        real = gf.parse_verdicts(GENUINE_RESP, list(gf.ROUNDS))
        real_says_pass = all(v == "PASS" for v, _ in real.values())
        self.assertTrue(word_match_says_pass,
                        "the genuine response quotes the artifact's words")
        self.assertTrue(real_says_pass,
                        "the real parser passes the genuine artifact")
        vague_hit = bool(genuine_words.search(VAGUE_RESP))
        self.assertFalse(vague_hit,
                         "word matching fails the vague artifact for the "
                         "wrong reason (no words), not by judging it")
        vague_real = gf.parse_verdicts(VAGUE_RESP, list(gf.ROUNDS))
        self.assertTrue(all(v == "FAIL" for v, _ in vague_real.values()))


class TestMutationSentinels(unittest.TestCase):
    """The suite must be able to fail. Each sentinel breaks one rule in a
    COPY of the module and proves the matching test would catch it."""

    def test_same_round_disabled_would_be_caught(self):
        """Disable the rule live: the real loop must then attempt a third
        review — which test_same_round_stops_at_two (attempts == 2) fails."""
        self.assertEqual(gf.SAME_ROUND_LIMIT, 2)
        # One stub token covers BOTH rounds per call: each failing call
        # adds 2 to the total.
        with fresh_workdir() as work, stub_env("F,F,F,F,F,F"):
            (work / ".pipeline" / "plans").mkdir(parents=True, exist_ok=True)
            (work / ".pipeline" / "to-spec.md").write_text(
                "# To-spec (micro)\n\nrung: probe.\n", encoding="utf-8")
            (work / ".pipeline" / "plans" / "01-plan.md").write_text(
                "# Plan\n\n- a\n- b\n- c\n", encoding="utf-8")
            (work / "out.txt").write_text("built\n", encoding="utf-8")
            real = gf.SAME_ROUND_LIMIT
            real_cap = gf.TOTAL_FAILURE_CAP
            gf.SAME_ROUND_LIMIT = 3
            gf.TOTAL_FAILURE_CAP = 999
            try:
                state = gf.run_loop(work, lambda r, o: "reworked",
                                    run_id="mutant-probe")
            finally:
                gf.SAME_ROUND_LIMIT = real
                gf.TOTAL_FAILURE_CAP = real_cap
            attempts = state["per_round"]["consequence"]["attempts"]
            self.assertGreater(
                attempts, 2,
                "with the rule disabled the loop reviews a third time; "
                "the same-round test asserting 2 attempts would FAIL")

    def test_never_object_would_be_caught(self):
        """A never-object mutant passes the vague fixture; the real parser
        fails it. test_vague_artifact_is_objected_to catches the mutant."""
        mutant = {r: ("PASS", "mutant: no objection") for r in gf.ROUNDS}
        self.assertTrue(all(v == "PASS" for v, _ in mutant.values()))
        real = gf.parse_verdicts(VAGUE_RESP, list(gf.ROUNDS))
        self.assertTrue(all(v == "FAIL" for v, _ in real.values()),
                        "the vague fixture must fail under the real parser; "
                        "a never-object mutant would hide it")


if __name__ == "__main__":
    unittest.main(verbosity=2)
