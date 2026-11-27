"""Parse and validate one Tech Pulse issue written in Markdown."""
import datetime as dt
import re
from dataclasses import dataclass, field

SECTIONS = ("AI", "Robotics", "Software / Dev Tools", "Startups", "Hardware")
MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")

HEADING = re.compile(r"^# TECH PULSE — (.+, (\d{4}))$", re.IGNORECASE)
ITEM = re.compile(r"^- \*\*\[(.+?)\]\((\S+)\)\*\* — (\S.*)$")


class IssueError(ValueError):
    pass


@dataclass
class Item:
    title: str
    url: str
    text: str


@dataclass
class Section:
    name: str
    items: list = field(default_factory=list)
    notes: list = field(default_factory=list)


@dataclass
class Issue:
    date: dt.date
    date_range: str
    summary: str
    sections: list


def _fail(number, message):
    raise IssueError(f"line {number}: {message}")


def end_of_range(date_range):
    """Return the last day named in a range such as 'NOV 25 – 27, 2026'."""
    days_part, _, year = date_range.rpartition(",")
    months = [w for w in re.findall(r"[A-Za-z]+", days_part) if w[:3].upper() in MONTHS]
    days = re.findall(r"\d+", days_part)
    if not months or not days:
        return None
    try:
        return dt.date(int(year), MONTHS.index(months[-1][:3].upper()) + 1, int(days[-1]))
    except ValueError:
        return None


def parse_issue(markdown, date):
    lines = [(n, l.strip()) for n, l in enumerate(markdown.lstrip("\ufeff").splitlines(), 1)]
    lines = [(n, l) for n, l in lines if l]
    if not lines:
        _fail(1, "the issue is empty")

    number, line = lines[0]
    heading = HEADING.match(line)
    if not heading:
        _fail(number, "expected '# TECH PULSE — <date range>, <year>'")
    date_range = heading.group(1)
    if end_of_range(date_range) != date:
        _fail(number, f"the heading does not end on the issue date {date.isoformat()}")

    if len(lines) < 2 or not lines[1][1].startswith("> "):
        _fail(lines[1][0] if len(lines) > 1 else number, "expected the '> ' summary line")
    summary = lines[1][1][2:].strip()

    body = lines[2:]
    if body and body[-1][1] == "---":
        body = body[:-1]

    sections = []
    last_position = -1
    for number, line in body:
        if line.startswith("## "):
            name = line[3:].strip()
            if name not in SECTIONS:
                _fail(number, f"unknown section '{name}'")
            position = SECTIONS.index(name)
            if position <= last_position:
                _fail(number, f"section '{name}' is repeated or out of order")
            last_position = position
            sections.append(Section(name))
            continue
        if not sections:
            _fail(number, "text before the first section")
        item = ITEM.match(line)
        if item:
            title, url, text = item.groups()
            if not re.match(r"https?://", url, re.IGNORECASE):
                _fail(number, "links must start with http:// or https://")
            sections[-1].items.append(Item(title, url, text))
        elif line.startswith(("- ", "**[", "#", ">", "---")):
            _fail(number, "not a valid item: use '- **[Headline](https://...)** — text' on one line")
        else:
            sections[-1].notes.append(line)

    if not any(s.items for s in sections):
        _fail(lines[-1][0], "the issue has no items")
    return Issue(date, date_range, summary, sections)
