# Reader guide — use this pack from any agent

The whole pack is plain Markdown plus one optional shell hook. Any agent
that reads `SKILL.md` files can run it. Copy the directories; nothing
needs compiling.

What to copy:

```text
skills/         the ten stage skills (Define → Plan → Build → Verify loop)
plugins/disciplined-vibe-coding/
  SKILL.md      the pipeline overlay (stages, gates, rung rules)
  references/   economy ladder
  templates/    to-spec, writing-plan, wayfinder
SOUL.md         persona (optional; or fold its rules into your system prompt)
```

## Agents with a skill loader

Copy each skill as its own folder containing its `SKILL.md`, into
whatever directory your agent scans for skills (consult your agent's
docs for the exact path — it differs per tool):

```text
<skills-dir>/disciplined-vibe-coding/SKILL.md   (from plugins/disciplined-vibe-coding/SKILL.md)
<skills-dir>/disciplined-intake/SKILL.md        (from skills/intake/SKILL.md)
... repeat per stage skill ...
```

Three rules travel with every copy:

- Keep the frontmatter `name`/`description` intact — that is the
  discovery signal most loaders read.
- Keep `references/` and `templates/` next to `SKILL.md` in the same
  folder, and load them only when the stage calls for them.
- The `readcheck.sh` hook is Hermes-only; skip it elsewhere.

## Agents with no skill loader

Paste order per task: `SOUL.md` once as the system prompt, then the
`SKILL.md` for the current pipeline stage only. Advance one stage at a
time. The pipeline degrades gracefully — one `SKILL.md` per stage still
works read straight out of the repo.
