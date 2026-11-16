#!/usr/bin/env bash
# Pull the FAST lab signs and equipment records into the site's content.
#
# Runs in CI and locally, on purpose. Issue #2 was pages that built locally and
# 404ed on Pages; the way to not repeat that is one code path for both.
#
#   scripts/fetch-signs.sh                    # clone from GitHub
#   SIGNS_SRC=../uwo-fast scripts/fetch-signs.sh   # use a local checkout
set -euo pipefail

REPO="${SIGNS_REPO:-uwo-fast/uwo-fast}"
SRC="${SIGNS_SRC:-}"
CLONE_DIR=""

if [ -z "$SRC" ]; then
    CLONE_DIR="$(mktemp -d)"
    trap 'rm -rf "$CLONE_DIR"' EXIT
    git clone --depth 1 "https://github.com/${REPO}.git" "$CLONE_DIR" 2>&1 | sed 's/^/  /'
    SRC="$CLONE_DIR"
fi

[ -d "$SRC/lab-signs" ] || { echo "no lab-signs/ in $SRC" >&2; exit 1; }

SIGNS=src/content/docs/signs
EQUIP=src/content/docs/equipment
rm -f "$SIGNS"/*.md
rm -rf "$EQUIP"
mkdir -p "$SIGNS" "$EQUIP"

# Write one document with the site's front matter: its URL as the slug (the
# repo's own slug is only the last segment), what kind of page it is, and the
# date it last changed. The leading level-1 heading repeats the title, which
# the page prints anyway, so it is dropped.
emit() { # <src> <out> <kind> <slug> <updated>
    awk -v kind="$3" -v slug="$4" -v d="$5" '
        NR == 1 && /^---$/ { fm = 1; print; print "kind: \"" kind "\""; print "slug: \"" slug "\""
                             if (d != "") print "last_updated: \"" d "\""; next }
        fm && /^---$/ { fm = 0; body = 1; print; next }
        fm && /^(slug|last_updated|kind):/ { next }
        body && !h1done && /^# / { h1done = 1; next }
        body && !h1done && /[^[:space:]]/ { h1done = 1 }
        { print }
    ' "$1" > "$2"
}

# The URL is a contract: /signs/<slug>/ is printed onto QR codes that cannot be
# recalled. The page takes that path from the slug, so a filename that has
# drifted from its slug is a sign whose source and URL disagree. Fail instead.
fail=0
for f in "$SRC"/lab-signs/*.md; do
    b="$(basename "$f")"
    case "$b" in README.md | AUTHORING.md | TODO.md | _*) continue ;; esac

    slug="$(sed -n 's/^slug: *"\(.*\)" *$/\1/p' "$f" | head -1)"
    if [ -z "$slug" ]; then
        echo "error: $b has no slug in its front matter" >&2
        fail=1
        continue
    fi
    if [ "$slug" != "${b%.md}" ]; then
        echo "error: $b declares slug '$slug'; filename and slug must match, because" >&2
        echo "       /signs/<slug>/ is printed onto QR codes" >&2
        fail=1
        continue
    fi

    # Mirror the date the PDF footer shows, which the sign build takes from git.
    updated="$(git -C "$SRC" log -1 --format=%cs -- "lab-signs/$b" 2>/dev/null || true)"
    emit "$f" "$SIGNS/$b" sign "signs/$slug" "$updated"
done
[ "$fail" -eq 0 ] || exit 1

if [ -d "$SRC/equipment" ]; then
    for f in "$SRC"/equipment/*.md; do
        b="$(basename "$f")"
        case "$b" in README.md) continue ;; esac
        slug="$(sed -n 's/^slug: *"\(.*\)" *$/\1/p' "$f" | head -1)"
        emit "$f" "$EQUIP/$b" equipment "equipment/${slug:-${b%.md}}" ""
    done
fi

# Links between documents are written for the repo, where they are relative
# paths to .md files. On the site those 404. Rewrite them to the published URL.
# Absolute https:// links are left alone.
#
# The site is served at the domain root (an organisation Pages site). If it ever
# moves under a path prefix, this is the one place to change.
sed -i -E \
    -e 's#\]\(\.\./lab-signs/([a-z0-9-]+)\.md\)#](/signs/\1/)#g' \
    -e 's#\]\(\.\./equipment/([a-z0-9-]+)\.md\)#](/equipment/\1/)#g' \
    -e 's#\]\(([a-z0-9-]+)\.md\)#](/signs/\1/)#g' \
    "$SIGNS"/*.md
sed -i -E \
    -e 's#\]\(\.\./lab-signs/([a-z0-9-]+)\.md\)#](/signs/\1/)#g' \
    -e 's#\]\(([a-z0-9-]+)\.md\)#](/equipment/\1/)#g' \
    "$EQUIP"/*.md

echo "fetched $(find "$SIGNS" -name '*.md' | wc -l) signs, $(find "$EQUIP" -name '*.md' | wc -l) equipment records"
