#!/bin/sh
# update.sh — replace shipped pack files from a fresh source tree, then reapply the user/ overlay.
#
# Contract (see UPDATE.md): shipped paths are read-only TO YOU — never
# hand-edit them; the updater owns them and regenerates their content as
# source-plus-overlay on every run. Your edits live in user/, which this
# script never writes into.
#
# Usage:
#   sh scripts/update.sh --source <fresh-tree> [--check] [--prune]
#
#   <fresh-tree>  fresh clone/export of the pack at the target version.
#   --check       dry run: report what would change, touch nothing.
#   --prune       also delete working-tree files the source tree no longer
#                 ships (stale files), but only ones the recorded baseline
#                 says were previously shipped, and never ones an overlay
#                 file covers. Never-shipped files are reported as untracked
#                 and never deleted. Without --prune everything is only
#                 reported, never deleted.
#
# Step 1 (replace the pack): every file in <fresh-tree> except user/, .git/,
# .pipeline/, and caches is copied over the working tree.
# Step 2 (reapply the overlay): each user/<path> (minus README/examples) is
# copied back over its shipped mirror path, so the working tree always
# holds source-plus-overlay. Hand-edits to shipped paths are lost here —
# that is by design; put them in user/ instead.
# Step 3 (report): overlay files whose shipped counterpart changed between
# the recorded baseline (what the last run installed) and the new source
# (shipped-then vs shipped-now) are flagged as conflicts for review. The
# overlay still wins. Comparing against the working tree instead would flag
# every customized file on every update — it already holds source-plus-overlay.
# Step 4 (stale): working-tree files the source no longer ships are
# reported; --prune deletes only ones the baseline says were previously
# shipped and no overlay file covers. Never-shipped files are reported as
# untracked and never deleted. Without --prune everything is kept.

set -eu

# Self-update safety: Step 1 replaces scripts/update.sh itself, and a shell
# may read a running script incrementally — overwriting $0 mid-run can then
# execute mixed old/new code. Re-exec from a temp copy so the on-disk
# replacement never affects the running process. No re-run needed.
if [ -z "${_UPDATE_REEXEC:-}" ]; then
    tmp_self=$(mktemp)
    cp "$0" "$tmp_self"
    export _UPDATE_REEXEC=1 _UPDATE_TMP_SELF="$tmp_self" \
        _UPDATE_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
    exec sh "$tmp_self" "$@"
fi

SRC=""
CHECK=0
PRUNE=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --source)
            SRC="${2:-}"
            shift 2
            ;;
        --check)
            CHECK=1
            shift
            ;;
        --prune)
            PRUNE=1
            shift
            ;;
        -h|--help)
            sed -n '2,/^$/p' "$0"
            echo "Usage: sh scripts/update.sh --source <fresh-tree> [--check] [--prune]"
            exit 0
            ;;
        *)
            echo "update.sh: unknown argument '$1'" >&2
            echo "Usage: sh scripts/update.sh --source <fresh-tree> [--check] [--prune]" >&2
            exit 1
            ;;
    esac
done

if [ -z "$SRC" ]; then
    echo "update.sh: --source <fresh-tree> is required" >&2
    exit 1
fi

ROOT=${_UPDATE_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}
SRC=$(CDPATH= cd -- "$SRC" && pwd)

if [ "$SRC" = "$ROOT" ]; then
    echo "update.sh: source and working tree are the same directory; refusing" >&2
    exit 1
fi
if [ ! -d "$SRC" ]; then
    echo "update.sh: source '$SRC' is not a directory" >&2
    exit 1
fi

# Shipped files in the source tree: everything except the never-touch zones.
list_shipped() {
    cd "$SRC" && find . -type f \
        -not -path './.git/*' \
        -not -path './user/*' \
        -not -path './.pipeline/*' \
        -not -path './__pycache__/*' \
        -not -name '*.pyc' | sort
}

