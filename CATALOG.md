# Catalog submission — Hermes plugin catalog

Submission is a PR to `NousResearch/hermes-agent` adding one file:
`plugin-catalog/disciplined-vibe-coding.yaml` (see Entry schema in that
repo's `plugin-catalog/README.md`). There is no self-serve registry.

## Draft entry (fill in `sha` after commit + push, then PR)

```yaml
name: disciplined-vibe-coding
repo: https://github.com/bmtrnavsky/disciplined-vibe-coding
sha: PUT-PINNED-COMMIT-SHA-HERE
description: Define/Plan/Build/Verify pipeline with five folded-in practices, for non-engineer builders
maintainer: bmtrnavsky
tier: community
category: general
version: "0.2.0"
docs_url: https://github.com/bmtrnavsky/disciplined-vibe-coding#readme
readme: true
capabilities:
  provides_tools: []
  provides_hooks: []
  provides_middleware: []
  requires_env: []
```

`version` must match the pinned code — bump it in the same PR that bumps `sha`.

## Before opening the PR

1. Commit + push this repo, then put the full 40-char commit SHA in `sha:`.
2. Run `hermes plugins validate` (includes the `security scan` check) against
   the pinned commit. `dangerous` fails admission; `caution` findings go in
   the CI log for the reviewer — do not merge past them.
3. Confirm declared `capabilities:` match what the plugin registers at the
   pinned commit (undeclared capability creep is treated as a security issue).

## Disclosure lines for the PR description (rule 13)

- Skill content is Markdown: ten stage skills under `skills/`, a pipeline
  overlay under `plugins/disciplined-vibe-coding/`. No binaries, no
  dependencies, no network calls, no background processes, no telemetry.
- One root `__init__.py` (stdlib only, no imports beyond the host API)
  registers the skills with the host; no other code ships.
- Ships one optional shell hook (`hooks/`, documented in `HOOKS.md`): a
  research-freshness nudge. Runs only if the user installs it; reads
  nothing outside its own state file.
- No credentials, no `requires_env`, no OAuth, no secret handling of any kind.
- Catalog installs pin by SHA. The repo also ships `scripts/update.sh`,
  which refreshes a checkout from a fresh tree (replacing shipped files,
  reapplying the `user/` overlay, never writing into `user/`); it runs
  only when the user invokes it and is not part of catalog install.
