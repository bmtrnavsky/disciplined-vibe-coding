# Catalog submission — Hermes plugin catalog

Submission is a PR to `NousResearch/hermes-agent` adding one file:
`plugin-catalog/disciplined-vibe-coding.yaml` (see Entry schema in that
repo's `plugin-catalog/README.md`). There is no self-serve registry.

## Draft entry (fill in `sha` after commit + push, then PR)

```yaml
name: disciplined-vibe-coding
repo: https://github.com/bmtrnavsky/disciplined-vibe-coding
sha: eb4dc2ff81dcc9f6645efe021b8d1b4634ebded2
description: Define/Plan/Build/Verify pipeline with five folded-in practices, for non-engineer builders
maintainer: bmtrnavsky
tier: community
category: general
version: "0.1.0"
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

- Markdown-only skill pack: ten skills under `skills/`, a pipeline overlay
  under `plugins/disciplined-vibe-coding/`. No Python, no binaries, no
  dependencies, no network calls, no background processes, no telemetry.
- Ships one optional shell hook (`hooks/`, documented in `HOOKS.md`): a
  research-freshness nudge. Runs only if the user installs it; reads
  nothing outside its own state file.
- No credentials, no `requires_env`, no OAuth, no secret handling of any kind.
- Installs only through the SHA pin; no self-updater.
