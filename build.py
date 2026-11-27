"""Build one page per month from the Markdown files in issues/."""
import datetime as dt
import re
import shutil
import sys
from html import escape
from itertools import groupby
from pathlib import Path

from pulse import IssueError, parse_issue

TITLE = "Tech Pulse"
AUTHOR = "Meqdad Darwish"
TAGLINE = "AI, robotics, software, startups and hardware, in plain language, every two days."
NOTE = "Each item links to its source. Check it before relying on figures."
SOCIAL = (
    ("LinkedIn: Meqdad Darwish", "https://www.linkedin.com/in/meqdad-darwish/"),
    ("X: @MeqdadDev", "https://twitter.com/MeqdadDev"),
    ("GitHub: MeqdadDev", "https://github.com/MeqdadDev"),
    ("Instagram: @meqdad.dev", "https://www.instagram.com/meqdad.dev/"),
)
FONTS = ("https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700"
         "&family=IBM+Plex+Serif:ital,wght@0,400;0,500;0,600;1,400"
         "&family=IBM+Plex+Mono:wght@400;500;600&display=swap")
EXTERNAL = 'target="_blank" rel="noopener"'


def inline(text):
    """Escape text, then allow `code`, **bold** and http(s) links."""
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", escape(text))
    html = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", html)
    return re.sub(r"\[([^\]]+)\]\((https?://[^\s()]+(?:\([^\s()]*\)[^\s()]*)*)\)",
                  rf'<a href="\2" {EXTERNAL}>\1</a>', html)


def load_issues(issues_dir):
    issues = []
    for path in sorted(Path(issues_dir).glob("*.md")):
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}\.md", path.name):
                raise IssueError("the file name must be YYYY-MM-DD.md")
            date = dt.date.fromisoformat(path.stem)
            issues.append(parse_issue(path.read_text(encoding="utf-8"), date))
        except ValueError as error:
            raise IssueError(f"{path.name}: {error}") from error
    if not issues:
        raise IssueError(f"no issues found in {issues_dir}")
    return sorted(issues, key=lambda i: i.date, reverse=True)


def render_issue(issue):
    parts = [
        f'<section class="entry" id="entry-{issue.date}" data-date="{issue.date}">',
        f'<span class="entry-date">{escape(issue.date_range.upper())}</span>',
        f'<h2 class="entry-subtitle">{inline(issue.summary)}</h2>',
    ]
    for section in issue.sections:
        parts.append(f'<div class="category"><h3 class="cat-label">{escape(section.name)}</h3>')
        if section.items:
            parts.append('<ul class="items">')
            parts += [
                f'<li><a class="headline" href="{escape(item.url)}" {EXTERNAL}>{inline(item.title)}</a>'
                f" &mdash; {inline(item.text)}</li>"
                for item in section.items
            ]
            parts.append("</ul>")
        parts += [f'<p class="no-item">{inline(note.strip("*"))}</p>' for note in section.notes]
        parts.append("</div>")
    parts.append("</section>")
    return "\n".join(parts)


def month_link(target, current, root, home):
    if home or target.year != current.year:
        href = root + target.strftime("%Y/%m.html")
    else:
        href = target.strftime("%m.html")
    mark = ' aria-current="page"' if target == current else ""
    return f'<a href="{href}"{mark}>{target:%b %Y}</a>'


def render_page(month, issues, months, root, home):
    """root is the relative path from this page back to the site's top folder."""
    label = f"{month:%B %Y}"
    month_links = "\n".join(month_link(m, month, root, home) for m in months)
    chips = "\n".join(
        f'<a href="#entry-{i.date}">{i.date.strftime("%b %d").upper()}</a>' for i in issues)
    count = f"{len(issues)} issue" + ("" if len(issues) == 1 else "s")
    latest = f"{issues[0].date:%b} {issues[0].date.day}, {issues[0].date.year}"
    social = "\n".join(f'<a href="{url}" {EXTERNAL}>{name}</a>' for name, url in SOCIAL)
    entries = "\n".join(render_issue(i) for i in issues)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{TITLE} · {label} · {AUTHOR}</title>
<meta name="description" content="{TAGLINE}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{escape(FONTS)}">
<link rel="stylesheet" href="{root}style.css">
</head>
<body>
<header class="masthead">
<div class="wrap">
<p class="eyebrow">{AUTHOR}</p>
<h1 class="title">{TITLE}</h1>
<p class="dek">{TAGLINE}</p>
<div class="meta-row"><span><strong>{label}</strong></span><span>Latest: <strong>{latest}</strong></span><span>{count}</span></div>
<nav class="months" aria-label="Months">
{month_links}
</nav>
</div>
</header>
<nav class="index" aria-label="Jump to issue">
<div class="index-inner">
{chips}
</div>
</nav>
<div class="wrap">
<main>
{entries}
</main>
<footer class="colophon">
<div class="social">
{social}
</div>
{NOTE}
</footer>
</div>
</body>
</html>
"""


def build(issues_dir, out_dir, style):
    issues = load_issues(issues_dir)
    grouped = {month: list(group) for month, group in
               groupby(issues, key=lambda i: i.date.replace(day=1))}
    months = list(grouped)  # newest first
    pages = {}
    for month, group in grouped.items():
        pages[month.strftime("%Y/%m.html")] = render_page(month, group, months, "../", False)
    pages["index.html"] = render_page(months[0], grouped[months[0]], months, "", True)

    out_dir = Path(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    written = []
    for name, html in pages.items():
        target = out_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8", newline="\n")
        written.append(target)
    shutil.copyfile(style, out_dir / "style.css")
    return written


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    try:
        pages = build(root / "issues", root / "_site", root / "site" / "style.css")
    except IssueError as error:
        sys.exit(f"Build failed: {error}")
    print(f"Built {len(pages)} pages in _site/")
