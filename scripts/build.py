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

# ── Per-category image POOLS ───────────────────────────────────────────────
# Each pool contains 12 unique, visually distinct Unsplash photo IDs.
# When an article has an unsafe image, we hash its URL to pick a pool entry —
# giving every card a DIFFERENT image while staying copyright-clean.
# All photos are free-to-use under the Unsplash Licence (unsplash.com/license).
CATEGORY_IMAGE_POOLS = {
    'ai-news': [
        'photo-1677442135703-1787eea5ce01',  # AI abstract purple
        'photo-1620712943543-bcc4688e7485',  # humanoid robot
        'photo-1655635643532-fa9ba2648cbe',  # AI chips blue
        'photo-1533228100845-08145b01de14',  # neural network nodes
        'photo-1558494949-ef010cbdcc31',     # data streams
        'photo-1635070041078-e363dbe005cb',  # AI brain digital
        'photo-1501526029524-a8ea952b15be',  # server room lights
        'photo-1531297484001-80022131f5a1',  # laptop code dark
        'photo-1504639725590-34d0984388bd',  # code screen
        'photo-1518770660439-4636190af475',  # circuit board macro
        'photo-1526374965328-7f61d4dc18c5',  # matrix code
        'photo-1510511459019-5dda7724fd87',  # data center blue
    ],
    'enterprise-tech': [
        'photo-1486312338219-ce68d2c6f44d',  # person on laptop
        'photo-1497366216548-37526070297c',  # modern office
        'photo-1568952433726-3896e3881c65',  # team meeting
        'photo-1553877522-43269d4ea984',     # office abstract
        'photo-1542744094-3a31f272c490',     # business laptop
        'photo-1521737711867-e3b97375f902',  # team working
        'photo-1600880292203-757bb62b4baf',  # remote work setup
        'photo-1454165804606-c3d57bc86b40',  # business graphs
        'photo-1507679799987-c73779587ccf',  # business suit
        'photo-1560472354-b33ff0c44a43',     # server infrastructure
        'photo-1530099486328-e021101a494a',  # data analytics
        'photo-1661956602116-aa6865609028',  # modern workspace
    ],
    'cybersecurity-updates': [
        'photo-1550751827-4bd374c3f58b',     # security shield blue
        'photo-1563986768609-322da13575f3',  # padlock digital
        'photo-1614064641938-3bbee52942c7',  # hacker dark
        'photo-1510511233900-1982d92bd835',  # code lock
        'photo-1555949963-aa79dcee981c',     # server lock
        'photo-1504384308090-c894fdcc538d',  # cyber abstract
        'photo-1516321318423-f06f85e504b3',  # secure network
        'photo-1544197150-b99a580bb7a8',     # privacy network
        'photo-1573164713988-8665fc963095',  # dark hacker
        'photo-1603808033192-082d6919d3e1',  # encrypted code
        'photo-1569396116180-210c182bedb8',  # server room secure
        'photo-1591696205602-2f950c417cb9',  # circuit security
    ],
    'mobile-gadgets': [
        'photo-1511707171634-5f897ff02aa9',  # phone on desk
        'photo-1592750475338-74b7b21085ab',  # iPhone white
        'photo-1585060544812-6b45742d762f',  # gadgets flat lay
        'photo-1523206489230-c012c64b2b48',  # phone in hand
        'photo-1567581935884-3349723552ca',  # smartwatch
        'photo-1542751371-adc38448a05e',     # various devices
        'photo-1525547719571-a2d4ac8945e2',  # phones on table
        'photo-1616348436168-de43ad0db179',  # phone close-up
        'photo-1565849904461-04a58ad377e0',  # unboxing phone
        'photo-1601784551446-20c9e07cdbdb',  # wireless earbuds
        'photo-1583394838336-acd977736f90',  # headphones
        'photo-1570891836654-d4590d13d073',  # tablet and phone
    ],
    'consumer-tech': [
        'photo-1498049794561-7780e7231661',  # tech products
        'photo-1517694712202-14dd9538aa97',  # MacBook open
        'photo-1593642632559-0c6d3fc62b89',  # laptop Windows
        'photo-1519389950473-47ba0277781c',  # tech workspace
        'photo-1496181133206-80ce9b88a853',  # laptop closeup
        'photo-1504707748692-419802cf939d',  # consumer electronics
        'photo-1550009158-9ebf69173e03',     # keyboard setup
        'photo-1587829741301-dc798b83add3',  # PC setup
        'photo-1484788984921-03950022c9ef',  # home tech setup
        'photo-1547658719-da2b51169166',     # smart home device
        'photo-1560472355-536de3962603',     # tech lifestyle
        'photo-1468495244123-6c6c332eeece',  # headphones music
    ],
    'broadcast-tech': [
        'photo-1478737270239-2f02b77fc618',  # radio studio
        'photo-1612420696760-0a0f34d3e7d0',  # broadcasting
        'photo-1567095761054-7003afd47020',  # podcast mic
        'photo-1598488035139-bdbb2231ce04',  # audio mixer
        'photo-1478737270239-2f02b77fc618',  # radio desk
        'photo-1516321497487-e288fb19713f',  # TV production
        'photo-1574717024653-61fd2cf4d44d',  # video camera
        'photo-1590602847861-f357a9332bbc',  # camera lens
        'photo-1492619375914-88005aa9e8fb',  # broadcast camera
        'photo-1611532736597-de2d4265fba3',  # live streaming
        'photo-1623039405147-547794f92e9e',  # media production
        'photo-1540575467063-178a50c2df87',  # event broadcast
    ],
    'gaming': [
        'photo-1538481199705-c710c4e965fc',  # gaming monitor
        'photo-1493711662062-fa541adb3fc8',  # gaming controller
        'photo-1552820728-8b83bb6b773f',     # gaming setup RGB
        'photo-1601887389937-0b02f7683064',  # PC gaming rig
        'photo-1612287230202-1ff1d85d1bdf',  # Nintendo Switch
        'photo-1511512578047-dfb367046420',  # FPS game screen
        'photo-1574375927938-d5a98e8ffe85',  # PS5 controller
        'photo-1580327344181-c1163234e5a0',  # gaming headset
        'photo-1606144042614-b2417e99c4e3',  # arcade machine
        'photo-1560419015-7c427e8ae5ba',     # gaming joystick
        'photo-1586182987320-4f376d39d787',  # esports arena
        'photo-1569429593410-b498b3fb3387',  # retro gaming
    ],
    'evs-automotive': [
        'photo-1593941707882-a5bba14938c7',  # EV charging
        'photo-1558618666-fcd25c85cd64',     # Tesla side
        'photo-1616455579100-2ceaa4eb2d37',  # electric car interior
        'photo-1549317661-bd32c8ce0db2',     # car dashboard
        'photo-1502161254119-e1f02c5b5e4b',  # car at night
        'photo-1568605117036-5fe5e7bab0b7',  # luxury car front
        'photo-1580274455191-1c62238fa1f4',  # EV front
        'photo-1617469767053-d3b523a0b982',  # charging station
        'photo-1590362891991-f776e747a588',  # car highway
        'photo-1606016159991-dfe4f2746ad5',  # automotive tech
        'photo-1571987502227-9231b837d92a',  # electric motor
        'photo-1583121274602-3e2820c69888',  # sports car
    ],
    'startups-business': [
        'photo-1559136555-9303baea8ebd',     # startup office
        'photo-1507003211169-0a1dd7228f2d',  # business person
        'photo-1600880292203-757bb62b4baf',  # team meeting
        'photo-1450101499163-c8848c66ca85',  # signing deal
        'photo-1460925895917-afdab827c52f',  # laptop analytics
        'photo-1553484771-371a605b060b',     # fintech
        'photo-1579532537598-459ecdaf39cc',  # pitch meeting
        'photo-1521737604893-d14cc237f11d',  # startup team
        'photo-1537511446984-935f663eb1f4',  # co-working
        'photo-1486406146926-c627a92ad1ab',  # corporate building
        'photo-1573164713714-d95e436ab8d6',  # handshake deal
        'photo-1444653389962-8149286c578a',  # planning strategy
    ],
    'default': [
        'photo-1518770660439-4636190af475',  # circuit board
        'photo-1531297484001-80022131f5a1',  # laptop code
        'photo-1504639725590-34d0984388bd',  # code screen
        'photo-1519389950473-47ba0277781c',  # tech workspace
        'photo-1498049794561-7780e7231661',  # tech products
        'photo-1550751827-4bd374c3f58b',     # security
        'photo-1526374965328-7f61d4dc18c5',  # code matrix
        'photo-1480944657103-7fed22359e1d',  # server room
        'photo-1488229297570-58520851e868',  # laptop glowing
        'photo-1451187580459-43490279c0fa',  # earth tech
        'photo-1516321318423-f06f85e504b3',  # network
        'photo-1558494949-ef010cbdcc31',     # data streams
    ],
}


