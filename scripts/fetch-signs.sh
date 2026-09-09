#!/usr/bin/env bash
# Pull the FAST lab signs and equipment records into Jekyll collections.
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

rm -rf _signs _equipment
mkdir -p _signs _equipment

# The URL is a contract: /signs/<slug>/ is printed onto QR codes that cannot be
# recalled. Jekyll derives that path from the filename, so a filename that has
# drifted from its slug would silently move a published sign. Fail instead.
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
    if [ -n "$updated" ]; then
        awk -v d="$updated" 'NR==1 && /^---$/ {print; print "last_updated: \"" d "\""; next} {print}' \
            "$f" > "_signs/$b"
    else
        cp "$f" "_signs/$b"
    fi
done
[ "$fail" -eq 0 ] || exit 1

if [ -d "$SRC/equipment" ]; then
    for f in "$SRC"/equipment/*.md; do
        b="$(basename "$f")"
        case "$b" in README.md) continue ;; esac
        cp "$f" "_equipment/$b"
    done
fi

# Links between documents are written for the repo, where they are relative
# paths to .md files. On the site those 404. Rewrite them to the published URL.
# Absolute https:// links are left alone.
#
# baseurl is empty for an organisation Pages site served at the domain root, and
# the workflow passes an empty base_path to match. If the site ever moves under a
# path prefix, this is the one place to change.
sed -i -E \
    -e 's#\]\(\.\./lab-signs/([a-z0-9-]+)\.md\)#](/signs/\1/)#g' \
    -e 's#\]\(\.\./equipment/([a-z0-9-]+)\.md\)#](/equipment/\1/)#g' \
    -e 's#\]\(([a-z0-9-]+)\.md\)#](/signs/\1/)#g' \
    _signs/*.md
sed -i -E \
    -e 's#\]\(\.\./lab-signs/([a-z0-9-]+)\.md\)#](/signs/\1/)#g' \
    -e 's#\]\(([a-z0-9-]+)\.md\)#](/equipment/\1/)#g' \
    _equipment/*.md

echo "fetched $(find _signs -name '*.md' | wc -l) signs, $(find _equipment -name '*.md' | wc -l) equipment records"
