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

# Jekyll renders a file only when it opens with front matter; a README without
# it is copied as a static file and its page 404s (#7). Every README becomes
# index.md with an explicit permalink, so the URL never depends on how :path
# treats index files. jq writes the values as JSON strings, which are valid
# YAML whatever characters a name or directory holds.
has_front_matter() {
    [ "$(head -n 1 "$1")" = "---" ] && tail -n +2 "$1" | grep -qx -- "---"
}

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

    while IFS= read -r -d '' readme; do
        sub="$(dirname "${readme#"$dest"}")"
        sub="${sub#/}"
        [ "$sub" = "." ] && sub=""
        title="${name:-$dir}${sub:+: $sub}"
        url="/projects/$dir/${sub:+$sub/}"
        index="$(dirname "$readme")/index.md"
        tmp="$(mktemp)"
        if has_front_matter "$readme"; then
            # Keep the README's own front matter; add a permalink and a title
            # after its opening line where it sets neither.
            { head -n 1 "$readme"
              grep -q '^permalink:' "$readme" || jq -rn --arg u "$url" '"permalink: \($u | tojson)"'
              grep -q '^title:' "$readme" || jq -rn --arg t "$title" '"title: \($t | tojson)"'
              tail -n +2 "$readme"; } > "$tmp"
        else
            { echo "---"
              jq -rn --arg t "$title" --arg u "$url" '"title: \($t | tojson)\npermalink: \($u | tojson)"'
              echo "---"
              echo
              cat "$readme"; } > "$tmp"
        fi
        rm "$readme"
        mv "$tmp" "$index"
    done < <(find "$dest" -iname README.md -not -path '*/.git/*' -print0)
done < <(jq -c '.[]' _data/projects.json)

echo "fetched $(jq length _data/projects.json) projects"
