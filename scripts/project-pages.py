#!/usr/bin/env python3
"""Turn one fetched project into site pages.

    project-pages.py <clone> <owner/repo> <name> <content-root> <public-root> [card-image] [assets-root]

<clone> is a throwaway copy of the project. The root README and every Markdown
file under docs/ become pages, each with an explicit URL, so a URL never
depends on how the site generator treats README or index files. Every other .md
file is dropped rather than published as raw text (#9).

Relative links in those pages are rewritten: a link to another rendered page
goes to that page, and a link to anything else in the repository goes to the
file on GitHub. An image in the repository is pointed at its copy on the site,
and only those images are copied there (#23).

A file that cannot become a page (two files for one URL, not UTF-8, a symlink)
is skipped with a warning rather than failing the fetch: the same build keeps
the lab sign pages current, and one project's docs must not hold that up.
"""

import json
import posixpath
import re
import sys
from pathlib import Path
from urllib.parse import quote, unquote

FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
CODE_SPAN = re.compile(r"(`+).*?\1")
# [text](target "title") and ![alt](target); the target may be in <...> and
# may hold one level of parentheses, as in foo_(bar).md
INLINE = re.compile(
    r"(!?)\[((?:[^\[\]]|\[[^\]]*\])*)\]"
    r"\(\s*(<[^>\n]*>|(?:[^()\s]|\([^()\s]*\))+)((?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*)\)"
)
REF_DEF = re.compile(r"^( {0,3}\[([^\]]+)\]:[ \t]*)(<[^>\n]*>|\S+)(.*)$")
REF_IMAGE = re.compile(r"!\[([^\]]*)\](?:\[([^\]]*)\])?")
HREF = re.compile(r"(<a\s[^>]*?\bhref=)(\"[^\"]*\"|'[^']*')", re.IGNORECASE)
IMG_SRC = re.compile(r"(<img\s[^>]*?\bsrc=)(\"[^\"]*\"|'[^']*')", re.IGNORECASE)
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
YAML_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*:|\s|- )")
TARGET = re.compile(r"^([^?#]*)(\?[^#]*)?(#.*)?$")


def warn(message):
    # A GitHub Actions annotation in CI, a plain line locally.
    print(f"::warning::{message}")


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


def fence_step(fence, line):
    """(new fence state, whether this line is a fence line).

    A fence closes only on the same character, at least as long as the one
    that opened it, with nothing after it.
    """
    m = FENCE.match(line)
    if not m:
        return fence, False
    mark = m.group(1)
    if fence is None:
        return (mark[0], len(mark)), True
    if mark[0] == fence[0] and len(mark) >= fence[1] and not m.group(2).strip():
        return None, True
    return fence, False


def code_lines(lines):
    """Yield (line, in_code) for each line, without its line ending."""
    fence = None
    for raw in lines:
        line = raw.rstrip("\r\n")
        fence, is_fence = fence_step(fence, line)
        yield line, bool(fence) or is_fence


def first_heading(lines):
    previous = None
    for line, code in code_lines(lines):
        if code:
            previous = None
            continue
        m = re.match(r"^ {0,3}# +(.+?)(?: +#+)?\s*$", line)
        if m:
            return m.group(1).strip()
        if previous and re.match(r"^ {0,3}=+\s*$", line):
            return previous.strip()
        previous = line if line.strip() else None
    return None


def label_key(label):
    """A reference label as kramdown matches it: case and whitespace folded."""
    return " ".join(label.split()).lower()


def yaml_scalar(value):
    """A one-line YAML scalar as written here: JSON-quoted, single-quoted or plain."""
    value = value.strip()
    if value[:1] == '"':
        try:
            return json.loads(value)
        except ValueError:
            return value.strip('"')
    if value[:1] == "'" and value[-1:] == "'":
        return value[1:-1].replace("''", "'")
    return value


