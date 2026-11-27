import datetime as dt
import unittest

from pulse import IssueError, parse_issue

SAMPLE = """# TECH PULSE — NOV 25 – 27, 2026

> One sentence combining the top two stories.

## AI

- **[Headline](https://example.com/a)** — What happened and why it matters.

A plain paragraph is a note, for a quiet category.

---
"""
DATE = dt.date(2026, 11, 27)
ITEM = "- **[Headline](https://example.com/a)** — What happened and why it matters."


class ParseIssue(unittest.TestCase):
    def reject(self, text, date=DATE):
        with self.assertRaises(IssueError) as ctx:
            parse_issue(text, date)
        self.assertRegex(str(ctx.exception), r"line \d+")

    def test_parses_sample(self):
        for text in (SAMPLE, SAMPLE.replace("\n", "\r\n")):
            issue = parse_issue(text, DATE)
            self.assertEqual(issue.date_range, "NOV 25 – 27, 2026")
            self.assertEqual(issue.summary, "One sentence combining the top two stories.")
            self.assertEqual([s.name for s in issue.sections], ["AI"])
            self.assertEqual(issue.sections[0].items[0].url, "https://example.com/a")
            self.assertEqual(len(issue.sections[0].items), 1)
            self.assertEqual(len(issue.sections[0].notes), 1)

    def test_rejects_two_line_item(self):
        self.reject(SAMPLE.replace(ITEM, "- **[Headline](https://example.com/a)**\nWhat happened."))

    def test_rejects_item_without_dash(self):
        self.reject(SAMPLE.replace(ITEM, ITEM[2:]))

    def test_rejects_javascript_url(self):
        self.reject(SAMPLE.replace("https://example.com/a", "javascript:alert(1)"))

    def test_rejects_date_mismatch(self):
        self.reject(SAMPLE, dt.date(2026, 11, 25))

    def test_rejects_missing_summary(self):
        self.reject(SAMPLE.replace("> One sentence combining the top two stories.\n", ""))

    def test_rejects_no_items(self):
        self.reject(SAMPLE.replace(ITEM, ""))

    def test_rejects_unknown_section(self):
        self.reject(SAMPLE.replace("## AI", "## Gossip"))

    def test_rejects_repeated_section(self):
        self.reject(SAMPLE.replace("---", "## AI\n\n" + ITEM + "\n\n---"))

    def test_rejects_sections_out_of_order(self):
        self.reject(SAMPLE.replace("## AI", "## Hardware").replace("---", "## AI\n\n" + ITEM + "\n"))

    def test_rejects_text_after_final_rule(self):
        self.reject(SAMPLE + "\nmore text\n")

    def test_url_with_parentheses(self):
        issue = parse_issue(SAMPLE.replace("/a)", "/a_(b))"), DATE)
        self.assertEqual(issue.sections[0].items[0].url, "https://example.com/a_(b)")


if __name__ == "__main__":
    unittest.main()
