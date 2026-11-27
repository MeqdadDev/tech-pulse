"""One-time import of issues from a Tech Pulse Log HTML page."""
import datetime as dt
from html.parser import HTMLParser

from pulse import SECTIONS, parse_issue

NAMES = {name.lower(): name for name in SECTIONS}
NAMES["software"] = SECTIONS[2]
FIELDS = {"entry-date": "range", "entry-subtitle": "summary", "cat-label": "section", "no-item": "note"}


class _Log(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.entries = []
        self.entry = None
        self.field = None
        self.tag = None
        self.buffer = []
        self.url = ""
        self.title = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = (attrs.get("class") or "").split()
        if tag == "section" and "entry" in classes:
            self.entry = {"date": attrs["data-date"], "range": "", "summary": "", "body": []}
        if self.entry is None:
            return
        if tag == "li":
            self.field, self.tag, self.buffer = "item", tag, []
        elif tag == "a" and "headline" in classes:
            self.url, self.buffer = attrs["href"], []
        elif tag == "code":
            self.buffer.append("`")
        else:
            for name in classes:
                if name in FIELDS:
                    self.field, self.tag, self.buffer = FIELDS[name], tag, []

    def handle_data(self, data):
        if self.field:
            self.buffer.append(data)

    def _text(self):
        return " ".join("".join(self.buffer).split())

    def handle_endtag(self, tag):
        if self.entry is None:
            return
        if tag == "code":
            self.buffer.append("`")
        elif tag == "a" and self.field == "item":
            self.title, self.buffer = self._text(), []
        elif tag == "section":
            self.entries.append(self.entry)
            self.entry = None
        elif self.field and tag == self.tag:
            text = self._text()
            if self.field in ("range", "summary"):
                self.entry[self.field] = text
            elif self.field == "section":
                self.entry["body"].append(f"## {NAMES.get(text.lower(), text)}")
            elif self.field == "note":
                self.entry["body"].append(text)
            else:
                self.entry["body"].append(f"- **[{self.title}]({self.url})** — {text.lstrip('— ')}")
            self.field = None


def convert_log(html, only=None):
    """Return {issue date: canonical Markdown} for all entries, or only the given dates."""
    parser = _Log()
    parser.feed(html)
    result = {}
    for entry in parser.entries:
        date = dt.date.fromisoformat(entry["date"])
        if only is not None and date not in only:
            continue
        blocks = [f"# TECH PULSE — {entry['range']}", f"> {entry['summary']}", *entry["body"]]
        text = "\n\n".join(blocks) + "\n\n---\n"
        parse_issue(text, date)
        result[date] = text
    return result