def declared_permalink(lines):
    end = front_matter_end(lines)
    for raw in lines[1:end] if end else []:
        m = re.match(r"^permalink:\s*(.+?)\s*$", raw.rstrip("\r\n"))
        if m:
            value = m.group(1)
            return value[1:-1] if value[:1] in "\"'" and value[-1:] == value[:1] else value
    return None


class Project:
    def __init__(self, dest, repo, name):
        self.dest = dest
        self.repo = repo
        self.name = name
        self.dir = dest.name
        self.pages = {}  # repo-relative path -> permalink
        self.texts = {}
        self.images = set()  # repo-relative paths of images the pages use

    def skip(self, path, why):
        warn(f"{self.dir}: not publishing {path.relative_to(self.dest).as_posix()}: {why}")
        path.unlink()

    def collect(self):
        for path in sorted(self.dest.rglob("*")):
            rel = path.relative_to(self.dest).as_posix()
            if rel.startswith(".git/") or path.suffix.lower() != ".md":
                continue
            if path.is_symlink():
                self.skip(path, "it is a symlink")
                continue
            if not path.is_file():
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
            try:
                text = path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                self.skip(path, "it is not UTF-8")
                continue
            url = declared_permalink(text.splitlines(keepends=True)) or url
            clash = next((other for other, u in self.pages.items() if u == url), None)
            if clash:
                self.skip(path, f"{clash} already has the URL {url}")
                continue
            self.pages[rel] = url
            self.texts[rel] = text

    def target(self, here, raw, image):
        """The rewritten link target, or None to leave it as written."""
        angle = raw.startswith("<") and raw.endswith(">")
        target = raw[1:-1] if angle else raw
        if not target or target.startswith(("#", "/")) or SCHEME.match(target):
            return None
        path, query, frag = TARGET.match(target).groups()
        query, frag = query or "", frag or ""
        path = posixpath.normpath(posixpath.join(posixpath.dirname(here), unquote(path)))
        if path == ".." or path.startswith("../"):
            return None
        if image:
            # Pages are served one directory deeper than their source file
            # (docs/a.md -> docs/a/), so a relative image path would miss.
            full = self.dest / path
            if full.is_file() and not full.is_symlink():
                self.images.add(path)
                return quote(f"/projects/{self.dir}/{path}") + query + frag
            return None
        if path in self.pages:
            return quote(self.pages[path]) + query + frag
        full = self.dest / path
        if full.is_dir():
            for child, url in self.pages.items():
                if posixpath.dirname(child) == ("" if path == "." else path) and posixpath.basename(child).lower() in ("readme.md", "index.md"):
                    return quote(url) + query + frag
            kind = "tree"
        elif full.is_file() or path.lower().endswith(".md"):
            kind = "blob"
        else:
            return None
        rest = "" if path == "." else f"/{quote(path)}"
        return f"https://github.com/{self.repo}/{kind}/HEAD{rest}{query}{frag}"

    def rewrite_line(self, here, line, image_labels):
        ref = REF_DEF.match(line)
        if ref:
            image = label_key(ref.group(2)) in image_labels
            new = self.target(here, ref.group(3), image=image)
            return line if new is None else f"{ref.group(1)}{new}{ref.group(4)}"

        def outside_code(sub):
            # Code-span positions are taken afresh for each pass, since the
            # pass before may have changed the line's length.
            def run(pattern, text):
                spans = [m.span() for m in CODE_SPAN.finditer(text)]
                return pattern.sub(lambda m: m.group(0) if any(a <= m.start() < b for a, b in spans) else sub(m), text)
            return run

        def inline(m):
            text = INLINE.sub(inline, m.group(2))  # an image inside a link
            new = self.target(here, m.group(3), image=bool(m.group(1)))
            return f"{m.group(1)}[{text}]({m.group(3) if new is None else new}{m.group(4)})"

        def attr(image):
            def sub(m):
                q = m.group(2)[0]
                new = self.target(here, m.group(2)[1:-1], image=image)
                return m.group(0) if new is None else f"{m.group(1)}{q}{new}{q}"
            return sub

        line = outside_code(inline)(INLINE, line)
        line = outside_code(attr(False))(HREF, line)
        return outside_code(attr(True))(IMG_SRC, line)

    def render(self, rel, url):
        path = self.dest / rel
        lines = self.texts[rel].splitlines(keepends=True)
        end = front_matter_end(lines)
        head, body = (lines[: end + 1], lines[end + 1 :]) if end is not None else ([], lines)

        image_labels = set()
        for line, code in code_lines(body):
            if not code:
                for m in REF_IMAGE.finditer(line):
                    if not line[m.end():m.end() + 1] == "(":
                        image_labels.add(label_key(m.group(2) or m.group(1)))

        out = []
        for raw, (line, code) in zip(body, code_lines(body)):
            eol = raw[len(line):]
            out.append(raw if code else self.rewrite_line(rel, line, image_labels) + eol)

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

    def inside(self, rel):
        """The file at rel, if it really lies inside the project (no symlink out)."""
        root = self.dest.resolve()
        full = (self.dest / rel).resolve()
        if full != root and root in full.parents and full.is_file():
            return full
        return None

    def publish(self, content, public, card=None, assets=None):
        """Copy the rendered pages and the images they use into the site.

        Each page goes to <content>/<url>/index.md with Starlight front matter: its
        title, and its URL as the slug, so the URL does not depend on where the
        file sits. Its own front matter is not carried over, and a leading
        level-1 heading is dropped, because Starlight prints the title as one.
        Only images a page references are copied to <public>; every other file
        in the repository stays on GitHub (#23). The card image, if any, goes to
        <assets>/<dir><ext> for the home page to optimise.
        """
        for rel, url in self.pages.items():
            lines = (self.dest / rel).read_text(encoding="utf-8").splitlines(keepends=True)
            end = front_matter_end(lines)
            head, body = lines[: end + 1], lines[end + 1 :]
            title = next((yaml_scalar(l.split(":", 1)[1]) for l in head if l.startswith("title:")), self.name)
            for i, (line, code) in enumerate(code_lines(body)):
                if code or not line.strip():
                    if code:
                        break
                    continue
                if re.match(r"^ {0,3}# +", line):
                    rest = body[i + 1 :]
                    while rest and not rest[0].strip():
                        rest = rest[1:]
                    body = body[:i] + rest
                break
            slug = url.strip("/")
            out = content / slug / "index.md"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(
                "---\n" f"title: {json.dumps(title)}\n" f"slug: {json.dumps(slug)}\n" "---\n" + "".join(body),
                encoding="utf-8",
            )
        copied = 0
        for rel in sorted(self.images):
            src = self.inside(rel)
            if src is None:
                warn(f"{self.dir}: not copying {rel}: it is not a file inside the repository")
                continue
            out = public / "projects" / self.dir / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(src.read_bytes())
            copied += 1
        if card:
            src = self.inside(card)
            if src is None:
                warn(f"{self.dir}: card image {card} is not a file inside the repository")
            else:
                assets.mkdir(parents=True, exist_ok=True)
                (assets / f"{self.dir}{src.suffix.lower()}").write_bytes(src.read_bytes())
        return copied


if __name__ == "__main__":
    # project-pages.py <clone> <owner/repo> <name> <content-root> <public-root> [card-image] [assets-root]
    args = sys.argv[1:]
    src, repo, name, content, public = args[:5]
    card = args[5] if len(args) > 5 and args[5] else None
    assets = Path(args[6]) if len(args) > 6 else None
    project = Project(Path(src), repo, name)
    count = project.run()
    images = project.publish(Path(content), Path(public), card, assets)
    print(f"  {Path(src).name}: {count} pages, {images} images")