def is_safe_image(url):
    """Return True if the image URL comes from a copyright-safe source."""
    if not url:
        return False
    from urllib.parse import urlparse
    host = urlparse(url).netloc.lower().lstrip('www.')
    return any(host == d or host.endswith('.' + d) for d in SAFE_IMAGE_DOMAINS)


def copyright_safe_image(url, category_slug='default', article_key=''):
    """
    Return url unchanged if safe.
    Otherwise pick a unique fallback from the category pool using the article
    URL/title as a hash seed — deterministic and different for every article.
    """
    if is_safe_image(url):
        return url
    import hashlib
    pool = CATEGORY_IMAGE_POOLS.get(category_slug, CATEGORY_IMAGE_POOLS['default'])
    seed = (article_key or category_slug).encode('utf-8')
    idx  = int(hashlib.md5(seed).hexdigest(), 16) % len(pool)
    photo_id = pool[idx]
    return f'https://images.unsplash.com/{photo_id}?w=800&auto=format&fit=crop'


def assign_unique_images(items, category_slug):
    """
    Walk through a list of article dicts and assign copyright-safe images.
    - Articles that already have a safe image keep their original.
    - Articles needing a fallback get sequential pool images so that no two
      consecutive unsafe-image cards ever show the same photo.
    """
    pool = CATEGORY_IMAGE_POOLS.get(category_slug, CATEGORY_IMAGE_POOLS['default'])
    pool_len = len(pool)
    pool_cursor = 0  # increments only when a fallback is needed

    for item in items:
        original_url = item.get('image')
        if is_safe_image(original_url):
            item['image'] = original_url  # safe — keep as-is
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
    items = assign_unique_images(items, cat_slug)

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
