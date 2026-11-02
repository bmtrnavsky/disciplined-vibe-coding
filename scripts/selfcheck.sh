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
check "spec record advisory" plugins/disciplined-vibe-coding/SKILL.md "Spec record (advisory"
check "spec record hook doc" HOOKS.md "spec record (advisory"
if grep -qF "pre_tool_call" "$ROOT/__init__.py"; then fail=$((fail+1)); echo "FAIL: blocking hook still registered (__init__.py)"; else pass=$((pass+1)); fi
if grep -qF "on_pre_tool_call" "$ROOT/spec_lock.py"; then fail=$((fail+1)); echo "FAIL: blocking hook still present (spec_lock.py)"; else pass=$((pass+1)); fi
check "lock tool present" spec_lock.py "def cmd_lock"
check "advisory wording" spec_lock.py "Advisory only"
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
if bash -n "$ROOT/hooks/readcheck.sh"; then pass=$((pass+1));
else fail=$((fail+1)); echo "FAIL: hooks/readcheck.sh syntax"; fi
if python -m py_compile "$ROOT/__init__.py" 2>/dev/null; then pass=$((pass+1));
else fail=$((fail+1)); echo "FAIL: __init__.py compiles"; fi
echo "selfcheck: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
