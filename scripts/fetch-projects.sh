#!/usr/bin/env bash
# Render each project in src/data/projects.json into the site.
#
# Runs in CI and locally, like fetch-signs.sh, so a page cannot build in one
# place and 404 in the other.
#
#   scripts/fetch-projects.sh                       # clone from GitHub
#   PROJECTS_SRC=.. scripts/fetch-projects.sh       # use local checkouts, ../<repo>
#
# Each project is copied into a throwaway directory, and project-pages.py writes
# its README and docs/ pages into src/content/docs/projects/<repo>/ and the
# images those pages use into public/projects/<repo>/. Nothing else from the
# repository is published (#23).
set -euo pipefail

SRC="${PROJECTS_SRC:-}"
CONTENT=src/content/docs
PUBLIC=public
ASSETS=src/assets/projects
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

rm -rf public/projects "$ASSETS"
find "$CONTENT/projects" -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} +

while IFS= read -r entry; do
    repo="$(jq -r '.repo' <<<"$entry")"
    name="$(jq -r '.name // empty' <<<"$entry")"
    image="$(jq -r '.image // empty' <<<"$entry")"
    dir="$(basename "$repo")"
    clone="$WORK/$dir"
    if [ -n "$SRC" ]; then
        mkdir -p "$clone"
        git -C "$SRC/$dir" archive HEAD | tar -x -C "$clone"
    else
        git clone --depth 1 "https://github.com/${repo}.git" "$clone" 2>&1 | sed 's/^/  /'
    fi

    python3 "$(dirname "$0")/project-pages.py" "$clone" "$repo" "${name:-$dir}" \
        "$CONTENT" "$PUBLIC" "$image" "$ASSETS"
done < <(jq -c '.[]' src/data/projects.json)

echo "fetched $(jq length src/data/projects.json) projects"
