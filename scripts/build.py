import os, json, re, time
import feedparser
from bs4 import BeautifulSoup
from slugify import slugify
from jinja2 import Template
from summarize import summarize_text

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA = os.path.join(ROOT, 'data', 'feeds.json')
META = os.path.join(ROOT, 'data', 'meta.json')
SITE = os.path.join(ROOT, 'site')

# Load templates
with open(os.path.join(SITE, 'template_category.html'), 'r', encoding='utf-8') as f:
    CATEGORY_TPL = Template(f.read())
with open(os.path.join(SITE, 'template_home.html'), 'r', encoding='utf-8') as f:
    HOME_TPL = Template(f.read())
with open(DATA, 'r', encoding='utf-8') as f:
    FEEDS = json.load(f)
with open(META, 'r', encoding='utf-8') as f:
    META_MAP = json.load(f)


def clean_text(html):
    txt = BeautifulSoup(html or '', 'html.parser').get_text(' ')
    return re.sub(r"\s+", " ", txt).strip()


def _pick_from_img_tag(img):
    """Try common attributes used for lazy-loading and responsive images."""
    for attr in ("src", "data-src", "data-original"):
        if img and img.get(attr):
            return img.get(attr)
    if img and img.get("srcset"):
        return img.get("srcset").split()[0]
    return None


def _looks_like_image(url):
    """Quick heuristic to filter obvious non-image URLs."""
    if not url:
        return False
    from urllib.parse import urlparse
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"))


def first_image(entry):
    """
    Robust RSS image extractor:
    - media:content / media:thumbnail
    - enclosures (with or without image/* type)
    - content:encoded (WordPress-style)
    - summary/description HTML (with lazy-load attrs and srcset)
    - known logo fallbacks for broadcast sources
    """
    # 1) media:content (list of dicts with 'url')
    media_content = entry.get("media_content")
    if media_content and isinstance(media_content, list):
        for m in media_content:
            url = m.get("url")
            if _looks_like_image(url):
                return url

    # 2) media:thumbnail
    media_thumb = entry.get("media_thumbnail")
    if media_thumb and isinstance(media_thumb, list):
        for t in media_thumb:
            url = t.get("url")
            if _looks_like_image(url):
                return url

    # 3) enclosures
    enclosures = entry.get("enclosures")
    if enclosures and isinstance(enclosures, list):
        for e in enclosures:
            url = e.get("href") or e.get("url")
            if _looks_like_image(url):
                return url
            if "image" in (e.get("type") or "") and url:
                return url

    # 4) content:encoded (Atom/WordPress-style content blocks)
    content_blocks = entry.get("content")
    if content_blocks and isinstance(content_blocks, list):
        for c in content_blocks:
            html = c.get("value") or c.get("content") or ""
            soup = BeautifulSoup(html, "html.parser")
            img = soup.find("img")
            url = _pick_from_img_tag(img)
            if url:
                return url

    # 5) summary/description (HTML)
    desc_html = entry.get("summary") or entry.get("description") or ""
    if desc_html:
        soup = BeautifulSoup(desc_html, "html.parser")
        img = soup.find("img")
        url = _pick_from_img_tag(img)
        if url:
            return url

    # 6) Special-case fallbacks for Broadcast Tech sources
    source_title = (entry.get("source", {}) or {}).get("title", "") or ""
    st_lower = source_title.lower()
    if "tvbeurope" in st_lower:
        return "https://www.tvbeurope.com/wp-content/uploads/sites/11/2022/01/tvbeurope-logo.png"
    if "newscaststudio" in st_lower:
        return "https://www.newscaststudio.com/wp-content/themes/newscaststudio/images/logo.png"
    if "vizrt" in st_lower:
        return "https://www.vizrt.com/wp-content/uploads/2021/06/vizrt-logo.png"

    return None


def parse_time(entry):
    t = entry.get('published_parsed') or entry.get('updated_parsed')
    if t:
        return time.mktime(t)
    return 0


def build_category(category, urls):
    items = []
    for url in urls:
        feed = feedparser.parse(url)
        for e in feed.entries[:10]:
            title = e.get('title', 'Untitled')
            link = e.get('link')
            source = feed.feed.get('title', 'Unknown')
            text = clean_text(e.get('summary') or e.get('description') or '')
            summary = summarize_text(text, sentences=2)
            img = first_image(e)
            items.append({
                'title': title,
                'link': link,
                'source': source,
                'summary': summary,
                'image': img,
                'ts': parse_time(e),
                'category': category,
                'commentary': ''   # Reserved for future editorial commentary injection
            })
    items.sort(key=lambda x: x['ts'], reverse=True)

    # Build meta — merge data file meta with fallback
    meta = dict(META_MAP.get(category, {
        'title': category,
        'description': category,
        'h1': category,
        'h2': '',
        'slug': slugify(category)
    }))
    # Ensure slug is always present
    if 'slug' not in meta:
        meta['slug'] = slugify(category)

    html = CATEGORY_TPL.render(meta=meta, cards=items)
    out = os.path.join(SITE, f"{meta['slug']}.html")
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    return items[:24]


def build_home(all_items):
    meta = dict(META_MAP['Home'])
    html = HOME_TPL.render(meta=meta, cards=all_items[:24])
    with open(os.path.join(SITE, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)


def main():
    all_items = []
    for cat, urls in FEEDS.items():
        top_items = build_category(cat, urls)
        all_items.extend(top_items)
    all_items.sort(key=lambda x: x['ts'], reverse=True)
    build_home(all_items)
    print(f"Build complete. {len(all_items)} items across {len(FEEDS)} categories.")

if __name__ == '__main__':
    main()
