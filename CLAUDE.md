# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A static, framework-free personal site: a single reverse-chronological scroll of daily content (text, photo, or video), each entry also reachable at its own permalink. No CMS, no database, no build tooling beyond one Python script. Hosted on GitHub Pages at `mariogaio.github.io` (a user-page repo, so all asset/link paths in generated HTML are root-relative, e.g. `/style.css`, `/assets/img/...`).

## Commands

Regenerate the site after adding/editing/removing anything in `contenuti/`:

```bash
python script/build.py
```

This is the only build step. It reads every `contenuti/*.md`, rewrites `index.html`, and fully regenerates `post/` (the whole directory is deleted and rebuilt each run, so removed posts don't leave orphaned permalink pages).

Local preview: any static file server pointed at the repo root, e.g. `python -m http.server 8422`.

There is no test suite, linter, or package manager — the generator has zero dependencies (Python stdlib only).

## Publishing a new post

1. Create `contenuti/YYYY-MM-DD-slug.md` (the filename stem becomes the permalink slug: `/post/<slug>/`). Frontmatter fields:
   - `data`: `YYYY-MM-DD` (drives both sort order and the displayed Italian date)
   - `tipo`: `testo` | `foto` | `video`
   - `immagine` (tipo `foto`): filename under `assets/img/`
   - `alt` (tipo `foto`): alt text
   - `video` (tipo `video`): either an `http...` embed URL (rendered as a 16:9 iframe) or a filename under `assets/video/` (rendered as `<video>`)
   - `fonte` (optional): bibliographic/source attribution, rendered as its own small muted paragraph after the body — don't put this in the body text itself. End it with a period, for consistency across posts.
2. Body is the markdown content (caption for foto/video, full text for testo). It's fine to leave the body empty for a `foto`/`video` post whose only text is the `fonte`.
3. Save any media into `assets/img/` or `assets/video/`.
4. Run `python script/build.py`.
5. Commit and push — GitHub Pages deploys automatically from `master`.

This repo is worked on from more than one Claude Code session (a local desktop session and a cloud session, sometimes both in the same day) — always `git pull`/`git fetch` before pushing, since a push can be rejected by commits made from the other session. If both sides touched generated HTML, resolve by re-running `python script/build.py` after merging the source files (`contenuti/`, `assets/`, `script/build.py`, `style.css`) rather than hand-resolving generated-file conflicts.

## Architecture

Everything generation-related lives in `script/build.py` as a single linear pipeline — there's no templating engine or multi-file module structure to navigate:

- `parse_post()` — splits frontmatter from body via one regex, does no YAML parsing (just `key: value` per line)
- `format_inline()` — the inline-markdown regex chain (`**bold**`, `*italic*`, `[text](url)`), shared by `md_to_html()` (post body) and the `fonte` field (single line, no paragraph splitting)
- `md_to_html()` — a deliberately minimal hand-rolled markdown converter built on `format_inline()`: paragraphs on blank lines, single `\n` → `<br>`. Nothing else is supported (no lists, headings, blockquotes, code) — extend `format_inline()` if a post needs more inline formatting.
- `render_media()` — the only place that branches on `tipo`; produces the `<figure>` markup for foto/video posts
- `render_article()` — shared between the home feed and permalink pages; the date is always plain text (accent-colored via CSS, not a link) — permalinks exist as URLs (`/post/<slug>/`, shared when confirming a publish) but aren't exposed as an in-page link, since Mario normally publishes one post a day and doesn't need in-feed navigation to a single post
- `page_shell()` — the single HTML document template (used for `index.html`, every `post/<slug>/index.html`, and `about/index.html`); also renders the `site-nav` (Home / About me) that appears on every page
- `build_about()` — writes the static `about/index.html` page from the `ABOUT_TEXT`/`ABOUT_EMAIL` constants; not sourced from `contenuti/`, since it's a fixed page, not a dated post
- `build()` — orchestrates: parse all posts, sort by `(data, mtime)` desc (file modification time breaks ties between same-day posts, so multiple posts published on one day keep their real publishing order), wipe+regenerate `post/`, write `index.html`, call `build_about()`

`style.css` is hand-maintained, not generated. It defines the whole visual language: system monospace font stack (no external font loading), light theme (`--bg`/`--text`/`--accent` custom properties), max-width `640px` centered column, minimal rule-line separators between posts (no cards/shadows). `SITE_TITLE`, `ABOUT_TEXT`, and `ABOUT_EMAIL` in `build.py` are the only other places site-wide text lives.

`.nojekyll` at the root disables GitHub Pages' Jekyll processing — required since this is plain generated HTML, not a Jekyll site.
