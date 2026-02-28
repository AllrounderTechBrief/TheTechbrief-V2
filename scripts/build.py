import os, json, re, time
import feedparser
from bs4 import BeautifulSoup
from slugify import slugify
from jinja2 import Template

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


# ── Text helpers ─────────────────────────────────────────────────────────────

def clean_text(html):
    txt = BeautifulSoup(html or '', 'html.parser').get_text(' ')
    return re.sub(r"\s+", " ", txt).strip()


def summarize_text(text, sentences=2):
    """Summarise with sumy/TextRank; fall back to truncation if unavailable."""
    text = (text or '').strip()
    if not text:
        return ''
    try:
        from sumy.parsers.plaintext import PlaintextParser
        from sumy.nlp.tokenizers import Tokenizer
        from sumy.summarizers.text_rank import TextRankSummarizer
        parser = PlaintextParser.from_string(text, Tokenizer('english'))
        summarizer = TextRankSummarizer()
        sents = summarizer(parser.document, sentences)
        if sents:
            return ' '.join([str(s) for s in sents])
    except Exception:
        pass
    # Fallback: first N sentences by period-split
    parts = re.split(r'(?<=[.!?])\s+', text)
    return ' '.join(parts[:sentences]) if len(parts) >= sentences else text[:280]


# ── Image extraction ──────────────────────────────────────────────────────────

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
    # 1) media:content
    for m in (entry.get('media_content') or []):
        if _looks_like_image(m.get('url')):
            return m['url']
    # 2) media:thumbnail
    for t in (entry.get('media_thumbnail') or []):
        if _looks_like_image(t.get('url')):
            return t['url']
    # 3) enclosures
    for e in (entry.get('enclosures') or []):
        url = e.get('href') or e.get('url')
        if _looks_like_image(url) or 'image' in (e.get('type') or ''):
            return url
    # 4) content:encoded blocks
    for c in (entry.get('content') or []):
        html = c.get('value') or c.get('content') or ''
        img = BeautifulSoup(html, 'html.parser').find('img')
        url = _pick_img_tag(img)
        if url:
            return url
    # 5) summary HTML
    desc = entry.get('summary') or entry.get('description') or ''
    if desc:
        img = BeautifulSoup(desc, 'html.parser').find('img')
        url = _pick_img_tag(img)
        if url:
            return url
    # 6) Broadcast source logo fallbacks
    src = ((entry.get('source') or {}).get('title') or '').lower()
    if 'tvbeurope' in src:
        return 'https://www.tvbeurope.com/wp-content/uploads/sites/11/2022/01/tvbeurope-logo.png'
    if 'newscaststudio' in src:
        return 'https://www.newscaststudio.com/wp-content/themes/newscaststudio/images/logo.png'
    if 'vizrt' in src:
        return 'https://www.vizrt.com/wp-content/uploads/2021/06/vizrt-logo.png'
    return None


def parse_time(entry):
    t = entry.get('published_parsed') or entry.get('updated_parsed')
    return time.mktime(t) if t else 0


def fmt_date(ts):
    """Return a human-readable date string from a Unix timestamp."""
    if not ts:
        return ''
    return time.strftime('%B %d, %Y', time.localtime(ts))


# ── Category builder ──────────────────────────────────────────────────────────

def build_category(category, urls):
    items = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
        except Exception as ex:
            print(f'  Feed error {url}: {ex}')
            continue
        for e in feed.entries[:10]:
            title = e.get('title', 'Untitled')
            link  = e.get('link', '')
            source = feed.feed.get('title', 'Unknown')
            text   = clean_text(e.get('summary') or e.get('description') or '')
            summary = summarize_text(text, sentences=2)
            img    = first_image(e)
            ts     = parse_time(e)
            items.append({
                'title':      title,
                'link':       link,
                'source':     source,
                'summary':    summary,
                'image':      img,
                'ts':         ts,
                'date':       fmt_date(ts),
                'category':   category,
                'commentary': ''
            })
    items.sort(key=lambda x: x['ts'], reverse=True)

    meta = dict(META_MAP.get(category, {
        'title': category, 'description': category,
        'h1': category, 'h2': '', 'slug': slugify(category)
    }))
    if 'slug' not in meta:
        meta['slug'] = slugify(category)

    html = CATEGORY_TPL.render(meta=meta, cards=items)
    out  = os.path.join(SITE, f"{meta['slug']}.html")
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  Built {meta["slug"]}.html  ({len(items)} items)')
    return items


# ── Home builder ──────────────────────────────────────────────────────────────

def build_home(category_map):
    """
    Home layout:
      featured  — top 1 item from each category (5 cards in highlight row)
      all_cards — top 4 items per category interleaved, deduped (main grid)
    """
    CATEGORY_ORDER = [
        'AI News', 'Mobile & Gadgets', 'Cybersecurity Updates',
        'Enterprise Tech', 'Broadcast Tech'
    ]

    featured   = []   # 1 per category — highlight strip
    all_cards  = []   # up to 4 per category — main grid

    for cat in CATEGORY_ORDER:
        items = category_map.get(cat, [])
        if items:
            featured.append(items[0])
            # Next 3 items go into main grid (skip the one already in featured)
            all_cards.extend(items[1:4])

    # Fill main grid with any leftover items (categories not in ORDER)
    seen_links = {c['link'] for c in featured} | {c['link'] for c in all_cards}
    for cat, items in category_map.items():
        if cat not in CATEGORY_ORDER:
            for item in items[:4]:
                if item['link'] not in seen_links:
                    all_cards.append(item)
                    seen_links.add(item['link'])

    # Sort main grid by timestamp
    all_cards.sort(key=lambda x: x['ts'], reverse=True)

    meta = dict(META_MAP['Home'])
    html = HOME_TPL.render(meta=meta, featured=featured, cards=all_cards[:20])
    with open(os.path.join(SITE, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  Built index.html  (featured={len(featured)}, grid={len(all_cards[:20])})')


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    print('Building Tech Brief…')
    category_map = {}
    for cat, urls in FEEDS.items():
        print(f'Fetching: {cat}')
        category_map[cat] = build_category(cat, urls)
    build_home(category_map)
    print('Build complete.')

if __name__ == '__main__':
    main()
