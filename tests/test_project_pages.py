"""Tests for scripts/project-pages.py.  Run: python3 -m unittest discover tests"""

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "project-pages.py"
spec = importlib.util.spec_from_file_location("project_pages", SCRIPT)
pp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pp)

REPO = "uwo-fast/demo"
GH = f"https://github.com/{REPO}"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dest = Path(self.tmp.name) / "demo"
        self.dest.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text, newline="\n"):
        path = self.dest / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.replace("\n", newline).encode())

    def run_pages(self, name="Demo"):
        return pp.Project(self.dest, REPO, name).run()

    def read(self, rel):
        return (self.dest / rel).read_text()

    def front(self, rel):
        lines = self.read(rel).splitlines()
        end = pp.front_matter_end([l + "\n" for l in lines])
        self.assertIsNotNone(end, f"{rel} has no front matter")
        return {k: v.strip() for k, _, v in (l.partition(":") for l in lines[1:end])}


class Selection(Base):
    def test_readme_and_docs_render_and_other_markdown_is_dropped(self):
        self.write("README.md", "# Demo\n")
        self.write("docs/guide.md", "# Guide\n")
        self.write("docs/README.md", "# Docs\n")
        self.write("docs/sub/deep.md", "text\n")
        self.write("TODO.md", "internal\n")
        self.write("analysis/README.md", "# Analysis\n")
        self.write("data.csv", "a,b\n")
        self.assertEqual(self.run_pages(), 4)
        self.assertFalse((self.dest / "TODO.md").exists())
        self.assertFalse((self.dest / "analysis/README.md").exists())
        self.assertTrue((self.dest / "data.csv").exists())
        self.assertEqual(json.loads(self.front("README.md")["permalink"]), "/projects/demo/")
        self.assertEqual(json.loads(self.front("docs/guide.md")["permalink"]), "/projects/demo/docs/guide/")
        self.assertEqual(json.loads(self.front("docs/README.md")["permalink"]), "/projects/demo/docs/")
        self.assertEqual(json.loads(self.front("docs/sub/deep.md")["permalink"]), "/projects/demo/docs/sub/deep/")

    def run_quiet(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            count = self.run_pages()
        return count, out.getvalue()

    def test_two_files_for_one_url_skip_the_second_with_a_warning(self):
        self.write("README.md", "x\n")
        self.write("docs/README.md", "x\n")
        self.write("docs/index.md", "x\n")
        self.write("docs/a.md", "x\n")
        self.write("docs/a/README.md", "x\n")
        count, out = self.run_quiet()
        self.assertEqual(count, 3)
        self.assertFalse((self.dest / "docs/index.md").exists())
        # The first file in path order keeps the URL.
        self.assertTrue((self.dest / "docs/a/README.md").exists())
        self.assertFalse((self.dest / "docs/a.md").exists())
        self.assertIn("::warning::demo: not publishing docs/index.md", out)
        self.assertIn("::warning::demo: not publishing docs/a.md", out)

    def test_undecodable_file_is_skipped_and_the_rest_render(self):
        self.write("README.md", "[b](docs/bad.md)\n")
        (self.dest / "docs").mkdir()
        (self.dest / "docs/bad.md").write_bytes(b"\xff\xfe\x00bad")
        count, out = self.run_quiet()
        self.assertEqual(count, 1)
        self.assertFalse((self.dest / "docs/bad.md").exists())
        self.assertIn("not UTF-8", out)

    def test_symlink_is_skipped_and_its_target_untouched(self):
        outside = Path(self.tmp.name) / "outside.md"
        outside.write_text("secret\n")
        self.write("README.md", "x\n")
        (self.dest / "docs").mkdir()
        (self.dest / "docs/ln.md").symlink_to(outside)
        count, out = self.run_quiet()
        self.assertEqual(count, 1)
        self.assertFalse((self.dest / "docs/ln.md").is_symlink())
        self.assertEqual(outside.read_text(), "secret\n")
        self.assertIn("symlink", out)

    def test_declared_permalink_is_used_for_links(self):
        self.write("README.md", "[b](docs/b.md)\n")
        self.write("docs/b.md", "---\npermalink: /custom/\n---\nbody\n")
        self.run_pages()
        self.assertIn("[b](/custom/)", self.read("README.md"))


class Titles(Base):
    def test_titles(self):
        self.write("README.md", "# Whatever\n")
        self.write("docs/guide.md", "```\n# not this\n```\n# Build guide ##\n")
        self.write("docs/plain.md", "no heading\n")
        self.write("docs/setext.md", "Setext title\n============\n\ntext\n")
        self.run_pages()
        self.assertEqual(json.loads(self.front("docs/setext.md")["title"]), "Demo: Setext title")
        self.assertEqual(json.loads(self.front("README.md")["title"]), "Demo")
        self.assertEqual(json.loads(self.front("docs/guide.md")["title"]), "Demo: Build guide")
        self.assertEqual(json.loads(self.front("docs/plain.md")["title"]), "Demo: docs/plain")

    def test_title_is_escaped(self):
        self.write("README.md", "x\n")
        self.run_pages(name='C:\\path "q": x')
        self.assertEqual(json.loads(self.front("README.md")["title"]), 'C:\\path "q": x')


class FrontMatter(Base):
    def test_existing_block_keeps_its_keys_and_gains_missing_ones(self):
        self.write("docs/a.md", '---\ntitle: Mine\nnav_order: 2\n---\n\npermalink: /oops/\n')
        self.write("docs/b.md", "---\npermalink: /custom/\n---\nbody\n")
        self.write("README.md", "x\n")
        self.run_pages()
        a = self.front("docs/a.md")
        self.assertEqual(a["title"], "Mine")
        self.assertEqual(json.loads(a["permalink"]), "/projects/demo/docs/a/")
        self.assertIn("permalink: /oops/", self.read("docs/a.md").split("---", 2)[2])
        b = self.front("docs/b.md")
        self.assertEqual(b["permalink"], "/custom/")
        self.assertIn("title", b)
        self.assertEqual(self.read("docs/b.md").split("---", 2)[1].count("permalink:"), 1)

    def test_horizontal_rules_are_not_front_matter(self):
        self.write("README.md", "---\nSome **text** here.\n---\nmore\n")
        self.run_pages()
        text = self.read("README.md")
        self.assertTrue(text.startswith('---\ntitle: "Demo"\npermalink: "/projects/demo/"\n---\n\n---\nSome **text** here.\n---\n'), text)

    def test_crlf_front_matter(self):
        self.write("README.md", "---\ntitle: Win\n---\nbody\n", newline="\r\n")
        self.run_pages()
        self.assertEqual(self.front("README.md")["title"], "Win")


class Links(Base):
    def setUp(self):
        super().setUp()
        self.write("README.md", "# Demo\n")
        self.write("docs/README.md", "# Docs\n")
        self.write("docs/my guide.md", "# Guide\n")
        self.write("analysis/README.md", "# A\n")
        self.write("data.csv", "x\n")
        self.write("LICENSE", "x\n")
        self.write("docs/img.png", "x")

    def page(self, body, rel="docs/page.md"):
        self.write(rel, body)
        self.run_pages()
        return self.read(rel).split("---", 2)[2]

    def test_rendered_pages(self):
        out = self.page(
            "[a](../README.md) [b](README.md#install) [c](<my guide.md>) [d](my%20guide.md)\n"
            "[e](./) [f](../) [g](.) [h](../docs)\n"
        )
        self.assertIn("[a](/projects/demo/)", out)
        self.assertIn("[b](/projects/demo/docs/#install)", out)
        self.assertIn("[c](/projects/demo/docs/my%20guide/)", out)
        self.assertIn("[d](/projects/demo/docs/my%20guide/)", out)
        self.assertIn("[e](/projects/demo/docs/)", out)
        self.assertIn("[f](/projects/demo/)", out)
        self.assertIn("[g](/projects/demo/docs/)", out)
        self.assertIn("[h](/projects/demo/docs/)", out)

    def test_everything_else_goes_to_github(self):
        out = self.page(
            "[a](../data.csv) [b](../analysis/README.md) [c](../analysis/) "
            '[d](../LICENSE "the licence")\n'
            "[![badge](https://img.example/b.svg)](../LICENSE)\n"
        )
        self.assertIn(f"[a]({GH}/blob/HEAD/data.csv)", out)
        self.assertIn(f"[b]({GH}/blob/HEAD/analysis/README.md)", out)
        self.assertIn(f"[c]({GH}/tree/HEAD/analysis)", out)
        self.assertIn(f'[d]({GH}/blob/HEAD/LICENSE "the licence")', out)
        self.assertIn(f"[![badge](https://img.example/b.svg)]({GH}/blob/HEAD/LICENSE)", out)

    def test_left_alone(self):
        body = (
            "![m](missing.png) ![e](https://e.org/i.png) [x](#here) [y](https://e.org/a.md) "
            "[z](mailto:a@b.c) [o](../../outside.md) [n](missing.txt) [r](/abs/)\n"
            "`[c](../README.md)`\n"
            "```\n[f](../README.md)\n```\n"
        )
        self.assertIn(body, self.page(body))

    def test_images_point_at_the_site_copy(self):
        out = self.page('![i](img.png) <img src="./img.png" alt="a"> [![i](img.png)](../data.csv)\n')
        self.assertIn("![i](/projects/demo/docs/img.png)", out)
        self.assertIn('<img src="/projects/demo/docs/img.png" alt="a">', out)
        self.assertIn(f"[![i](/projects/demo/docs/img.png)]({GH}/blob/HEAD/data.csv)", out)

    def test_html_links_and_reference_definitions(self):
        out = self.page('<a href="../data.csv">d</a> <a href=\'my guide.md\'>g</a>\n\n[ref]: ../README.md "t"\n')
        self.assertIn(f'<a href="{GH}/blob/HEAD/data.csv">d</a>', out)
        self.assertIn("<a href='/projects/demo/docs/my%20guide/'>g</a>", out)
        self.assertIn('[ref]: /projects/demo/ "t"', out)

    def test_fence_closes_only_on_a_matching_fence(self):
        out = self.page("````\n```\n[in](../README.md)\n````\n[out](../README.md)\n~~~\n[t](../README.md)\n```\n~~~\n")
        self.assertIn("```\n[in](../README.md)\n````\n", out)
        self.assertIn("[out](/projects/demo/)", out)
        self.assertIn("~~~\n[t](../README.md)\n```\n~~~", out)

    def test_code_spans_after_a_rewrite(self):
        # Each [x](../data.csv) grows by ~38 characters when rewritten, which
        # moves the tags after it into or out of where the code spans were.
        out = self.page(
            '[a](../data.csv)[b](../data.csv) <a href="../data.csv">x</a> `' + "c" * 120 + "`\n"
            '[a](../data.csv)[b](../data.csv)[c](../data.csv) `<a href="../data.csv">`\n'
        )
        self.assertIn(f'<a href="{GH}/blob/HEAD/data.csv">x</a>', out)
        self.assertIn('`<a href="../data.csv">`', out)

    def test_query_strings_are_kept(self):
        out = self.page("![i](img.png?v=2) [q](../data.csv?raw=1#L2) [p](../README.md?x=1#top)\n")
        self.assertIn("![i](/projects/demo/docs/img.png?v=2)", out)
        self.assertIn(f"[q]({GH}/blob/HEAD/data.csv?raw=1#L2)", out)
        self.assertIn("[p](/projects/demo/?x=1#top)", out)

    def test_reference_style_images(self):
        out = self.page("![alt][i] ![s]\n\n[i]: img.png\n[s]: img.png\n[l]: ../data.csv\n")
        self.assertIn("[i]: /projects/demo/docs/img.png", out)
        self.assertIn("[s]: /projects/demo/docs/img.png", out)
        self.assertIn(f"[l]: {GH}/blob/HEAD/data.csv", out)

    def test_parentheses_in_a_target(self):
        self.write("docs/foo_(bar).md", "x\n")
        out = self.page("[f](foo_(bar).md)\n")
        self.assertIn("[f](/projects/demo/docs/foo_%28bar%29/)", out)

    def test_root_readme_links(self):
        self.write("README.md", "[d](docs/README.md) [g](docs/my%20guide.md#s) [t](TODO.md)\n")
        self.write("TODO.md", "x\n")
        self.run_pages()
        out = self.read("README.md")
        self.assertIn("[d](/projects/demo/docs/)", out)
        self.assertIn("[g](/projects/demo/docs/my%20guide/#s)", out)
        self.assertIn(f"[t]({GH}/blob/HEAD/TODO.md)", out)


if __name__ == "__main__":
    unittest.main()
