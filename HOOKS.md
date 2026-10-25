# HOOKS.md — optional Hermes hooks for this pack

Skills are advisory — hooks keep them honest. Hermes has three hook mechanisms
(gateway HOOK.yaml+handler.py, plugin ctx.register_hook(), shell hooks declared
under `hooks:` in a profile's config.yaml). This pack ships one shell hook.

## Real constraint, read this before adding more

Shell hooks communicate over a strict JSON contract, not plain text:

- The script receives a JSON payload on **stdin** (`hook_event_name`, `tool_name`,
  `tool_input`, `session_id`, `cwd`, `extra`).
- The script must print **valid JSON** on **stdout** — `{}` for a no-op, or an
  event-specific shape. Plain text on stdout is non-matching output and is
  silently ignored; nothing surfaces to the model or the operator.
- **Only `pre_llm_call` can inject context** into the conversation
  (`{"context": "..."}`). `pre_tool_call` and `post_tool_call` can only
  `block` or `approve` a tool call — there is no context-injection path on
  those events. A hook meant to nudge rather than gate has to live on
  `pre_llm_call`, even if the original intent was to tie it to a specific
  tool (e.g. `write_file`/`patch`) via a `matcher`. `matcher` only applies to
  `pre_tool_call`/`post_tool_call` in the first place, so a `pre_llm_call`
  hook never takes one — it fires once per turn, unconditionally.
- First use of any `(event, command)` pair prompts for interactive approval
  and persists the decision to an allowlist. Any non-interactive context
  (gateway, cron) needs `hooks_auto_accept: true` in config.yaml, or the
  `--accept-hooks` CLI flag, or `HERMES_ACCEPT_HOOKS=1` — otherwise a newly
  added hook silently never registers.
- A hook's script content is trusted by command string, not by hash — editing
  the script on disk does not require re-approval. `hermes hooks doctor`
  flags mtime drift so you notice an edit happened.
- Every hook mechanism here is non-blocking by design at the framework level
  in the sense that a broken hook can't crash the agent — malformed JSON, a
  nonzero exit, or a timeout all just log a warning and continue. That is
  separate from whether an individual hook's own logic can block a tool call
  (`pre_tool_call` genuinely can, via `{"action": "block", ...}`) — this pack
  doesn't use that, by choice, described below.

## 1. readcheck (pre_llm_call; nudges, never blocks)

```yaml
hooks:
  pre_llm_call:
    - command: "<path-to-pack>/hooks/readcheck.sh"
      timeout: 5
hooks_auto_accept: true
```

Checks how long it's been since `.pipeline/read.log` (relative to the current
working directory) was last written. If it's been more than 40 minutes,
injects a one-line advisory into the next turn's context: touching an
unfamiliar API or codebase without reading docs first is exactly the failure
mode `research` and `debug` exist to prevent. If the log is fresh, the hook
emits `{}` and costs nothing.

This hook cannot stop a tool call, cannot require approval, and cannot see
which specific tool is about to run — those are `pre_tool_call` capabilities
this pack deliberately doesn't use, since the goal here is a nudge visible to
the model and the operator, not a gate that can misfire and block real work
on a false positive.
