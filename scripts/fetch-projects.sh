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

mapfile -t repos < <(jq -r '.[].repo' _data/projects.json)
mapfile -t names < <(jq -r '.[].name' _data/projects.json)

for i in "${!repos[@]}"; do
    repo="${repos[$i]}"
    dir="$(basename "$repo")"
    dest="_projects/$dir"
    rm -rf "$dest"
    if [ -n "$SRC" ]; then
        mkdir -p "$dest"
        git -C "$SRC/$dir" archive HEAD | tar -x -C "$dest"
    else
        git clone --depth 1 "https://github.com/${repo}.git" "$dest" 2>&1 | sed 's/^/  /'
    fi

    # Jekyll renders a file only when it opens with front matter; a README
    # without it is copied as a static file and its page 404s (#7). Each
    # README becomes index.md with a title and an explicit permalink, so the
    # URL does not depend on how :path treats index files.
    while IFS= read -r -d '' readme; do
        sub="$(dirname "${readme#"$dest"}")"
        sub="${sub#/}"
        if [ -z "$sub" ] || [ "$sub" = "." ]; then
            title="${names[$i]}"
            url="/projects/$dir/"
        else
            title="${names[$i]}: $sub"
            url="/projects/$dir/$sub/"
        fi
        index="$(dirname "$readme")/index.md"
        if [ "$(head -c 3 "$readme")" = "---" ]; then
            mv "$readme" "$index"
            continue
        fi
        {
            printf -- '---\ntitle: "%s"\npermalink: %s\n---\n\n' "${title//\"/\\\"}" "$url"
            cat "$readme"
        } > "$index"
        rm "$readme"
    done < <(find "$dest" -name README.md -not -path '*/.git/*' -print0)
done

echo "fetched ${#repos[@]} projects"
