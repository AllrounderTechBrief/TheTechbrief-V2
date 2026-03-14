"""
Build script for The Tech Brief.
Fetches RSS feeds → generates category pages + homepage into docs/

SOURCE OF TRUTH: site/ folder
  - Edit templates in site/template_*.html
  - Edit static pages (about, contact) in site/
  - Edit RSS sources in data/feeds.json
  - Edit category metadata in data/meta.json
  - NEVER edit docs/ directly — it is overwritten on every build

Original article injection:
  - Run scripts/generate_articles.py daily to populate data/generated_articles.json
  - build.py reads that file and injects editorial articles into homepage + category pages

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
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA = os.path.join(ROOT, 'data', 'feeds.json')
META = os.path.join(ROOT, 'data', 'meta.json')
SITE = os.path.join(ROOT, 'docs')
SITE_URL = 'https://www.thetechbrief.net'

# ── Load templates & data ──────────────────────────────────────────────────
with open(os.path.join(ROOT, 'site', 'template_category.html'), 'r', encoding='utf-8') as f:
    CATEGORY_TPL = Template(f.read())
with open(os.path.join(ROOT, 'site', 'template_home.html'), 'r', encoding='utf-8') as f:
    HOME_TPL = Template(f.read())
with open(DATA, 'r', encoding='utf-8') as f:
    FEEDS = json.load(f)
with open(META, 'r', encoding='utf-8') as f:
    META_MAP = json.load(f)


# ── Load generated editorial articles ─────────────────────────────────────
def load_editorial_articles():
    path = os.path.join(ROOT, 'data', 'generated_articles.json')
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


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
    for m in (entry.get('media_content') or []):
        if _looks_like_image(m.get('url')):
            return m['url']
    for t in (entry.get('media_thumbnail') or []):
        if _looks_like_image(t.get('url')):
            return t['url']
    for e in (entry.get('enclosures') or []):
        url = e.get('href') or e.get('url')
        if _looks_like_image(url) or 'image' in (e.get('type') or ''):
            return url
    for c in (entry.get('content') or []):
        html = c.get('value') or c.get('content') or ''
        img = BeautifulSoup(html, 'html.parser').find('img')
        url = _pick_img_tag(img)
        if url:
            return url
    desc = entry.get('summary') or entry.get('description') or ''
    if desc:
        img = BeautifulSoup(desc, 'html.parser').find('img')
        url = _pick_img_tag(img)
        if url:
            return url
    return None


# ── Copyright-safe image handling ─────────────────────────────────────────
SAFE_IMAGE_DOMAINS = (
    'images.unsplash.com',
    'images.pexels.com',
    'cdn.pixabay.com',
    'upload.wikimedia.org',
    'apple.com/newsroom/images',
    'samsung.com/press',
    'google.com/press',
)

CATEGORY_IMAGE_POOLS = {
    'ai-news': [
        'photo-1677442135703-1787eea5ce01', 'photo-1620712943543-bcc4688e7485',
        'photo-1655635643532-fa9ba2648cbe', 'photo-1533228100845-08145b01de14',
        'photo-1558494949-ef010cbdcc31',     'photo-1635070041078-e363dbe005cb',
        'photo-1501526029524-a8ea952b15be', 'photo-1531297484001-80022131f5a1',
        'photo-1504639725590-34d0984388bd', 'photo-1518770660439-4636190af475',
        'photo-1526374965328-7f61d4dc18c5', 'photo-1510511459019-5dda7724fd87',
    ],
    'enterprise-tech': [
        'photo-1486312338219-ce68d2c6f44d', 'photo-1497366216548-37526070297c',
        'photo-1568952433726-3896e3881c65', 'photo-1553877522-43269d4ea984',
        'photo-1542744094-3a31f272c490',     'photo-1521737711867-e3b97375f902',
        'photo-1600880292203-757bb62b4baf', 'photo-1454165804606-c3d57bc86b40',
        'photo-1507679799987-c73779587ccf', 'photo-1560472354-b33ff0c44a43',
        'photo-1530099486328-e021101a494a', 'photo-1661956602116-aa6865609028',
    ],
    'cybersecurity-updates': [
        'photo-1550751827-4bd374c3f58b',     'photo-1563986768609-322da13575f3',
        'photo-1614064641938-3bbee52942c7', 'photo-1510511233900-1982d92bd835',
        'photo-1555949963-aa79dcee981c',     'photo-1504384308090-c894fdcc538d',
        'photo-1516321318423-f06f85e504b3', 'photo-1544197150-b99a580bb7a8',
        'photo-1573164713988-8665fc963095', 'photo-1603808033192-082d6919d3e1',
        'photo-1569396116180-210c182bedb8', 'photo-1591696205602-2f950c417cb9',
    ],
    'mobile-gadgets': [
        'photo-1511707171634-5f897ff02aa9', 'photo-1592750475338-74b7b21085ab',
        'photo-1585060544812-6b45742d762f', 'photo-1523206489230-c012c64b2b48',
        'photo-1567581935884-3349723552ca', 'photo-1542751371-adc38448a05e',
        'photo-1525547719571-a2d4ac8945e2', 'photo-1616348436168-de43ad0db179',
        'photo-1565849904461-04a58ad377e0', 'photo-1601784551446-20c9e07cdbdb',
        'photo-1583394838336-acd977736f90', 'photo-1570891836654-d4590d13d073',
    ],
    'consumer-tech': [
        'photo-1498049794561-7780e7231661', 'photo-1517694712202-14dd9538aa97',
        'photo-1593642632559-0c6d3fc62b89', 'photo-1519389950473-47ba0277781c',
        'photo-1496181133206-80ce9b88a853', 'photo-1504707748692-419802cf939d',
        'photo-1550009158-9ebf69173e03',     'photo-1587829741301-dc798b83add3',
        'photo-1484788984921-03950022c9ef', 'photo-1547658719-da2b51169166',
        'photo-1560472355-536de3962603',     'photo-1468495244123-6c6c332eeece',
    ],
    'broadcast-tech': [
        'photo-1478737270239-2f02b77fc618', 'photo-1612420696760-0a0f34d3e7d0',
        'photo-1567095761054-7003afd47020', 'photo-1598488035139-bdbb2231ce04',
        'photo-1516321497487-e288fb19713f', 'photo-1574717024653-61fd2cf4d44d',
        'photo-1590602847861-f357a9332bbc', 'photo-1492619375914-88005aa9e8fb',
        'photo-1611532736597-de2d4265fba3', 'photo-1623039405147-547794f92e9e',
        'photo-1540575467063-178a50c2df87', 'photo-1478737270239-2f02b77fc618',
    ],
    'gaming': [
        'photo-1538481199705-c710c4e965fc', 'photo-1493711662062-fa541adb3fc8',
        'photo-1552820728-8b83bb6b773f',     'photo-1601887389937-0b02f7683064',
        'photo-1612287230202-1ff1d85d1bdf', 'photo-1511512578047-dfb367046420',
        'photo-1574375927938-d5a98e8ffe85', 'photo-1580327344181-c1163234e5a0',
        'photo-1606144042614-b2417e99c4e3', 'photo-1560419015-7c427e8ae5ba',
        'photo-1586182987320-4f376d39d787', 'photo-1569429593410-b498b3fb3387',
    ],
    'evs-automotive': [
        'photo-1593941707882-a5bba14938c7', 'photo-1558618666-fcd25c85cd64',
        'photo-1616455579100-2ceaa4eb2d37', 'photo-1549317661-bd32c8ce0db2',
        'photo-1502161254119-e1f02c5b5e4b', 'photo-1568605117036-5fe5e7bab0b7',
        'photo-1580274455191-1c62238fa1f4', 'photo-1617469767053-d3b523a0b982',
        'photo-1590362891991-f776e747a588', 'photo-1606016159991-dfe4f2746ad5',
        'photo-1571987502227-9231b837d92a', 'photo-1583121274602-3e2820c69888',
    ],
    'startups-business': [
        'photo-1559136555-9303baea8ebd',     'photo-1507003211169-0a1dd7228f2d',
        'photo-1600880292203-757bb62b4baf', 'photo-1450101499163-c8848c66ca85',
        'photo-1460925895917-afdab827c52f', 'photo-1553484771-371a605b060b',
        'photo-1579532537598-459ecdaf39cc', 'photo-1521737604893-d14cc237f11d',
        'photo-1537511446984-935f663eb1f4', 'photo-1486406146926-c627a92ad1ab',
        'photo-1573164713714-d95e436ab8d6', 'photo-1444653389962-8149286c578a',
    ],
    'default': [
        'photo-1518770660439-4636190af475', 'photo-1531297484001-80022131f5a1',
        'photo-1504639725590-34d0984388bd', 'photo-1519389950473-47ba0277781c',
        'photo-1498049794561-7780e7231661', 'photo-1550751827-4bd374c3f58b',
        'photo-1526374965328-7f61d4dc18c5', 'photo-1480944657103-7fed22359e1d',
        'photo-1488229297570-58520851e868', 'photo-1451187580459-43490279c0fa',
        'photo-1516321318423-f06f85e504b3', 'photo-1558494949-ef010cbdcc31',
    ],
}


def is_safe_image(url):
    if not url:
        return False
    from urllib.parse import urlparse
    host = urlparse(url).netloc.lower().lstrip('www.')
    return any(host == d or host.endswith('.' + d) for d in SAFE_IMAGE_DOMAINS)


def copyright_safe_image(url, category_slug='default', article_key=''):
    if is_safe_image(url):
        return url
    import hashlib
    pool = CATEGORY_IMAGE_POOLS.get(category_slug, CATEGORY_IMAGE_POOLS['default'])
    seed = (article_key or category_slug).encode('utf-8')
    idx  = int(hashlib.md5(seed).hexdigest(), 16) % len(pool)
    photo_id = pool[idx]
    return f'https://images.unsplash.com/{photo_id}?w=800&auto=format&fit=crop'


def assign_unique_images(items, category_slug):
    pool = CATEGORY_IMAGE_POOLS.get(category_slug, CATEGORY_IMAGE_POOLS['default'])
    pool_len = len(pool)
    pool_cursor = 0
    for item in items:
        original_url = item.get('image')
        if is_safe_image(original_url):
            item['image'] = original_url
        else:
            photo_id = pool[pool_cursor % pool_len]
            pool_cursor += 1
            item['image'] = f'https://images.unsplash.com/{photo_id}?w=800&auto=format&fit=crop'
    return items


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
            import shutil as sh
            sh.copy2(src, os.path.join(SITE, fname))
        else:
            print(f'  WARNING: static file not found in site/: {fname}')


# ── Category builder ───────────────────────────────────────────────────────

def build_category(category, urls, editorial_articles):
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
                'date': fmt_date(ts), 'category': category, 'commentary': '',
                'is_editorial': False
            })
    items.sort(key=lambda x: x['ts'], reverse=True)

    meta = dict(META_MAP.get(category, {
        'title': category, 'description': category,
        'h1': category, 'h2': '', 'slug': slugify(category)
    }))
    if 'slug' not in meta:
        meta['slug'] = slugify(category)

    cat_slug = meta['slug']
    items = assign_unique_images(items, cat_slug)

    # Get editorial articles for this category
    cat_editorial = [
        a for a in editorial_articles
        if a.get('cat_slug') == cat_slug
    ][:3]

    html = CATEGORY_TPL.render(meta=meta, cards=items, cat_editorial=cat_editorial)
    out  = os.path.join(SITE, f"{meta['slug']}.html")
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  Built {meta["slug"]}.html  ({len(items)} items, {len(cat_editorial)} editorial)')
    return items


# ── Home builder ───────────────────────────────────────────────────────────

def build_home(category_map, editorial_articles):
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

    for cat, items in category_map.items():
        if cat not in CATEGORY_ORDER:
            for item in items[:3]:
                if item['link'] not in seen:
                    all_cards.append(item)
                    seen.add(item['link'])

    all_cards.sort(key=lambda x: x['ts'], reverse=True)

    # Top 6 editorial articles for homepage highlights
    home_editorial = editorial_articles[:6]

    meta = dict(META_MAP['Home'])
    html = HOME_TPL.render(
        meta=meta,
        featured=[],
        cards=all_cards[:27],
        editorial_articles=home_editorial
    )
    with open(os.path.join(SITE, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  Built index.html  (grid={len(all_cards[:27])}, editorial={len(home_editorial)})')


# ── Sitemap builder ────────────────────────────────────────────────────────

def build_sitemap(editorial_articles):
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    # Static pages
    static_pages = [
        ('',                     'hourly',  '1.0'),
        ('ai-news.html',         'hourly',  '0.9'),
        ('broadcast-tech.html',  'hourly',  '0.9'),
        ('enterprise-tech.html', 'hourly',  '0.9'),
        ('cybersecurity-updates.html', 'hourly', '0.9'),
        ('mobile-gadgets.html',  'hourly',  '0.9'),
        ('consumer-tech.html',   'hourly',  '0.9'),
        ('gaming.html',          'hourly',  '0.9'),
        ('evs-automotive.html',  'hourly',  '0.9'),
        ('startups-business.html','hourly', '0.9'),
        ('how-to.html',          'monthly', '0.9'),
        ('about.html',           'monthly', '0.8'),
        ('contact.html',         'monthly', '0.7'),
        ('legal/privacy.html',   'yearly',  '0.5'),
        ('legal/terms.html',     'yearly',  '0.5'),
        ('legal/disclaimer.html','yearly',  '0.4'),
        ('legal/copyright.html', 'yearly',  '0.4'),
        ('legal/affiliate.html', 'yearly',  '0.4'),
    ]

    # Fixed articles
    fixed_articles = [
        ('articles/ai-agents-enterprise-2025.html',  '2025-02-01', 'monthly', '0.8'),
        ('articles/android-vs-iphone-2025.html',     '2025-02-15', 'monthly', '0.8'),
        ('articles/ransomware-playbook-2025.html',   '2025-02-10', 'monthly', '0.8'),
        ('articles/how-to-factory-reset-android.html','2025-03-01','monthly', '0.8'),
        ('articles/how-to-factory-reset-iphone.html','2025-03-01', 'monthly', '0.8'),
        ('articles/how-to-upgrade-windows.html',     '2025-03-01', 'monthly', '0.8'),
        ('articles/how-to-upgrade-macos.html',       '2025-03-01', 'monthly', '0.8'),
        ('articles/how-to-clear-cache.html',         '2025-03-01', 'monthly', '0.8'),
        ('articles/how-to-set-up-new-android.html',  '2025-03-01', 'monthly', '0.8'),
    ]

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
             '']

    # Static pages
    lines.append('  <!-- Core pages -->')
    for path, freq, pri in static_pages:
        url = f"{SITE_URL}/{path}" if path else SITE_URL + '/'
        lines += [
            '  <url>',
            f'    <loc>{url}</loc>',
            f'    <lastmod>{today}</lastmod>',
            f'    <changefreq>{freq}</changefreq>',
            f'    <priority>{pri}</priority>',
            '  </url>',
        ]

    # Fixed long-form articles
    lines.append('')
    lines.append('  <!-- Evergreen long-form articles -->')
    for path, lastmod, freq, pri in fixed_articles:
        lines += [
            '  <url>',
            f'    <loc>{SITE_URL}/{path}</loc>',
            f'    <lastmod>{lastmod}</lastmod>',
            f'    <changefreq>{freq}</changefreq>',
            f'    <priority>{pri}</priority>',
            '  </url>',
        ]

    # AI-generated articles
    if editorial_articles:
        lines.append('')
        lines.append('  <!-- AI-generated original articles -->')
        for a in editorial_articles:
            url  = f"{SITE_URL}/{a['url']}"
            date = a.get('date', today)
            lines += [
                '  <url>',
                f'    <loc>{url}</loc>',
                f'    <lastmod>{date}</lastmod>',
                '    <changefreq>monthly</changefreq>',
                '    <priority>0.75</priority>',
                '  </url>',
            ]

    lines += ['', '</urlset>', '']

    sitemap_out = os.path.join(SITE, 'sitemap.xml')
    with open(sitemap_out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    # Also update robots.txt with correct domain
    robots_src = os.path.join(ROOT, 'site', 'robots.txt')
    robots_out = os.path.join(SITE, 'robots.txt')
    robots_content = f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n"
    with open(robots_out, 'w', encoding='utf-8') as f:
        f.write(robots_content)
    # Keep site/ copy in sync too
    with open(robots_src, 'w', encoding='utf-8') as f:
        f.write(robots_content)

    total_urls = len(static_pages) + len(fixed_articles) + len(editorial_articles)
    print(f'  Built sitemap.xml  ({total_urls} URLs)  +  robots.txt')


# ── Entry point ────────────────────────────────────────────────────────────

def main():
    os.makedirs(SITE, exist_ok=True)

    # Load generated editorial articles
    editorial_articles = load_editorial_articles()
    print(f'Loaded {len(editorial_articles)} editorial articles from generated_articles.json')

    print('Syncing static assets from site/ to docs/…')
    sync_static_assets()

    print('Building Tech Brief…')
    category_map = {}
    for cat, urls in FEEDS.items():
        print(f'Fetching: {cat}')
        category_map[cat] = build_category(cat, urls, editorial_articles)

    build_home(category_map, editorial_articles)
    build_sitemap(editorial_articles)
    print('Build complete.')


if __name__ == '__main__':
    main()
