"""One-time import of earlier issues from a monthly gist."""
import re

from pulse import SECTIONS, end_of_range, parse_issue

ISSUE_HEADING = re.compile(r"^#{1,3} (?:tech pulse — )?(.+, \d{4})$", re.IGNORECASE)
SECTION_HEADING = re.compile(r"^#{2,3} \W*(.+)$")
ITEM = re.compile(r"^(?:- )?(\*\*\[.+?\]\(\S+\)\*\*)(.*)$")
NAMES = {name.lower(): name for name in SECTIONS}
NAMES.update({"software": SECTIONS[2], "software & dev tools": SECTIONS[2]})


def _item_text(rest):
    dated = re.match(r"^\s*(\([^)]*\))\s*—\s*(.*)$", rest)
    if dated:
        return f"{dated.group(1)} {dated.group(2)}"
    if rest.startswith(" — "):
        return rest[3:].strip()
    text = rest.lstrip(" ,—–:").strip()
    return text[:1].upper() + text[1:]


def _convert_issue(date_range, lines):
    out = [f"# TECH PULSE — {date_range.upper()}"]
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if line == "---":
            continue
        if line.startswith(">"):
            out.append(line)
            continue
        heading = SECTION_HEADING.match(line)
        if heading:
            name = heading.group(1).strip()
            if name.lower() not in NAMES:
                raise ValueError(f"{date_range}: unknown section '{name}'")
            out.append(f"## {NAMES[name.lower()]}")
            continue
        item = ITEM.match(line)
        if item:
            link, rest = item.groups()
            if not rest.strip():
                following = lines[index] if index < len(lines) else ""
                if not following or following.startswith(("#", "- ", "**", "---", ">")):
                    raise ValueError(f"{date_range}: headline without text: {link[:80]}")
                rest = f" — {following}"
                index += 1
            out.append(f"- {link} — {_item_text(rest)}")
            continue
        note = line[2:] if line.startswith("- ") else line
        if note.startswith(("**", "#")):
            raise ValueError(f"{date_range}: unrecognised line: {line[:80]}")
        out.append(re.sub(r"^\*(.+)\*$", r"\1", note))
    return "\n\n".join(out) + "\n\n---\n"


def convert_gist(markdown, skip=()):
    """Return {issue date: canonical Markdown}. skip holds 0-based issue positions to drop."""
    found = []
    for raw in markdown.splitlines():
        line = raw.strip()
        heading = ISSUE_HEADING.match(line)
        if heading:
            found.append((heading.group(1), []))
        elif line and found and not line.startswith("<!--"):
            found[-1][1].append(line)
    result = {}
    for position, (date_range, lines) in enumerate(found):
        if position in skip:
            continue
        date = end_of_range(date_range)
        if date is None:
            raise ValueError(f"cannot read the date in '{date_range}'")
        if date in result:
            raise ValueError(f"two issues end on {date.isoformat()}")
        text = _convert_issue(date_range, lines)
        try:
            parse_issue(text, date)
        except ValueError as error:
            raise ValueError(f"{date.isoformat()}: {error}") from error
        result[date] = text
    return result
