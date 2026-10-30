# Update contract — shipped paths read-only to you, overlay wins

One rule, no exceptions: **shipped paths are read-only to you — never
hand-edit them; your edits live in `user/`; the updater never touches
`user/`.** The updater itself owns the shipped paths: every run
regenerates them as source-plus-overlay, so a hand-edit to a shipped file
is overwritten by design. This is the same rule as Hermes user-modified
marking, enforced by directory instead of by flag — anything under `user/`
is by definition user-modified.

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
   between the recorded baseline (what the last run installed) and the new
   source (shipped-then vs shipped-now — not source vs overlay, which
   always differ by design) is flagged for review: the overlay still wins
   until the user edits it, but the shipped diff may contain something
   worth adopting. The first run after the baseline was introduced has no
   baseline yet and compares working tree vs source once, then records one.
4. **Report stale files.** A working-tree file the fresh source no longer
   ships is kept and reported; re-run with `--prune` to delete stale files
   that were previously shipped (per the baseline) and that no overlay
   file covers. Files never shipped are reported as untracked and are never
   deleted.

Run it (manual checkouts only — catalog installs update with
`hermes plugins update disciplined-vibe-coding`, because copying a tree
over the install moves it off the reviewed pin): `sh scripts/update.sh --source <fresh-tree>` (preview: add `--check`; drop removed-upstream files: add `--prune`).
`<fresh-tree>` is a fresh clone or export of the pack at the target version.
The updater replaces itself (`scripts/update.sh`) as part of step 1 — it
re-execs from a temp copy first, so one run is enough; no re-run needed.
