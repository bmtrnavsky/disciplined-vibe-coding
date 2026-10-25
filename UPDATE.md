# Update contract — shipped files read-only, user edits in overlay

One rule, no exceptions: **shipped files are read-only; user edits live in
`user/`; the updater never touches `user/`.** This is the same rule as Hermes
user-modified marking, enforced by directory instead of by flag — anything
under `user/` is by definition user-modified.

## Overlay convention

- `user/` mirrors the repo tree: `user/<path>` overrides shipped `<path>`.
  Example: `user/plugins/disciplined-vibe-coding/templates/writing-plan.md`
  stands in for `plugins/disciplined-vibe-coding/templates/writing-plan.md`
  at use time.
- Only files the user actually customized get an overlay copy. No copy, no
  override — the shipped file is used as-is.
- The updater never writes, moves, or deletes anything under `user/`, except
  the shipped documentation itself (`user/README.md`, `*.example` files).
- To customize: copy the shipped file to its `user/` mirror path and edit
  the copy. Never edit the shipped file in place.
- Commit overlay files in your fork so updates stay clean; on a non-git
  install they simply persist where they are.

## Update procedure

1. **Replace the pack.** Fresh files overwrite every shipped path —
   everything except `user/`, `.git/`, `.pipeline/`, and bytecode/caches.
2. **Reapply the overlay.** Each `user/<path>` (minus README/examples) is
   copied back over its shipped mirror path, so customizations survive.
3. **Report conflicts.** An overlay file whose shipped counterpart changed
   underneath it is flagged for review: the overlay still wins until the
   user edits it, but the shipped diff may contain something worth adopting.

Run it: `sh scripts/update.sh --source <fresh-tree>` (preview: add `--check`).
`<fresh-tree>` is a fresh clone or export of the pack at the target version.
