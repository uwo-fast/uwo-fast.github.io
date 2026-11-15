#!/usr/bin/env python3
"""Turn one fetched project into site pages.

    project-pages.py <dest> <owner/repo> <name>

<dest> is the project's directory under _projects/. The root README and every
Markdown file under docs/ become pages, each with an explicit permalink, so a
URL never depends on how Jekyll treats README or index files. Every other .md
file is deleted rather than published as raw text (#9).

Relative links in those pages are rewritten: a link to another rendered page
goes to that page, and a link to anything else in the repository goes to the
file on GitHub. An image in the repository is pointed at its copy on the site,
since the files beside the pages are still published.
"""

import json
import posixpath
import re
import sys
from pathlib import Path
from urllib.parse import quote, unquote

FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
CODE_SPAN = re.compile(r"(`+).*?\1")
# [text](target "title") and ![alt](target), target optionally in <...>
INLINE = re.compile(r"(!?)\[((?:[^\[\]]|\[[^\]]*\])*)\]\(\s*(<[^>\n]*>|[^)\s]+)((?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*)\)")
REF_DEF = re.compile(r"^( {0,3}\[[^\]]+\]:[ \t]*)(<[^>\n]*>|\S+)(.*)$")
HREF = re.compile(r"(<a\s[^>]*?\bhref=)(\"[^\"]*\"|'[^']*')", re.IGNORECASE)
IMG_SRC = re.compile(r"(<img\s[^>]*?\bsrc=)(\"[^\"]*\"|'[^']*')", re.IGNORECASE)
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
YAML_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*:|\s|- )")


def front_matter_end(lines):
    """Index of the closing `---` when the file opens with a YAML block.

    Only `key:` lines, indented or `- ` continuation lines and blank lines
    count as YAML, so a README that opens with a `---` rule and has another
    one later is not mistaken for front matter.
    """
    if not lines or lines[0].rstrip("\r\n") != "---":
        return None
    for i, raw in enumerate(lines[1:], start=1):
        line = raw.rstrip("\r\n")
        if line == "---":
            return i
        if line == "" or YAML_LINE.match(line):
            continue
        return None
    return None


def first_heading(lines):
    in_fence = None
    for raw in lines:
        line = raw.rstrip("\r\n")
        m = FENCE.match(line)
        if m:
            in_fence = None if in_fence and m.group(1)[0] == in_fence else (in_fence or m.group(1)[0])
            continue
        if in_fence:
            continue
        m = re.match(r"^ {0,3}# +(.+?)(?: +#+)?\s*$", line)
        if m:
            return m.group(1).strip()
    return None


class Project:
    def __init__(self, dest, repo, name):
        self.dest = dest
        self.repo = repo
        self.name = name
        self.dir = dest.name
        self.pages = {}  # repo-relative path -> permalink

    def collect(self):
        for path in sorted(self.dest.rglob("*")):
            rel = path.relative_to(self.dest).as_posix()
            if not path.is_file() or rel.startswith(".git/") or path.suffix.lower() != ".md":
                continue
            if rel.lower() == "readme.md":
                url = f"/projects/{self.dir}/"
            elif rel.startswith("docs/"):
                stem = posixpath.splitext(rel)[0]
                if posixpath.basename(stem).lower() in ("readme", "index"):
                    stem = posixpath.dirname(stem)
                url = f"/projects/{self.dir}/{stem}/"
            else:
                path.unlink()
                continue
            for other, other_url in self.pages.items():
                if other_url == url:
                    sys.exit(f"error: {self.dest / rel} and {self.dest / other} would both be {url}")
            self.pages[rel] = url

    def target(self, here, raw, image):
        """The rewritten link target, or None to leave it as written."""
        angle = raw.startswith("<") and raw.endswith(">")
        target = raw[1:-1] if angle else raw
        if not target or target.startswith(("#", "/")) or SCHEME.match(target):
            return None
        path, _, frag = target.partition("#")
        path = posixpath.normpath(posixpath.join(posixpath.dirname(here), unquote(path)))
        if path == ".." or path.startswith("../"):
            return None
        if image:
            # Pages are served one directory deeper than their source file
            # (docs/a.md -> docs/a/), so a relative image path would miss.
            return quote(f"/projects/{self.dir}/{path}") if (self.dest / path).is_file() else None
        frag = f"#{frag}" if frag else ""
        if path in self.pages:
            return quote(self.pages[path]) + frag
        full = self.dest / path
        if full.is_dir():
            for child, url in self.pages.items():
                if posixpath.dirname(child) == ("" if path == "." else path) and posixpath.basename(child).lower() in ("readme.md", "index.md"):
                    return quote(url) + frag
            kind = "tree"
        elif full.is_file() or path.lower().endswith(".md"):
            kind = "blob"
        else:
            return None
        rest = "" if path == "." else f"/{quote(path)}"
        return f"https://github.com/{self.repo}/{kind}/HEAD{rest}{frag}"

    def rewrite_line(self, here, line):
        spans = [m.span() for m in CODE_SPAN.finditer(line)]

        def in_code(pos):
            return any(a <= pos < b for a, b in spans)

        def inline(m):
            if in_code(m.start()):
                return m.group(0)
            text = INLINE.sub(inline, m.group(2))  # an image inside a link
            new = self.target(here, m.group(3), image=bool(m.group(1)))
            return f"{m.group(1)}[{text}]({m.group(3) if new is None else new}{m.group(4)})"

        def attr(image):
            def sub(m):
                if in_code(m.start()):
                    return m.group(0)
                q = m.group(2)[0]
                new = self.target(here, m.group(2)[1:-1], image=image)
                return m.group(0) if new is None else f"{m.group(1)}{q}{new}{q}"
            return sub

        ref = REF_DEF.match(line)
        if ref:
            new = self.target(here, ref.group(2), image=False)
            return line if new is None else f"{ref.group(1)}{new}{ref.group(3)}"
        line = INLINE.sub(inline, line)
        return IMG_SRC.sub(attr(True), HREF.sub(attr(False), line))

    def render(self, rel, url):
        path = self.dest / rel
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)
        end = front_matter_end(lines)
        head, body = (lines[: end + 1], lines[end + 1 :]) if end is not None else ([], lines)

        out, fence = [], None
        for raw in body:
            line = raw.rstrip("\r\n")
            eol = raw[len(line):]
            m = FENCE.match(line)
            if m:
                char = m.group(1)[0]
                fence = None if fence == char else (fence or char)
                out.append(raw)
                continue
            out.append(raw if fence else self.rewrite_line(rel, line) + eol)

        if rel.lower() == "readme.md":
            title = self.name
        else:
            title = f"{self.name}: {first_heading(body) or posixpath.splitext(rel)[0]}"
        if end is None:
            head = ["---\n", f"title: {json.dumps(title)}\n", f"permalink: {json.dumps(url)}\n", "---\n", "\n"]
        else:
            block = [l.rstrip("\r\n") for l in head[1:-1]]
            extra = []
            if not any(l.startswith("permalink:") for l in block):
                extra.append(f"permalink: {json.dumps(url)}\n")
            if not any(l.startswith("title:") for l in block):
                extra.append(f"title: {json.dumps(title)}\n")
            head = head[:1] + extra + head[1:]
        path.write_text("".join(head + out), encoding="utf-8")
        path.chmod(0o644)

    def run(self):
        self.collect()
        for rel, url in self.pages.items():
            self.render(rel, url)
        return len(self.pages)


if __name__ == "__main__":
    dest, repo, name = sys.argv[1:4]
    count = Project(Path(dest), repo, name).run()
    print(f"  {Path(dest).name}: {count} pages")
