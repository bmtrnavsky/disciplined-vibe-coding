# HOOKS.md — optional Hermes hooks for this pack

Skills are advisory — hooks and the small stdlib gate scripts in `scripts/`
(`dvc_stage.py`, `dvc_tickets.py`) are what keep them honest. Hermes has four
hook systems
(gateway HOOK.yaml+handler.py, plugin ctx.register_hook(), shell hooks declared
under `hooks:` in a profile's config.yaml, plus outbound webhooks which are
notify-only and cannot steer the agent). This pack ships one shell hook.

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
  and persists the decision to an allowlist. Approve it once in an
  interactive `hermes` session and you are done. Unattended contexts
  (gateway, cron) cannot prompt, so a newly added hook silently never
  registers there unless you opt in with `hooks_auto_accept: true`,
  `--accept-hooks`, or `HERMES_ACCEPT_HOOKS=1` — note that switch applies
  to every shell hook in that profile, not just this one.
- A hook's script content is trusted by command string, not by hash — editing
  the script on disk does not require re-approval. `hermes hooks doctor`
  flags mtime drift so you notice an edit happened.
- Every hook mechanism here is non-blocking by design at the framework level
  in the sense that a broken hook can't crash the agent — malformed JSON, a
  nonzero exit, or a timeout all just log a warning and continue. That is
  separate from whether an individual hook's own logic can block a tool call
  (`pre_tool_call` genuinely can, via `{"action": "block", ...}`) — §2 uses
  exactly that, while §1 stays advisory by choice.

## 1. readcheck (pre_llm_call; nudges, never blocks)

```yaml
hooks:
  pre_llm_call:
    - command: "<path-to-pack>/hooks/readcheck.sh"
      timeout: 5
```

Approve the hook once in an interactive `hermes` session when prompted;
that approval is saved and you are done.

Checks how long it's been since `.pipeline/read.log` (relative to the current
working directory) was last written. If it's been more than 40 minutes,
injects a one-line advisory into the next turn's context: touching an
unfamiliar API or codebase without reading docs first is exactly the failure
mode `research` and `debug` exist to prevent. If the log is fresh, the hook
emits `{}` and costs nothing.

This hook cannot stop a tool call, cannot require approval, and cannot see
which specific tool is about to run — those are `pre_tool_call` capabilities
this hook deliberately doesn't use, since the goal here is a nudge visible to
the model and the operator, not a gate that can misfire and block real work
on a false positive.

## 2. spec record (declared drift is advisory; undeclared drift fails)

`dvc_run.py` hashes the spec at Define (`spec_lock.py lock`).
A declared change (`declare --by NAME --why REASON`) re-hashes with
who/when/why — visibility only, never a block. A change with no
declaration fails the run at Verify (gate G7 spec-stable). No hook,
no prompt — the run enforces it, not a person.

```sh
python spec_lock.py lock                              # Define: hash the spec
python spec_lock.py check                             # re-hash and compare
python spec_lock.py declare --by NAME --why REASON    # record a change
```

- Lock lives at `.pipeline/spec.lock`: spec path, sha256, declarations.
- Undeclared drift prints a `spec drift: ... lock <hash> != current <hash>`
  line and fails the run at Verify (gate G7) — never a silent pass.
- Missing/unreadable lock or spec fails gate G7 at Verify, never a warning.
- Declared drift re-hashes, appending who/when/why plus old/new hashes —
  the record is visible in the lock, never silent; it stays advisory.
