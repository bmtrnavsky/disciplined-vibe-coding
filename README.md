# A coding agent for non-engineers and vibe coders

A lean skill pack + persona for one named orchestrator (built for Hermes;
portable to any agent that supports skill files). For someone who wants to
build real software — small fixes through multi-week projects — without
being a software engineer, with lead-dev discipline explained in plain
language at every step.

This isn't a shortcut around learning. It's scaffolding: the same rigor a
senior engineer would insist on (define before building, test before
shipping, verify before claiming done), applied consistently so you can lean
on it instead of having to already know it.

## The loop

    Define (intake -> brainstorm) -> Plan (research <-> plan) -> Build (test-first -> execute <-> debug) -> Verify (verify -> version)

One loop per small task, or per milestone of a larger project. Same four
words every time — the repetition is deliberate. You learn the shape of good
engineering practice by watching it applied the same way, over and over,
not by reading a lecture about it once.

## What it actually stops you from doing

- Building before anyone (you or the agent) has said out loud what "done"
  looks like.
- Shipping a destructive change with no rollback plan.
- Claiming something works because a command didn't error, rather than
  because someone actually checked the output.
- Storing payment card data instead of using a provider-hosted checkout.
- Running something autonomous (a bot, a scheduler) with no kill-switch.
- A near-miss on a metric getting quietly rounded up to "good enough."

## Stakes-aware, not one-size-fits-all

Every task gets a tier: **TOY** (learning, nothing at risk), **WORKFLOW**
(your own systems could break), or **MONEY** (payments, live trading,
anything public-facing). The tier changes what gets asked, what gets a
rollback plan, and whether a stronger model reviews the work before it's
called finished.

## Layout

    SOUL.md              the persona — how it talks, what it never compromises on
    USER.md.template      fill in your own background, environment, and preferences
    HOOKS.md              optional shell hook for research-freshness nudges
    hooks/                the one hook this pack ships
    skills/               the ten skills that make up the loop
    ATTRIBUTIONS.md        what this pack draws from, and where
    SOURCE-LICENSES.md    full license text and copyright lines for every source

## Install

**Hermes:** `SOUL.md` → your profile's `SOUL.md`; `skills/` → your profile's
skills directory (or a shared skills path referenced via
`skills.external_dirs`); `USER.md.template` → fill in and save as `USER.md`;
`hooks/` → optional, wire into `config.yaml` per `HOOKS.md` if you want the
research-freshness nudge.

**Elsewhere:** `SOUL.md` → your system prompt; the `SKILL.md` files → wherever
your tool loads skills from.

## Why "vibe coder," not "Turing," not a brand name

The name doesn't matter — call your instance whatever you want in your own
`SOUL.md`. What matters is the shape: a fixed loop, plain language, and
guardrails that hold whether you're fixing a small bug or shipping something
real. This repo describes the shape, not a persona to imitate.

## License

MIT for everything original to this pack (`SOUL.md`, `USER.md.template`,
`HOOKS.md`, this README). The ten skills derive from several MIT-licensed
sources — see `ATTRIBUTIONS.md` for lineage and `SOURCE-LICENSES.md` for the
full license text and copyright line of every upstream project. Those
notices travel with this pack per MIT's terms; keep them if you fork or
redistribute.
