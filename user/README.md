# user/ — your overlay. The updater never touches it.

Shipped files are read-only. Anything you customize lives here, mirroring
the repo tree: `user/<path>` overrides shipped `<path>`.

Example: to make the writing-plan template yours, copy it and edit the copy:

```sh
mkdir -p user/plugins/disciplined-vibe-coding/templates
cp plugins/disciplined-vibe-coding/templates/writing-plan.md user/plugins/disciplined-vibe-coding/templates/writing-plan.md
```

Then edit the copy under `user/`. Updates replace the shipped
template and reapply your overlay on top; a shipped change underneath your
overlay is reported as a conflict for review, never silently merged.

Start from the `.example` file at the same mirror path (see its header) to
see the shape of an overlay file. Full contract: `UPDATE.md`.
