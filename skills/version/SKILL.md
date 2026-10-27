---
name: version
description: Use for commits at Build checkpoints, and releases/bumps/changelogs in Verify. Narrative commits, semver, builder-readable changelog, annotated tags. (Lineage: agent-skills/git-workflow-and-versioning, release-skills)
phase: Verify
---

# Version — git is your safety net

## Prime directive
Commit history is the only audit trail.

## Invocation points
- Build: commit at every `execute` checkpoint — narrative, one logical change.
- Verify: releases only after verify green.

## Steps
1. **Narrative commits.** Why over what. Imperative. One logical change.
2. **Semver.** MAJOR breaks use. MINOR adds cleanly. PATCH fixes. Unsure on importables: MAJOR.
3. **Changelog** per `write-docs`: Added/Changed/Fixed/Deprecated/Removed, "what changed and do I care." Full-spec and above: entry per change. One-liner and micro-spec: no entry — the commit message is the record.
4. **Annotated tags** carry the changelog section. Tags mark project-rung releases only — routine commits never earn one.

## Rung scaling (economy ladder)

One-liner and micro-spec: single commit, no changelog, no tag. Full-spec:
changelog entry with the change. Project: changelog plus annotated tag at
release. "No release dance for routine work" holds because routine work is
not a release.

## Guardrails
- No commit bundling unrelated changes. No project-rung release without changelog + tag.
