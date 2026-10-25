# Economy ladder — right-size the effort before planning

Declare the rung in one sentence in the to-spec. The rung sets the
ceremony for Plan, Verify, and Commit. When in doubt, pick the lower rung;
a rung can step up mid-build if the blast radius grows.

| Rung | When | Ceremony |
|---|---|---|
| one-liner | 1 file, reversible, no open questions | intake is the chat line; no to-spec file, no plan file |
| micro-spec | up to 3 files, reversible, no new dependency | 3-line micro-spec; 3-bullet plan; single commit |
| full-spec | multi-file, irreversible, or a new dependency | full to-spec; full writing-plan; verify with fresh evidence |
| project | spans sessions, needs milestones | to-spec per milestone under `.pipeline/plans/`; roadmap; Wayfinder mandatory |

Blast-radius overrides: anything touching payments, live trading,
production data, or another profile's files steps up at least one rung.
MONEY-tier work is never a one-liner.

Declaration examples (one sentence each):

- "rung: one-liner, reversible single-line fix."
- "rung: micro-spec, reversible two-file change."
- "rung: full-spec, irreversible migration, needs fresh-evidence verify."
- "rung: project, three milestones, Wayfinder tracks across sessions."
