#!/bin/sh
# update.sh — replace shipped pack files from a fresh source tree, then reapply the user/ overlay.
#
# Contract (see UPDATE.md): shipped files are read-only; user edits live in
# user/; this script never writes into user/.
#
# Usage:
#   sh scripts/update.sh --source <fresh-tree> [--check]
#
#   <fresh-tree>  fresh clone/export of the pack at the target version.
#   --check       dry run: report what would change, touch nothing.
#
# Step 1 (replace the pack): every file in <fresh-tree> except user/, .git/,
# .pipeline/, and caches is copied over the working tree.
# Step 2 (reapply the overlay): each user/<path> (minus README/examples) is
# copied back over its shipped mirror path.
# Step 3 (report): overlay files whose shipped counterpart changed underneath
# them are flagged as conflicts for review. The overlay still wins.

set -eu

SRC=""
CHECK=0

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
        -h|--help)
            sed -n '2,/^$/p' "$0"
            echo "Usage: sh scripts/update.sh --source <fresh-tree> [--check]"
            exit 0
            ;;
        *)
            echo "update.sh: unknown argument '$1'" >&2
            echo "Usage: sh scripts/update.sh --source <fresh-tree> [--check]" >&2
            exit 1
            ;;
    esac
done

if [ -z "$SRC" ]; then
    echo "update.sh: --source <fresh-tree> is required" >&2
    exit 1
fi

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
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

replaced=0
identical=0
reapplied=0
conflicts=0

tmp_shipped=$(mktemp)
tmp_overlay=$(mktemp)
trap 'rm -f "$tmp_shipped" "$tmp_overlay"' EXIT INT TERM
list_shipped > "$tmp_shipped"
list_overlay > "$tmp_overlay"

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
done < "$tmp_shipped"

# Step 2: reapply the overlay. Step 3: flag conflicts where the shipped
# counterpart changed underneath an overlay file in this same update.
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
            if ! cmp -s "$SRC/$rel" "$ROOT/user/$rel"; then
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

if [ "$CHECK" -eq 1 ]; then
    echo "check: $replaced would replace, $identical identical, $reapplied overlay reapplied, $conflicts conflicts."
else
    echo "done: $replaced replaced, $identical identical, $reapplied overlay reapplied, $conflicts conflicts."
fi
