#!/usr/bin/env python3
"""Fail if the built site is missing a URL it must serve.

    check-urls.py <dist>

Reads scripts/required-urls.txt (the pages behind printed QR codes, and the
top-level pages) and src/data/projects.json (one page per listed project), and
checks that <dist> holds an index.html for each.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def required():
    urls = []
    for line in (ROOT / "scripts" / "required-urls.txt").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line)
    for project in json.loads((ROOT / "src" / "data" / "projects.json").read_text()):
        urls.append(f"/projects/{project['repo'].split('/')[-1]}/")
    return urls


def missing(dist, urls):
    return [u for u in urls if not (dist / u.strip("/") / "index.html").is_file()]


if __name__ == "__main__":
    dist = Path(sys.argv[1])
    urls = required()
    gone = missing(dist, urls)
    for url in gone:
        print(f"::error::{url} is not in the built site")
    print(f"{len(urls) - len(gone)} of {len(urls)} required URLs present")
    sys.exit(1 if gone else 0)