# Active overlay files: user-owned customizations only (docs/examples excluded).
list_overlay() {
    if [ ! -d "$ROOT/user" ]; then
        return 0
    fi
    cd "$ROOT/user" && find . -type f \
        -not -name 'README.md' \
        -not -name '.gitignore' \
        -not -name '*.example' | sort
}

# Baseline of previously-shipped content, one line per path:
# "<relpath><TAB><cksum-crc> <cksum-size>". Records what the last successful
# (non---check) run installed, as source-side content (pre-overlay), so the
# next run compares shipped-then vs shipped-now instead of comparing the
# overlay-modified working tree against the source. Lives under .pipeline/,
# which is never copied from the source and never scanned as shipped.
MANIFEST="$ROOT/.pipeline/shipped-manifest.tsv"
TAB=$(printf '\t')

# Print the stored "crc size" for $2 in manifest $1 (exact path match), or
# fail when the path was never recorded.
manifest_entry() {
    while IFS= read -r line; do
        case "$line" in
            "$2$TAB"*)
                printf '%s\n' "${line#"$2$TAB"}"
                return 0
                ;;
        esac
    done < "$1"
    return 1
}

replaced=0
identical=0
reapplied=0
conflicts=0
stale=0

tmp_shipped=$(mktemp)
tmp_overlay=$(mktemp)
tmp_conflict=$(mktemp)
tmp_roottree=$(mktemp)
tmp_manifest=$(mktemp)
trap 'rm -f "$tmp_shipped" "$tmp_overlay" "$tmp_conflict" "$tmp_roottree" "$tmp_manifest" "${_UPDATE_TMP_SELF:-}"' EXIT INT TERM
list_shipped > "$tmp_shipped"
list_overlay > "$tmp_overlay"

