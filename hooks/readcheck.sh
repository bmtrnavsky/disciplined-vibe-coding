#!/usr/bin/env bash
# hooks/readcheck.sh
# pre_llm_call hook — advisory only, never blocks.
# Design note: the original intent was to tie this to write_file/patch calls
# specifically (pre_tool_call), but pre_tool_call only supports block/approve,
# not context injection. Context injection is pre_llm_call-only, which fires
# once per turn rather than once per write. Moved here deliberately so the
# advisory actually surfaces instead of being silently ignored.
#
# Dependency-free on purpose: no jq. Every exit path prints exactly one
# valid JSON object to stdout — a hook that prints nothing (missing
# dependency, unparsable payload) is silently ignored by Hermes, which
# would make this hook dead without anyone noticing.
payload="$(cat -)"

# Extract "cwd" from the JSON payload with sed; fall back to "." when the
# payload is empty, malformed, or carries no cwd.
cwd="$(printf '%s' "$payload" | sed -n 's/.*"cwd"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)"
[ -n "$cwd" ] || cwd="."
LOG="$cwd/.pipeline/read.log"
NOW=$(date +%s)
case "$NOW" in *[!0-9]*) NOW=0 ;; esac

if [ -s "$LOG" ]; then
  MTIME=$(stat -c %Y "$LOG" 2>/dev/null || stat -f %m "$LOG" 2>/dev/null || echo 0)
  case "$MTIME" in *[!0-9]*) MTIME=0 ;; esac
  AGE=$(( NOW - MTIME ))
  if [ "$AGE" -le 2400 ]; then
    printf '{}\n'
    exit 0
  fi
fi

printf '{"context": "[pipeline] Advisory: no docs/read logged in 40 min (or no read log yet). Touching an API or unfamiliar code? Research first; log it."}\n'
