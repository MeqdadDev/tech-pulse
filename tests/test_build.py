import re
import tempfile
import unittest
from pathlib import Path

from build import build

ROOT = Path(__file__).resolve().parent.parent


def issue(range_, headline="Headline", summary="Summary.", text="Text.", note=None, url="https://example.com/a"):
    extra = f"\n{note}\n" if note else ""
    return f"# TECH PULSE — {range_}\n\n> {summary}\n\n## AI\n\n- **[{headline}]({url})** — {text}\n{extra}\n---\n"


NOV25 = ("2026-11-25.md", issue("NOV 23 – 25, 2026"))
NOV27 = ("2026-11-27.md", issue("NOV 25 – 27, 2026"))
DEC01 = ("2026-12-01.md", issue("NOV 29 – DEC 01, 2026"))
JAN02 = ("2027-01-02.md", issue("DEC 31 – JAN 02, 2027"))


class Build(unittest.TestCase):
    def run_build(self, *files):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "issues").mkdir()
        for name, text in files:
            (root / "issues" / name).write_text(text, encoding="utf-8")
        build(root / "issues", root / "out", ROOT / "site" / "style.css")
        self.out = root / "out"

    def page(self, path):
        return (self.out / path).read_text(encoding="utf-8")

    def test_newest_first(self):
        self.run_build(NOV25, NOV27)
        html = self.page("2026/11.html")
        self.assertLess(html.index('id="entry-2026-11-27"'), html.index('id="entry-2026-11-25"'))

    def test_new_month(self):
        self.run_build(NOV27, DEC01)
        home = self.page("index.html")
        self.assertIn('id="entry-2026-12-01"', home)
        self.assertNotIn('id="entry-2026-11-27"', home)
        self.assertTrue((self.out / "2026/12.html").exists())
        self.assertIn('href="12.html"', self.page("2026/11.html"))

    def test_year_change(self):
        self.run_build(DEC01, JAN02)
        self.assertIn('href="../2027/01.html"', self.page("2026/12.html"))
        self.assertIn('href="../2026/12.html"', self.page("2027/01.html"))

    def test_all_links_resolve(self):
        self.run_build(NOV25, NOV27, DEC01, JAN02)
        pages = list(self.out.rglob("*.html"))
        self.assertEqual(len(pages), 4)
        for page in pages:
            html = page.read_text(encoding="utf-8")
            for link in re.findall(r'href="([^"]+)"', html):
                if link.startswith("http"):
                    continue
                if link.startswith("#"):
                    self.assertIn(f'id="{link[1:]}"', html)
                else:
                    self.assertTrue((page.parent / link).resolve().is_file(), f"{page.name}: {link}")

    def test_escapes_html(self):
        bad = "<script>x</script>"
        self.run_build(("2026-11-27.md", issue(
            "NOV 25 – 27, 2026", headline=bad, summary=bad, text=f"{bad} and `a<b`", note=bad,
            url='https://example.com/"onmouseover="x')))
        html = self.page("index.html")
        self.assertNotIn("<script", html)
        self.assertEqual(html.count("&lt;script&gt;"), 4)
        self.assertIn("<code>a&lt;b</code>", html)
        self.assertNotIn('"onmouseover="', html)

    def test_brand(self):
        self.run_build(NOV27)
        html = self.page("index.html")
        for text in ("Meqdad Darwish", "Tech Pulse",
                     "AI, robotics, software, startups and hardware, in plain language, every two days.",
                     "https://www.linkedin.com/in/meqdad-darwish/", "https://twitter.com/MeqdadDev",
                     "https://github.com/MeqdadDev", "https://www.instagram.com/meqdad.dev/",
                     "Each item links to its source. Check it before relying on figures.",
                     'rel="noopener"'):
            self.assertIn(text, html)
        self.assertNotIn("Purpose", html)

    def test_inline_links_and_bold_in_text(self):
        text = "See [BBC](https://example.com/b?x=1&y=2) and **check yours**. [bad](javascript:alert(1))"
        self.run_build(("2026-11-27.md", issue("NOV 25 – 27, 2026", text=text)))
        html = self.page("index.html")
        self.assertIn('<a href="https://example.com/b?x=1&amp;y=2" target="_blank" rel="noopener">BBC</a>', html)
        self.assertIn("<strong>check yours</strong>", html)
        self.assertNotIn('href="javascript', html)

    def test_empty_or_bad_input_fails(self):
        for files in ((), (("latest.md", NOV27[1]),), (("2026-11-27.md", "oops"),)):
            with self.subTest(files=files):
                with self.assertRaises(ValueError) as ctx:
                    self.run_build(*files)
                if files:
                    self.assertIn(files[0][0], str(ctx.exception))
