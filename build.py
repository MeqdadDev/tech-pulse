"""Build one page per month from the Markdown files in issues/."""
import datetime as dt
import re
import shutil
import sys
from html import escape
from itertools import groupby
from pathlib import Path

from pulse import SECTIONS, IssueError, parse_issue

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
PORTFOLIO = "https://meqdaddev.github.io/"
FONTS = "https://fonts.googleapis.com/css2?family=Rubik:ital,wght@0,400;0,500;0,700;0,800;1,400&display=swap"
EXTERNAL = 'target="_blank" rel="noopener"'
CATEGORY_CLASS = dict(zip(SECTIONS, ("ai", "robotics", "software", "startups", "hardware")))

# Runs in <head>, before the page is painted, so a saved choice never flashes the other theme.
THEME_BOOT = """<script>
try{var t=localStorage.getItem("theme");if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t)}catch(e){}
document.documentElement.classList.add("js")
</script>"""

# Without a saved choice the page follows the device. The button names the mode it switches to.
THEME_SWITCH = """<script>
(function(){
var root=document.documentElement,button=document.getElementById("theme-toggle"),
media=window.matchMedia("(prefers-color-scheme: dark)");
function dark(){var t=root.getAttribute("data-theme");return t?t==="dark":media.matches}
function label(){button.querySelector("span").textContent=dark()?"Light mode":"Dark mode"}
button.addEventListener("click",function(){
var next=dark()?"light":"dark";root.setAttribute("data-theme",next);
try{localStorage.setItem("theme",next)}catch(e){}
label()});
if(media.addEventListener)media.addEventListener("change",label);
label()})()
</script>"""


def inline(text):
    """Escape text, then allow `code`, **bold** and http(s) links."""
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", escape(text))
    html = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", html)
    return re.sub(r"\[([^\]]+)\]\((https?://[^\s()]+(?:\([^\s()]*\)[^\s()]*)*)\)",
                  rf'<a href="\2" {EXTERNAL}>\1</a>', html)


def load_issues(issues_dir):
    issues = []
    for path in sorted(Path(issues_dir).iterdir()):
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
        parts.append(f'<div class="category cat-{CATEGORY_CLASS[section.name]}">'
                     f'<h3 class="cat-label">{escape(section.name)}</h3>')
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


def plural(count, one, many):
    return f"{count} {one if count == 1 else many}"


def story_count(issue):
    return sum(len(section.items) for section in issue.sections)


def month_card(target, issues, current, root, home):
    """A month's tile. Its bars are the story count of each issue, oldest on the left."""
    if home or target.year != current.year:
        href = root + target.strftime("%Y/%m.html")
    else:
        href = target.strftime("%m.html")
    mark = ' aria-current="page"' if target == current else ""
    counts = [story_count(i) for i in reversed(issues)]
    tallest = max(counts)
    bars = "".join(f'<i style="height:{round(100 * c / tallest)}%"></i>' for c in counts)
    totals = f'{plural(len(issues), "issue", "issues")}, {plural(sum(counts), "story", "stories")}'
    return (f'<a class="month-card" href="{href}"{mark}>'
            f'<span class="month-name">{target:%B}</span>'
            f'<span class="month-year">{target.year}</span>'
            f'<span class="pulse" aria-hidden="true">{bars}</span>'
            f'<span class="month-totals">{totals}</span></a>')


def render_page(month, issues, months, root, home):
    """months maps each month to its issues, newest first.
    root is the relative path from this page back to the site's top folder."""
    label = f"{month:%B %Y}"
    cards = "\n".join(month_card(m, group, month, root, home) for m, group in months.items())
    chips = "\n".join(f'<a href="#entry-{i.date}">{i.date:%b} {i.date.day}</a>' for i in issues)
    latest = f"{issues[0].date:%B} {issues[0].date.day}"
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
{THEME_BOOT}
</head>
<body>
<div class="topbar">
<div class="wrap">
<a class="author" href="{PORTFOLIO}">{AUTHOR}</a>
<div class="actions">
<a class="button portfolio" href="{PORTFOLIO}">Who am I?</a>
<button class="button" type="button" id="theme-toggle"><b aria-hidden="true"></b><span>Dark mode</span></button>
</div>
</div>
</div>
<header class="masthead">
<div class="wrap">
<h1 class="title">{TITLE}</h1>
<p class="dek">{TAGLINE}</p>
<p class="latest">Newest issue on this page: <strong>{latest}</strong></p>
</div>
</header>
<nav class="months" aria-label="Months">
<div class="wrap">
<h2>Pick a month</h2>
<div class="month-grid">
{cards}
</div>
</div>
</nav>
<nav class="index" aria-label="Jump to issue">
<div class="wrap index-inner">
{chips}
</div>
</nav>
<div class="wrap">
<main>
<h2 class="month-title">{label}</h2>
{entries}
</main>
<footer class="colophon">
<p class="about">Researched and written with AI help. Published by {AUTHOR}. <a href="{PORTFOLIO}">See my portfolio</a></p>
<div class="social">
{social}
</div>
<p>{NOTE}</p>
</footer>
</div>
{THEME_SWITCH}
</body>
</html>
"""


def build(issues_dir, out_dir, style):
    issues = load_issues(issues_dir)
    grouped = {month: list(group) for month, group in
               groupby(issues, key=lambda i: i.date.replace(day=1))}
    newest = next(iter(grouped))  # months are newest first
    pages = {}
    for month, group in grouped.items():
        pages[month.strftime("%Y/%m.html")] = render_page(month, group, grouped, "../", False)
    pages["index.html"] = render_page(newest, grouped[newest], grouped, "", True)

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
