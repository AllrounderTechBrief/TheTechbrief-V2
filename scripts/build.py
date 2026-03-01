"""
Build script for The Tech Brief.
Fetches RSS feeds → generates category pages + homepage into docs/.

SOURCE OF TRUTH: site/ folder
  - Edit templates in site/template_*.html
  - Edit static pages (about, contact) in site/
  - Edit RSS sources in data/feeds.json
  - Edit category metadata in data/meta.json
  - NEVER edit docs/ directly — it is overwritten on every build

To add a new static page:
  1. Create site/<slug>.html
  2. Add '<slug>.html' to static_files in sync_static_assets()
  3. Commit and push

To add a new feed-driven category:
  1. Add feeds to data/feeds.json
  2. Add metadata to data/meta.json
  3. Add category name to CATEGORY_ORDER in build_home()
  4. Commit and push
"""
import os, json, re, time
import feedparser
from bs4 import BeautifulSoup
from slugify import slugify
from jinja2 import Template

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA = os.path.join(ROOT, 'data', 'feeds.json')
META = os.path.join(ROOT, 'data', 'meta.json')
SITE = os.path.join(ROOT, 'docs')

# ── Load templates & data ──────────────────────────────────────────────────
with open(os.path.join(ROOT, 'site', 'template_category.html'), 'r', encoding='utf-8') as f:
    CATEGORY_TPL = Template(f.read())
with open(os.path.join(ROOT, 'site', 'template_home.html'), 'r', encoding='utf-8') as f:
    HOME_TPL = Template(f.read())
with open(DATA, 'r', encoding='utf-8') as f:
    FEEDS = json.load(f)
with open(META, 'r', encoding='utf-8') as f:
    META_MAP = json.load(f)


# ── Text helpers ───────────────────────────────────────────────────────────

def clean_text(html):
    txt = BeautifulSoup(html or '', 'html.parser').get_text(' ')
    return re.sub(r"\s+", " ", txt).strip()


def summarize_text(text, sentences=2):
    text = (text or '').strip()
    if not text:
        return ''
    try:
        from sumy.parsers.plaintext import PlaintextParser
        from sumy.nlp.tokenizers import Tokenizer
        from sumy.summarizers.text_rank import TextRankSummarizer
        parser = PlaintextParser.from_string(text, Tokenizer('english'))
        summarizer = TextRankSummarizer()
        result = summarizer(parser.document, sentences)
        if result:
            return ' '.join(str(s) for s in result)
    except Exception:
        pass
    parts = re.split(r'(?<=[.!?])\s+', text)
    joined = ' '.join(parts[:sentences])
    return joined if joined else text[:280]


# ── Image extraction ───────────────────────────────────────────────────────

def _looks_like_image(url):
    if not url:
        return False
    from urllib.parse import urlparse
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in ('.jpg', '.jpeg', '.png', '.webp', '.gif'))


def _pick_img_tag(img):
    for attr in ('src', 'data-src', 'data-original'):
        if img and img.get(attr):
            return img.get(attr)
    if img and img.get('srcset'):
        return img.get('srcset').split()[0]
    return None


def first_image(entry):
    # 1. media:content
    for m in (entry.get('media_content') or []):
        if _looks_like_image(m.get('url')):
            return m['url']
    # 2. media:thumbnail
    for t in (entry.get('media_thumbnail') or []):
        if _looks_like_image(t.get('url')):
            return t['url']
    # 3. enclosures
    for e in (entry.get('enclosures') or []):
        url = e.get('href') or e.get('url')
        if _looks_like_image(url) or 'image' in (e.get('type') or ''):
            return url
    # 4. <content> HTML
    for c in (entry.get('content') or []):
        html = c.get('value') or c.get('content') or ''
        img = BeautifulSoup(html, 'html.parser').find('img')
        url = _pick_img_tag(img)
        if url:
            return url
    # 5. <description> / <summary> HTML
    desc = entry.get('summary') or entry.get('description') or ''
    if desc:
        img = BeautifulSoup(desc, 'html.parser').find('img')
        url = _pick_img_tag(img)
        if url:
            return url
    return None


# ── Copyright-safe image handling ─────────────────────────────────────────
# Sources that are definitively safe to use
SAFE_IMAGE_DOMAINS = (
    'images.unsplash.com',
    'images.pexels.com',
    'cdn.pixabay.com',
    'upload.wikimedia.org',
    'apple.com/newsroom/images',
    'samsung.com/press',
    'google.com/press',
)

# Curated copyright-free Unsplash fallbacks keyed by category slug
# All URLs are Unsplash public-domain images (CC0-equivalent licence)
CATEGORY_FALLBACK_IMAGES = {
    'ai-news':             'https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=800&auto=format&fit=crop',
    'enterprise-tech':     'https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?w=800&auto=format&fit=crop',
    'cybersecurity-updates':'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=800&auto=format&fit=crop',
    'mobile-gadgets':      'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=800&auto=format&fit=crop',
    'consumer-tech':       'https://images.unsplash.com/photo-1498049794561-7780e7231661?w=800&auto=format&fit=crop',
    'broadcast-tech':      'https://images.unsplash.com/photo-1478737270239-2f02b77fc618?w=800&auto=format&fit=crop',
    'gaming':              'https://images.unsplash.com/photo-1538481199705-c710c4e965fc?w=800&auto=format&fit=crop',
    'evs-automotive':      'https://images.unsplash.com/photo-1593941707882-a5bba14938c7?w=800&auto=format&fit=crop',
    'startups-business':   'https://images.unsplash.com/photo-1559136555-9303baea8ebd?w=800&auto=format&fit=crop',
    'default':             'https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&auto=format&fit=crop',
}


