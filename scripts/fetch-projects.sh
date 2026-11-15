#!/usr/bin/env bash
# Pull each project in _data/projects.json into the Jekyll `projects` collection.
#
# Runs in CI and locally, like fetch-signs.sh, so a page cannot build in one
# place and 404 in the other.
#
#   scripts/fetch-projects.sh                       # clone from GitHub
#   PROJECTS_SRC=.. scripts/fetch-projects.sh       # use local checkouts, ../<repo>
set -euo pipefail

SRC="${PROJECTS_SRC:-}"

while IFS= read -r entry; do
    repo="$(jq -r '.repo' <<<"$entry")"
    name="$(jq -r '.name // empty' <<<"$entry")"
    dir="$(basename "$repo")"
    dest="_projects/$dir"
    rm -rf "$dest"
    if [ -n "$SRC" ]; then
        mkdir -p "$dest"
        git -C "$SRC/$dir" archive HEAD | tar -x -C "$dest"
    else
        git clone --depth 1 "https://github.com/${repo}.git" "$dest" 2>&1 | sed 's/^/  /'
    fi

    # The README and docs/ become pages with their links rewritten; any other
    # Markdown is dropped (#7, #9).
    python3 "$(dirname "$0")/project-pages.py" "$dest" "$repo" "${name:-$dir}"
done < <(jq -c '.[]' _data/projects.json)

echo "fetched $(jq length _data/projects.json) projects"
