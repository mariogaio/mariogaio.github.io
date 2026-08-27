#!/usr/bin/env python3
"""Generatore statico per il sito personale a scroll.

Legge i file .md in contenuti/, genera:
- index.html (flusso completo, ordine cronologico inverso)
- post/<slug>/index.html per ogni contenuto (link permanente)

Uso: python script/build.py
"""
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENUTI_DIR = ROOT / "contenuti"
POST_DIR = ROOT / "post"

SITE_TITLE = "Appunti pubblici di Mario Gaio"
ABOUT_TEXT = "Gli appunti che lascio qui alimentano la parte destra del mio cervello."
ABOUT_EMAIL = "mariogaio.it@gmail.com"

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
        .replace('"', "&quot;")
    )


def format_inline(text):
    text = escape_html(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


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
        text = format_inline(para).replace("\n", "<br>\n")
        html_parts.append(f"<p>{text}</p>")
    return "\n".join(html_parts)


def order_timestamp(path):
    """Timestamp used to order same-day posts, oldest first.

    Prefers the commit time git first added the file — stable across
    fresh checkouts/clones (unlike filesystem mtime, which resets and
    caused same-day posts to reorder randomly between the local and
    cloud sessions working on this repo). Falls back to filesystem
    mtime for a file that hasn't been committed yet.
    """
    try:
        result = subprocess.run(
            ["git", "log", "--follow", "--format=%at", "--", str(path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        timestamps = [line for line in result.stdout.splitlines() if line.strip()]
        if timestamps:
            return int(timestamps[-1])  # earliest commit that touched this file
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        pass
    return path.stat().st_mtime


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
        "fonte_html": format_inline(meta["fonte"]) if meta.get("fonte") else None,
        "order_ts": order_timestamp(path),
    }


def render_media(post):
    meta = post["meta"]
    tipo = post["tipo"]
    if tipo == "foto":
        immagini = [i.strip() for i in meta.get("immagine", "").split(",") if i.strip()]
        alt_parts = [a.strip() for a in meta.get("alt", "").split("|")]
        imgs = []
        for i, immagine in enumerate(immagini):
            alt = escape_html(alt_parts[i] if i < len(alt_parts) else alt_parts[-1])
            imgs.append(f'<img src="/assets/img/{immagine}" alt="{alt}" loading="lazy">')
        return f'<figure class="post-media">{"".join(imgs)}</figure>'
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


def render_article(post):
    media_html = render_media(post)
    fonte_html = (
        f'<p class="fonte">{post["fonte_html"]}</p>' if post["fonte_html"] else ""
    )
    return f"""<article class="post" id="{post['slug']}">
  <p class="post-date">{post['data_leggibile']}</p>
  {media_html}
  <div class="post-body">
    {post['body_html']}
  </div>
  {fonte_html}
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
<header class="site-header">
  <a href="/" class="site-title">{SITE_TITLE}</a>
  <nav class="site-nav"><a href="/">Home</a><a href="/about/">About me</a></nav>
</header>
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


def build_about():
    body = f"""<div class="about-page">
  <p>{escape_html(ABOUT_TEXT)}</p>
  <p><a href="mailto:{ABOUT_EMAIL}">{ABOUT_EMAIL}</a></p>
</div>"""
    back_link = '<p class="back-link"><a href="/">&larr; tutti i contenuti</a></p>'
    page = page_shell(f"About me — {SITE_TITLE}", body, back_link)
    out_dir = ROOT / "about"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(page, encoding="utf-8")


def build():
    md_files = sorted(CONTENUTI_DIR.glob("*.md"))
    if not md_files:
        print("Nessun contenuto trovato in contenuti/.")
        return

    posts = [parse_post(p) for p in md_files]
    posts.sort(key=lambda p: (p["data"], p["order_ts"]), reverse=True)

    if POST_DIR.exists():
        shutil.rmtree(POST_DIR)
    POST_DIR.mkdir(parents=True, exist_ok=True)

    back_link = '<p class="back-link"><a href="/">&larr; tutti i contenuti</a></p>'
    for post in posts:
        page = page_shell(
            f"{post['data_leggibile']} — {SITE_TITLE}",
            render_article(post),
            back_link,
        )
        out_dir = POST_DIR / post["slug"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(page, encoding="utf-8")

    feed_html = "\n".join(render_article(p) for p in posts)
    index_page = page_shell(SITE_TITLE, feed_html, render_archive(posts))
    (ROOT / "index.html").write_text(index_page, encoding="utf-8")

    build_about()

    print(f"Generati {len(posts)} contenuti -> index.html + post/<slug>/index.html + about/")


if __name__ == "__main__":
    build()