def is_safe_image(url):
    """Return True if the image URL comes from a copyright-safe source."""
    if not url:
        return False
    from urllib.parse import urlparse
    host = urlparse(url).netloc.lower().lstrip('www.')
    return any(host == d or host.endswith('.' + d) for d in SAFE_IMAGE_DOMAINS)


def copyright_safe_image(url, category_slug='default'):
    """Return url unchanged if safe; otherwise return a curated Unsplash fallback."""
    if is_safe_image(url):
        return url
    return CATEGORY_FALLBACK_IMAGES.get(category_slug,
                                        CATEGORY_FALLBACK_IMAGES['default'])


def parse_time(entry):
    t = entry.get('published_parsed') or entry.get('updated_parsed')
    return time.mktime(t) if t else 0


def fmt_date(ts):
    if not ts:
        return ''
    return time.strftime('%B %d, %Y', time.localtime(ts))


# ── Sync static assets from site/ → docs/ ─────────────────────────────────

def sync_static_assets():
    import shutil

    static_dirs = ['assets', 'legal', 'articles']

    # Static pages that are NOT feed-generated (hand-authored in site/)
    # Do NOT add feed-driven category pages here — build_category() handles them
    static_files = [
        'about.html',
        'contact.html',
        'how-to.html',
        'robots.txt',
        'sitemap.xml',
        'template_category.html',
        'template_home.html',
    ]

    src_root = os.path.join(ROOT, 'site')

    for d in static_dirs:
        src = os.path.join(src_root, d)
        dst = os.path.join(SITE, d)
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

    for fname in static_files:
        src = os.path.join(src_root, fname)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(SITE, fname))
        else:
            print(f'  WARNING: static file not found in site/: {fname}')


# ── Category builder ───────────────────────────────────────────────────────

def build_category(category, urls):
    items = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
        except Exception as ex:
            print(f'  Feed error {url}: {ex}')
            continue
        for e in feed.entries[:12]:
            title   = e.get('title', 'Untitled')
            link    = e.get('link', '')
            source  = feed.feed.get('title', 'Unknown')
            text    = clean_text(e.get('summary') or e.get('description') or '')
            summary = summarize_text(text, sentences=2)
            img     = first_image(e)
            ts      = parse_time(e)
            items.append({
                'title': title, 'link': link, 'source': source,
                'summary': summary, 'image': img, 'ts': ts,
                'date': fmt_date(ts), 'category': category, 'commentary': ''
            })
    items.sort(key=lambda x: x['ts'], reverse=True)

    meta = dict(META_MAP.get(category, {
        'title': category, 'description': category,
        'h1': category, 'h2': '', 'slug': slugify(category)
    }))
    if 'slug' not in meta:
        meta['slug'] = slugify(category)

    cat_slug = meta['slug']
    for item in items:
        item['image'] = copyright_safe_image(item.get('image'), cat_slug)

    html = CATEGORY_TPL.render(meta=meta, cards=items)
    out  = os.path.join(SITE, f"{meta['slug']}.html")
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  Built {meta["slug"]}.html  ({len(items)} items)')
    return items


# ── Home builder ───────────────────────────────────────────────────────────

def build_home(category_map):
    CATEGORY_ORDER = [
        'AI News',
        'Startups & Business',
        'Mobile & Gadgets',
        'Consumer Tech',
        'Cybersecurity Updates',
        'Enterprise Tech',
        'Broadcast Tech',
        'Gaming',
        'EVs & Automotive',
    ]

    all_cards = []
    seen = set()

    for cat in CATEGORY_ORDER:
        items = category_map.get(cat, [])
        for item in items[:3]:
            if item['link'] not in seen:
                all_cards.append(item)
                seen.add(item['link'])

    # Catch any extra categories not listed above
    for cat, items in category_map.items():
        if cat not in CATEGORY_ORDER:
            for item in items[:3]:
                if item['link'] not in seen:
                    all_cards.append(item)
                    seen.add(item['link'])

    all_cards.sort(key=lambda x: x['ts'], reverse=True)

    meta = dict(META_MAP['Home'])
    html = HOME_TPL.render(meta=meta, featured=[], cards=all_cards[:27])
    with open(os.path.join(SITE, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  Built index.html  (grid={len(all_cards[:27])})')


# ── Entry point ────────────────────────────────────────────────────────────

def main():
    os.makedirs(SITE, exist_ok=True)
    print('Syncing static assets from site/ to docs/…')
    sync_static_assets()

    print('Building Tech Brief…')
    category_map = {}
    for cat, urls in FEEDS.items():
        print(f'Fetching: {cat}')
        category_map[cat] = build_category(cat, urls)
    build_home(category_map)
    print('Build complete.')

if __name__ == '__main__':
    main()
