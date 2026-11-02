#!/usr/bin/env bash
# scripts/selfcheck.sh — acceptance checks for the STORM must-fix panel.
# Six checks: gate enforcement/bypass logging, teardown second-failure
# rule, rung step-up rule, goldfish hardening, 1.0 bar measurement,
# secret-scanning line. Plus syntax sanity (hook compiles, python compiles).
set -u
ROOT="$(dirname "$0")/.."
pass=0; fail=0
check() { # $1 = description, $2 = file, $3 = fixed string
  if grep -qF "$3" "$ROOT/$2"; then pass=$((pass+1));
  else fail=$((fail+1)); echo "FAIL: $1 ($2)"; fi
}
check "gate enforcement" plugins/disciplined-vibe-coding/SKILL.md "A failed gate blocks the next stage"
check "spec record declared advisory" plugins/disciplined-vibe-coding/SKILL.md "declared drift is advisory; undeclared drift fails"
check "spec record hook doc" HOOKS.md "spec record (declared drift is advisory"
check "not built wired" scripts/dvc_run.py "NOT BUILT"
check "stdin closed" scripts/dvc_run.py "stdin=subprocess.DEVNULL"
check "build timeout" scripts/dvc_run.py "DVC_BUILD_TIMEOUT"
check "g7 gate" scripts/dvc_gates.py "G7 verify/spec-stable"
check "g7 check" scripts/dvc_gates.py "def check_spec_stable"
check "not built gate" scripts/dvc_gates.py "NOT BUILT"
check "report not built" scripts/dvc_report.py "NOT BUILT"
check "report gate G7" scripts/dvc_report.py '"G7"'
if grep -qF "pre_tool_call" "$ROOT/__init__.py"; then fail=$((fail+1)); echo "FAIL: blocking hook still registered (__init__.py)"; else pass=$((pass+1)); fi
if grep -qF "on_pre_tool_call" "$ROOT/spec_lock.py"; then fail=$((fail+1)); echo "FAIL: blocking hook still present (spec_lock.py)"; else pass=$((pass+1)); fi
check "lock tool present" spec_lock.py "def cmd_lock"
check "declared drift stays visible" spec_lock.py "Declared drift is visibility"
check "declare path" spec_lock.py "declarations"
check "run entry present" scripts/dvc_run.py "zero human input"
check "bypass logging" plugins/disciplined-vibe-coding/SKILL.md "logged in the Wayfinder result"
check "teardown second failure" plugins/disciplined-vibe-coding/SKILL.md "A second failure on the same round stops the"
check "rung step-up" plugins/disciplined-vibe-coding/SKILL.md "A rung never steps down"
check "ladder step-up" plugins/disciplined-vibe-coding/references/economy-ladder.md "never steps down mid-build"
check "goldfish hardening" plugins/disciplined-vibe-coding/SKILL.md "Each round note states the sources opened"
check "1.0 bar measurement" plugins/disciplined-vibe-coding/SKILL.md "named in the changelog entry that claims 1.0"
check "secret scan pipeline" plugins/disciplined-vibe-coding/SKILL.md "Secret scan before every commit"
check "secret scan version" skills/version/SKILL.md "secret-scan hit"
check "goldfish module" scripts/dvc_goldfish.py "cannot approve"
check "goldfish blind" scripts/dvc_goldfish.py "Sees only the packet files"
check "same-round stop" scripts/dvc_goldfish.py "SAME_ROUND_LIMIT = 2"
check "total cap" scripts/dvc_goldfish.py "TOTAL_FAILURE_CAP = len(ROUNDS) + 1"
check "count keying" scripts/dvc_goldfish.py "never by spec hash"
check "stub gated" scripts/dvc_goldfish.py "DVC_TEST_MODE"
check "regex judge gone" scripts/dvc_run.py "hash-locked packet"
check "packet template" templates/goldfish-packet.md "no approve verdict"
check "loop wired" scripts/dvc_run.py "goldfish loop ended in FAILURE"
check "run id" scripts/dvc_run.py "run_id = dvc_goldfish.make_run_id"
check "no third attempt" scripts/dvc_goldfish.py "no third attempt"
check "gates module" scripts/dvc_gates.py "ADVISORIES = ("
check "gate G1 wired" scripts/dvc_run.py "define/spec-locked"
check "gate G2 wired" scripts/dvc_run.py "economy/rung-declared"
check "gate G3 wired" scripts/dvc_run.py "plan/shaped"
check "gate G4 named" scripts/dvc_run.py "teardown/goldfish-pass"
check "gate G5 wired" scripts/dvc_run.py "build/proof-green"
check "gate G6 mapped" scripts/dvc_run.py "verify/done-claim-mapped"
check "gate fail names" scripts/dvc_gates.py "GATE FAIL"
check "advisory labelled" scripts/dvc_run.py "ADVISORY"
check "report module" scripts/dvc_report.py "run-report.md"
check "report printed" scripts/dvc_run.py 'report: {path}'
check "report quotes verbatim" scripts/dvc_report.py "quoted verbatim"
check "report never overstates" scripts/dvc_report.py "never \"completed with notes\""
if bash -n "$ROOT/hooks/readcheck.sh"; then pass=$((pass+1));
else fail=$((fail+1)); echo "FAIL: hooks/readcheck.sh syntax"; fi
if python -m py_compile "$ROOT/__init__.py" 2>/dev/null; then pass=$((pass+1));
else fail=$((fail+1)); echo "FAIL: __init__.py compiles"; fi
echo "selfcheck: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
