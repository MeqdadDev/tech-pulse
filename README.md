# Tech Pulse

AI, robotics, software, startups and hardware, in plain language, every two days.
Researched and written with AI help. Published by Meqdad Darwish.

Each issue is one file, `issues/YYYY-MM-DD.md`. Pushing it to `main` rebuilds and
publishes the site: one page per month, newest issue first. If a test or the build
fails, the live site stays as it was.

## Issue format

```markdown
# TECH PULSE — NOV 25 – 27, 2026

> One sentence combining the top two stories.

## AI

- **[Headline](https://example.com/a)** — What happened and why it matters.

A plain paragraph is a note, for a quiet category.

---
```

Sections, in this order, each optional: `AI`, `Robotics`, `Software / Dev Tools`,
`Startups`, `Hardware`. An issue needs at least one item, and each item stays on one
line. The file name is the run date and must match the last day in the heading.

## Build locally

```
python -m unittest
python build.py
```

The pages are written to `_site/`.
