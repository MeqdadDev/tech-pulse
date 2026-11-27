import datetime as dt
import unittest

from pulse import parse_issue
from tools.import_gist import convert_gist
from tools.import_log import convert_log

HEAD = "# Tech Pulse — Oct. Tech News\n\nA running log, for the team.\n\n---\n\n"
LINK = "**[T](https://example.com/a_(b))**"


def gist(body, heading="# TECH PULSE — NOV 23 – 25, 2026"):
    return f"{HEAD}{heading}\n\n> Summary.\n\n## AI\n\n{body}\n\n---\n"


def only(markdown):
    ((date, text),) = convert_gist(markdown).items()
    return date, text, parse_issue(text, date)


class Gist(unittest.TestCase):
    def test_item_forms_become_one_line(self):
        for body in (f"- {LINK} — Text.", f"{LINK} — Text.", f"{LINK}\nText.", f"- {LINK}\n\nText."):
            with self.subTest(body=body):
                date, text, issue = only(gist(body))
                self.assertEqual(date, dt.date(2026, 11, 25))
                self.assertIn(f"- {LINK} — Text.\n", text)
                self.assertEqual(issue.sections[0].notes, [])

    def test_text_without_dash_separator(self):
        for rest, expected in ((", an agentic model.", "An agentic model."),
                               (" after the ruling.", "After the ruling."),
                               (" (Oct 18) — The launch.", "(Oct 18) The launch.")):
            with self.subTest(rest=rest):
                self.assertEqual(only(gist(f"- {LINK}{rest}"))[2].sections[0].items[0].text, expected)

    def test_note_forms(self):
        body = f"- {LINK} — Text.\n\nPlain note.\n\n- Dashed note.\n\n*Italic note.*"
        self.assertEqual(only(gist(body))[2].sections[0].notes,
                         ["Plain note.", "Dashed note.", "Italic note."])

    def test_heading_and_section_variants(self):
        for heading, section in (("## Tech Pulse — NOV 23 – 25, 2026", "### Software"),
                                 ("## Nov 23 – Nov 25, 2026", "## Software & Dev Tools"),
                                 ("# Tech Pulse — Nov 23–25, 2026", "## 💻 Software / Dev Tools")):
            with self.subTest(heading=heading, section=section):
                text = gist(f"- {LINK} — Text.", heading).replace("## AI", section)
                _, converted, issue = only(text)
                self.assertEqual(issue.sections[0].name, "Software / Dev Tools")
                self.assertNotIn("running log", converted)

    def test_duplicate_date_stops(self):
        one = gist(f"- {LINK} — Text.")
        with self.assertRaisesRegex(ValueError, "2026-11-25"):
            convert_gist(one + one[len(HEAD):])

    def test_skip_drops_one_duplicate(self):
        one = gist(f"- {LINK} — Text.")
        result = convert_gist(one + one[len(HEAD):].replace("Text.", "Second."), skip={1})
        self.assertIn("Text.", result[dt.date(2026, 11, 25)])

    def test_headline_without_text_stops(self):
        with self.assertRaises(ValueError):
            convert_gist(gist(LINK))

    def test_bold_line_without_link_stops(self):
        with self.assertRaises(ValueError):
            convert_gist(gist(f"- {LINK} — Text.\n\n- **No link** — Text."))


ENTRY = """<section class="entry" id="entry-{d}" data-date="{d}">
<span class="entry-date">{r}</span><h2 class="entry-subtitle">A &mdash; summary&rsquo;s.</h2>
<div class="entry-body"><div class="category" data-cat="software"><h3 class="cat-label">Software</h3>
<ul class="items"><li><a class="headline" href="https://example.com/?a=1&amp;b=2">A &amp; B</a> &mdash; Uses <code>/ship</code> now.</li></ul>
<p class="no-item">Quiet otherwise.</p></div></div></section>"""
PAGE = ("<footer>outside</footer>"
        + ENTRY.format(d="2026-11-25", r="NOV 23 &ndash; 25, 2026")
        + ENTRY.format(d="2026-11-27", r="NOV 25 &ndash; 27, 2026") + "<p>after</p>")


class Log(unittest.TestCase):
    def test_two_entries(self):
        result = convert_log(PAGE)
        self.assertEqual(sorted(result), [dt.date(2026, 11, 25), dt.date(2026, 11, 27)])
        issue = parse_issue(result[dt.date(2026, 11, 27)], dt.date(2026, 11, 27))
        self.assertEqual(issue.summary, "A — summary’s.")
        self.assertEqual(issue.sections[0].name, "Software / Dev Tools")
        item = issue.sections[0].items[0]
        self.assertEqual((item.title, item.url), ("A & B", "https://example.com/?a=1&b=2"))
        self.assertEqual(item.text, "Uses `/ship` now.")
        self.assertEqual(issue.sections[0].notes, ["Quiet otherwise."])

    def test_only_selected_dates_are_converted(self):
        broken = PAGE + ENTRY.format(d="2026-11-15", r="NOV 10 &ndash; 14, 2026")
        self.assertEqual(list(convert_log(broken, only={dt.date(2026, 11, 27)})), [dt.date(2026, 11, 27)])


if __name__ == "__main__":
    unittest.main()
