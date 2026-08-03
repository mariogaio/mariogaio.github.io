#!/usr/bin/env python3
"""Generatore statico per il sito personale a scroll.

Legge i file .md in contenuti/, genera:
- index.html (flusso completo, ordine cronologico inverso)
- post/<slug>/index.html per ogni contenuto (link permanente)

Uso: python script/build.py
"""
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENUTI_DIR = ROOT / "contenuti"
POST_DIR = ROOT / "post"

SITE_TITLE = "appunti"

MESI_IT = {
    1: "gennaio", 2: "febbraio", 3: "marzo", 4: "aprile",
    5: "maggio", 6: "giugno", 7: "luglio", 8: "agosto",
    9: "settembre", 10: "ottobre", 11: "novembre", 12: "dicembre",
}

FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", re.DOTALL)


def escape_html(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def md_to_html(md):
    md = md.strip()
    if not md:
        return ""
    paragraphs = re.split(r"\n\s*\n", md)
    html_parts = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        text = escape_html(para)
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
        text = text.replace("\n", "<br>\n")
        html_parts.append(f"<p>{text}</p>")
    return "\n".join(html_parts)


def parse_post(path):
    raw = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(raw)
    if not match:
        raise ValueError(f"Frontmatter mancante in {path.name}")
    fm_raw, body = match.groups()
    meta = {}
    for line in fm_raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()

    if "data" not in meta or "tipo" not in meta:
        raise ValueError(f"Campi 'data' o 'tipo' mancanti in {path.name}")

    data_obj = datetime.strptime(meta["data"], "%Y-%m-%d")
    data_leggibile = f"{data_obj.day} {MESI_IT[data_obj.month]} {data_obj.year}"

    return {
        "slug": path.stem,
        "data": meta["data"],
        "data_leggibile": data_leggibile,
        "tipo": meta["tipo"],
        "meta": meta,
        "body_html": md_to_html(body),
    }


def render_media(post):
    meta = post["meta"]
    tipo = post["tipo"]
    if tipo == "foto":
        immagine = meta.get("immagine", "")
        alt = escape_html(meta.get("alt", ""))
        return (
            f'<figure class="post-media">'
            f'<img src="/assets/img/{immagine}" alt="{alt}" loading="lazy">'
            f"</figure>"
        )
    if tipo == "video":
        video = meta.get("video", "")
        if video.startswith("http"):
            return (
                f'<figure class="post-media post-media--embed">'
                f'<iframe src="{video}" loading="lazy" allowfullscreen '
                f'referrerpolicy="no-referrer"></iframe>'
                f"</figure>"
            )
        return (
            f'<figure class="post-media">'
            f'<video controls preload="metadata" src="/assets/video/{video}"></video>'
            f"</figure>"
        )
    return ""


def render_article(post, permalink=True):
    media_html = render_media(post)
    date_link = (
        f'<a href="/post/{post["slug"]}/">{post["data_leggibile"]}</a>'
        if permalink
        else post["data_leggibile"]
    )
    return f"""<article class="post" id="{post['slug']}">
  <p class="post-date">{date_link}</p>
  {media_html}
  <div class="post-body">
    {post['body_html']}
  </div>
</article>"""


def page_shell(title, body_html, footer_html):
    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape_html(title)}</title>
<link rel="stylesheet" href="/style.css">
</head>
<body>
<header class="site-header"><a href="/">{SITE_TITLE}</a></header>
<main class="feed">
{body_html}
</main>
{footer_html}
</body>
</html>
"""


def render_archive(posts):
    groups = {}
    for post in posts:
        year, month, _ = post["data"].split("-")
        key = (year, month)
        groups.setdefault(key, []).append(post)
    ordered_keys = sorted(groups.keys(), reverse=True)
    items = []
    for year, month in ordered_keys:
        first_slug = groups[(year, month)][0]["slug"]
        label = f"{MESI_IT[int(month)]} {year}"
        items.append(f'<a href="#{first_slug}">{label}</a>')
    return f"""<footer class="site-footer">
  <nav class="archive">
    <span class="archive-label">archivio</span>
    {" &middot; ".join(items)}
  </nav>
</footer>"""


def build():
    md_files = sorted(CONTENUTI_DIR.glob("*.md"))
    if not md_files:
        print("Nessun contenuto trovato in contenuti/.")
        return

    posts = [parse_post(p) for p in md_files]
    posts.sort(key=lambda p: (p["data"], p["slug"]), reverse=True)

    back_link = '<p class="back-link"><a href="/">&larr; tutti i contenuti</a></p>'
    for post in posts:
        page = page_shell(
            f"{post['data_leggibile']} — {SITE_TITLE}",
            render_article(post, permalink=False),
            back_link,
        )
        out_dir = POST_DIR / post["slug"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(page, encoding="utf-8")

    feed_html = "\n".join(render_article(p, permalink=True) for p in posts)
    index_page = page_shell(SITE_TITLE, feed_html, render_archive(posts))
    (ROOT / "index.html").write_text(index_page, encoding="utf-8")

    print(f"Generati {len(posts)} contenuti -> index.html + post/<slug>/index.html")


if __name__ == "__main__":
    build()
