#!/usr/bin/env bash
# hooks/turing-readcheck.sh
# pre_llm_call hook — advisory only, never blocks.
# Design note: the original intent was to tie this to write_file/patch calls
# specifically (pre_tool_call), but pre_tool_call only supports block/approve,
# not context injection. Context injection is pre_llm_call-only, which fires
# once per turn rather than once per write. Moved here deliberately so the
# advisory actually surfaces instead of being silently ignored.
payload="$(cat -)"
cwd=$(echo "$payload" | jq -r '.cwd // "."')
LOG="$cwd/.turing/read.log"
NOW=$(date +%s)

if [ -s "$LOG" ]; then
  MTIME=$(stat -c %Y "$LOG" 2>/dev/null || stat -f %m "$LOG" 2>/dev/null || echo 0)
  AGE=$(( NOW - MTIME ))
  if [ "$AGE" -le 2400 ]; then
    printf '{}\n'
    exit 0
  fi
fi

jq --null-input '{context: "[TURING] Advisory: no docs/read logged in 40 min. Touching an API or unfamiliar code? Research first; log it."}'
