---
name: version
description: Use for commits at Build checkpoints, releases/bumps/changelogs in Verify, and branch or worktree finish (merge, keep open, or handoff). Narrative commits, semver, builder-readable changelog, annotated tags. (Lineage: agent-skills/git-workflow-and-versioning, release-skills)
phase: Verify
---

# Version — git is your safety net

## Prime directive
Commit history is the only audit trail.

## Invocation points
- Build: commit at every `execute` checkpoint — narrative, one logical change.
- Verify: releases only after verify green.
- Finish: feature branch or worktree done, suite green, merge or handoff per the checklist below.
- Ticket builds: write the commit sha into the ticket's rollback line (card
  body, or the ticket's section in the plan) at commit time. to-tickets ships
  that line as an instruction; the commit is where the sha exists.

## Steps
1. **Narrative commits.** Why over what. Imperative. One logical change.
2. **Semver.** MAJOR breaks use. MINOR adds cleanly. PATCH fixes. Unsure on importables: MAJOR.
3. **Changelog** per `write-docs`: Added/Changed/Fixed/Deprecated/Removed, "what changed and do I care." Full-spec and above: entry per change. One-liner and micro-spec: no entry — the commit message is the record.
4. **Annotated tags** carry the changelog section. Tags mark project-rung releases only — routine commits never earn one.

## Finish checklist (feature branch or worktree only)
1. Full suite green, fresh evidence in hand.
2. Confirm base branch (plan, conversation, or upstream). Ask if unsure.
3. Present options: merge, keep branch open, or hand the diff to the user. In all three cases sync `.pipeline/` back to the main checkout first, then update the status footer. On merge or handoff, remove the worktree if one was created; when keeping the branch open, leave it in place. At project rung, merge comes before the release changelog section and tag, since the tag belongs on the base branch.

## Rung scaling (economy ladder)

One-liner and micro-spec: single commit, no changelog, no tag. Full-spec:
changelog entry with the change. Project: changelog plus annotated tag at
release. "No release dance for routine work" holds because routine work is
not a release.

## Guardrails
- No commit bundling unrelated changes. No project-rung release without changelog + tag.
- No commit with an unhandled secret-scan hit: search the staged diff for
  keys, tokens, passwords, and connection strings first.