# Conflict detection runs BEFORE any copy, against the recorded baseline —
# not against the working tree, which already holds source-plus-overlay
# from the previous run (comparing those would flag every customized file
# on every update). No baseline yet (installs predating the manifest):
# fall back to working-tree-vs-source once; this run records the baseline.
while IFS= read -r f; do
    [ -n "$f" ] || continue
    rel=${f#./}
    if [ -f "$ROOT/user/$rel" ] && [ -f "$ROOT/$rel" ] && [ -f "$SRC/$rel" ]; then
        if [ -f "$MANIFEST" ]; then
            old=$(manifest_entry "$MANIFEST" "$rel" || true)
            new=$(cksum < "$SRC/$rel")
            if [ -n "$old" ] && [ "$old" != "$new" ]; then
                printf '%s\n' "./$rel" >> "$tmp_conflict"
            fi
        elif ! cmp -s "$ROOT/$rel" "$SRC/$rel"; then
            printf '%s\n' "./$rel" >> "$tmp_conflict"
        fi
    fi
done < "$tmp_overlay"

# Step 1: replace the pack.
while IFS= read -r f; do
    [ -n "$f" ] || continue
    rel=${f#./}
    if [ ! -f "$ROOT/$rel" ]; then
        if [ "$CHECK" -eq 1 ]; then
            echo "NEW       $rel"
        else
            mkdir -p "$ROOT/$(dirname "$rel")"
            cp "$SRC/$rel" "$ROOT/$rel"
            echo "added     $rel"
        fi
        replaced=$((replaced + 1))
    elif cmp -s "$SRC/$rel" "$ROOT/$rel"; then
        identical=$((identical + 1))
    else
        if [ "$CHECK" -eq 1 ]; then
            echo "REPLACE   $rel"
        else
            cp "$SRC/$rel" "$ROOT/$rel"
            echo "replaced  $rel"
        fi
        replaced=$((replaced + 1))
    fi
    sum=$(cksum < "$SRC/$rel")
    printf '%s%s%s\n' "$rel" "$TAB" "$sum" >> "$tmp_manifest"
done < "$tmp_shipped"

# Step 2: reapply the overlay. Step 3: report the precomputed conflicts,
# orphans, and stale files removed upstream.
while IFS= read -r f; do
    [ -n "$f" ] || continue
    rel=${f#./}
    if [ -f "$ROOT/$rel" ]; then
        if [ "$CHECK" -eq 1 ]; then
            echo "REAPPLY   $rel  (overlay wins)"
        else
            cp "$ROOT/user/$rel" "$ROOT/$rel"
            echo "reapplied $rel  (overlay wins)"
        fi
        reapplied=$((reapplied + 1))
        if grep -qxF "./$rel" "$tmp_shipped"; then
            if grep -qxF "./$rel" "$tmp_conflict"; then
                echo "CONFLICT  $rel  (shipped changed under overlay — review, overlay still wins)"
                conflicts=$((conflicts + 1))
            fi
        else
            echo "ORPHAN    $rel  (overlay has no shipped counterpart — kept as-is)"
        fi
    else
        echo "ORPHAN    $rel  (overlay has no shipped counterpart — kept as-is)"
    fi
done < "$tmp_overlay"

# Step 4: files in the working tree that the source no longer ships. Only
# paths the baseline says were previously shipped are prune candidates —
# anything never shipped (local notes, scripts) is reported as UNTRACKED
# and is never deleted. With no baseline yet nothing is deleted either:
# this run records one for next time.
cd "$ROOT" && find . -type f \
    -not -path './.git/*' \
    -not -path './user/*' \
    -not -path './.pipeline/*' \
    -not -path './__pycache__/*' \
    -not -name '*.pyc' | sort > "$tmp_roottree"
while IFS= read -r f; do
    [ -n "$f" ] || continue
    rel=${f#./}
    if ! grep -qxF "$f" "$tmp_shipped"; then
        stale=$((stale + 1))
        if [ -f "$ROOT/user/$rel" ]; then
            echo "STALE     $rel  (removed upstream — overlay-covered, kept; delete by hand if unwanted)"
        elif [ ! -f "$MANIFEST" ]; then
            echo "STALE     $rel  (removed upstream or untracked — no baseline yet, kept)"
        elif manifest_entry "$MANIFEST" "$rel" >/dev/null; then
            if [ "$PRUNE" -eq 1 ] && [ "$CHECK" -eq 0 ]; then
                rm -f "$ROOT/$rel"
                echo "pruned    $rel  (removed upstream — deleted)"
            elif [ "$PRUNE" -eq 1 ]; then
                echo "STALE     $rel  (removed upstream — would prune)"
            else
                echo "STALE     $rel  (removed upstream — kept; re-run with --prune to delete)"
            fi
        else
            echo "UNTRACKED $rel  (never shipped — kept, never pruned)"
        fi
    fi
done < "$tmp_roottree"

# Baseline for the next run: what the source shipped now (pre-overlay
# content), so future conflict/prune decisions compare shipped-then vs
# shipped-now. Entries for paths the source no longer ships but the working
# tree still holds are carried forward — otherwise a plain run would forget
# the removal and a later --prune would misread the file as never-shipped.
# Check mode touches nothing.
if [ "$CHECK" -eq 0 ]; then
    mkdir -p "$ROOT/.pipeline"
    if [ -f "$MANIFEST" ]; then
        while IFS= read -r line; do
            case "$line" in
                *"$TAB"*)
                    rel=${line%%"$TAB"*}
                    if ! grep -qxF "./$rel" "$tmp_shipped" && [ -f "$ROOT/$rel" ]; then
                        printf '%s\n' "$line" >> "$tmp_manifest"
                    fi
                    ;;
            esac
        done < "$MANIFEST"
    fi
    sort -o "$tmp_manifest" "$tmp_manifest"
    mv "$tmp_manifest" "$MANIFEST"
fi

if [ "$CHECK" -eq 1 ]; then
    echo "check: $replaced would replace, $identical identical, $reapplied overlay reapplied, $conflicts conflicts, $stale stale."
else
    echo "done: $replaced replaced, $identical identical, $reapplied overlay reapplied, $conflicts conflicts, $stale stale."
fi
