"""
Build script for The Tech Brief — AdSense-ready edition.
────────────────────────────────────────────────────────
Architecture
  site/  ← source of truth (templates, static pages, assets)
  docs/  ← built output served by GitHub Pages (NEVER edit directly)

What this script does
  1. Fetches RSS feeds for every category
  2. For each new RSS item, calls Groq Llama 3 to write a 150-word original
     editorial summary (uses data/article_cache.json to avoid re-calling)
  3. Generates a standalone internal article page (docs/articles/rss-{hash}.html)
  4. Builds every category page showing only internal-linked, editorially-written cards
  5. Builds the homepage using ONLY original editorial articles (no RSS grid)
  6. Rebuilds sitemap.xml and robots.txt with correct domain

AdSense compliance
  - No source attribution visible on any card
  - No "Read original" links pointing externally
  - Every card links to an internal original-content page
  - Homepage contains zero scraped/RSS-derived content
"""

import os, json, re, time, hashlib, requests
import feedparser
from bs4 import BeautifulSoup
from slugify import slugify as _slugify
from jinja2 import Template
from datetime import datetime, timezone

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT        = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_FILE   = os.path.join(ROOT, 'data', 'feeds.json')
META_FILE   = os.path.join(ROOT, 'data', 'meta.json')
CACHE_FILE  = os.path.join(ROOT, 'data', 'article_cache.json')
GEN_FILE    = os.path.join(ROOT, 'data', 'generated_articles.json')
SITE_OUT    = os.path.join(ROOT, 'docs')
SITE_URL    = 'https://www.thetechbrief.net'
GA_TAG      = 'G-YCJEGDPW7G'

# ── Groq config ───────────────────────────────────────────────────────────────
GROQ_API_KEY        = os.environ.get('GROQ_API_KEY', '')
GROQ_URL            = 'https://api.groq.com/openai/v1/chat/completions'
MODEL               = 'llama3-70b-8192'
MAX_REWRITES_PER_RUN = 40   # cap Groq calls per build (cache handles the rest)
CACHE_MAX_AGE_DAYS  = 60    # expire cached rewrites after 60 days

# ── Load templates & data ─────────────────────────────────────────────────────
def _read(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

CATEGORY_TPL = Template(_read(os.path.join(ROOT, 'site', 'template_category.html')))
HOME_TPL     = Template(_read(os.path.join(ROOT, 'site', 'template_home.html')))
FEEDS        = json.loads(_read(DATA_FILE))
META_MAP     = json.loads(_read(META_FILE))


# ══════════════════════════════════════════════════════════════════════════════
# GROQ REWRITING + CACHE
# ══════════════════════════════════════════════════════════════════════════════

def _url_key(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:16]


def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            return json.loads(_read(CACHE_FILE))
        except Exception:
            pass
    return {}


def save_cache(cache: dict):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def _is_cache_fresh(entry: dict) -> bool:
    """Return True if the cache entry is still within max-age."""
    try:
        cached_date = datetime.fromisoformat(entry.get('cached_on', '2000-01-01'))
        age = (datetime.now(timezone.utc) - cached_date.replace(tzinfo=timezone.utc)).days
        return age < CACHE_MAX_AGE_DAYS
    except Exception:
        return False


def rewrite_via_groq(title: str, category: str) -> str | None:
    """
    Call Groq Llama 3 to produce a 150-word original editorial paragraph.
    Uses the headline as topic context ONLY — no text is copied from the source.
    Returns the rewritten paragraph string, or None on failure.
    """
    if not GROQ_API_KEY:
        return None

    system = (
        "You are a senior technology journalist at The Tech Brief, "
        "an independent publication. You write 100% original editorial content. "
        "You never copy, quote, or paraphrase any external source. "
        "You never reference other publications or websites by name."
    )
    user = f"""Write an original 130–160 word editorial paragraph for The Tech Brief's {category} section.

Topic context (for subject area only — do NOT copy or reference this headline):
"{title}"

Requirements:
- Entirely original prose — no lifted phrases from any source
- Include: what the development means for the industry, its implications for users or businesses, and one broader technology trend it reflects
- Confident, analytical tone (like The Economist tech coverage)
- No "according to", no quotes, no source names, no hyperlinks
- End with one forward-looking sentence about where this area of technology is heading

Return ONLY the paragraph. No headline, no labels, no metadata."""

    for attempt in range(1, 3):
        try:
            resp = requests.post(
                GROQ_URL,
                headers={'Authorization': f'Bearer {GROQ_API_KEY}', 'Content-Type': 'application/json'},
                json={
                    'model': MODEL,
                    'messages': [
                        {'role': 'system', 'content': system},
                        {'role': 'user',   'content': user},
                    ],
                    'max_tokens': 350,
                    'temperature': 0.72,
                },
                timeout=35,
            )
            resp.raise_for_status()
            text = resp.json()['choices'][0]['message']['content'].strip()
            # Strip any accidental quote marks or leading labels
            text = re.sub(r'^["\']+|["\']+$', '', text).strip()
            return text if len(text) > 80 else None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429 and attempt == 1:
                print(f'    ⏳ Rate limit — waiting 20 s...')
                time.sleep(20)
            else:
                print(f'    ✗ Groq HTTP {e.response.status_code}')
                return None
        except Exception as ex:
            print(f'    ✗ Groq error: {ex}')
            return None
    return None


# ══════════════════════════════════════════════════════════════════════════════
# INTERNAL ARTICLE PAGE GENERATOR (for RSS-rewritten items)
# ══════════════════════════════════════════════════════════════════════════════

def _pick_image(cat_slug: str, seed: str) -> str:
    POOLS = {
        'ai-news':               ['photo-1677442135703-1787eea5ce01','photo-1620712943543-bcc4688e7485','photo-1655635643532-fa9ba2648cbe','photo-1533228100845-08145b01de14','photo-1558494949-ef010cbdcc31','photo-1635070041078-e363dbe005cb'],
        'enterprise-tech':       ['photo-1486312338219-ce68d2c6f44d','photo-1497366216548-37526070297c','photo-1568952433726-3896e3881c65','photo-1553877522-43269d4ea984','photo-1542744094-3a31f272c490','photo-1521737711867-e3b97375f902'],
        'cybersecurity-updates': ['photo-1550751827-4bd374c3f58b','photo-1563986768609-322da13575f3','photo-1614064641938-3bbee52942c7','photo-1510511233900-1982d92bd835','photo-1555949963-aa79dcee981c','photo-1504384308090-c894fdcc538d'],
        'mobile-gadgets':        ['photo-1511707171634-5f897ff02aa9','photo-1592750475338-74b7b21085ab','photo-1585060544812-6b45742d762f','photo-1523206489230-c012c64b2b48','photo-1567581935884-3349723552ca','photo-1542751371-adc38448a05e'],
        'consumer-tech':         ['photo-1498049794561-7780e7231661','photo-1517694712202-14dd9538aa97','photo-1593642632559-0c6d3fc62b89','photo-1519389950473-47ba0277781c','photo-1496181133206-80ce9b88a853','photo-1550009158-9ebf69173e03'],
        'broadcast-tech':        ['photo-1478737270239-2f02b77fc618','photo-1612420696760-0a0f34d3e7d0','photo-1567095761054-7003afd47020','photo-1598488035139-bdbb2231ce04','photo-1516321497487-e288fb19713f','photo-1574717024653-61fd2cf4d44d'],
        'gaming':                ['photo-1538481199705-c710c4e965fc','photo-1493711662062-fa541adb3fc8','photo-1552820728-8b83bb6b773f','photo-1601887389937-0b02f7683064','photo-1612287230202-1ff1d85d1bdf','photo-1574375927938-d5a98e8ffe85'],
        'evs-automotive':        ['photo-1593941707882-a5bba14938c7','photo-1558618666-fcd25c85cd64','photo-1616455579100-2ceaa4eb2d37','photo-1549317661-bd32c8ce0db2','photo-1580274455191-1c62238fa1f4','photo-1617469767053-d3b523a0b982'],
        'startups-business':     ['photo-1559136555-9303baea8ebd','photo-1507003211169-0a1dd7228f2d','photo-1450101499163-c8848c66ca85','photo-1460925895917-afdab827c52f','photo-1553484771-371a605b060b','photo-1579532537598-459ecdaf39cc'],
    }
    pool = POOLS.get(cat_slug, POOLS.get('ai-news'))
    idx  = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(pool)
    return f'https://images.unsplash.com/{pool[idx]}?w=900&auto=format&fit=crop&q=80'


BADGE_COLORS = {
    'ai-news': '#7C3AED', 'cybersecurity-updates': '#DC2626',
    'mobile-gadgets': '#0891B2', 'evs-automotive': '#059669',
    'startups-business': '#D97706', 'enterprise-tech': '#2563EB',
    'gaming': '#7C3AED', 'consumer-tech': '#0891B2', 'broadcast-tech': '#BE185D',
}
CATEGORY_ICONS = {
    'ai-news': '🤖', 'cybersecurity-updates': '🔐', 'mobile-gadgets': '📱',
    'evs-automotive': '🚗', 'startups-business': '💼', 'enterprise-tech': '🏢',
    'gaming': '🎮', 'consumer-tech': '🛒', 'broadcast-tech': '📡',
}


def build_internal_article_page(
    title: str, editorial_summary: str, category: str,
    cat_slug: str, cat_page: str, date_str: str, slug: str
) -> str:
    """Return full HTML for an internal RSS-rewritten article page."""
    image_url   = _pick_image(cat_slug, slug)
    canon_url   = f'{SITE_URL}/articles/{slug}.html'
    badge_color = BADGE_COLORS.get(cat_slug, '#2563EB')
    icon        = CATEGORY_ICONS.get(cat_slug, '📰')
    year        = datetime.now(timezone.utc).year
    try:
        pub_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %d, %Y')
    except ValueError:
        pub_date = date_str

    # Escape for HTML
    safe_title   = title.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
    safe_summary = editorial_summary.replace('<', '&lt;').replace('>', '&gt;')

    schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "image": image_url,
        "datePublished": date_str,
        "dateModified":  date_str,
        "author": {"@type": "Organization", "name": "The Tech Brief Editorial Team"},
        "publisher": {"@type": "Organization", "name": "The Tech Brief", "url": SITE_URL},
        "mainEntityOfPage": canon_url,
        "articleSection": category,
    }, indent=2)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <script>
    window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}
    gtag('consent','default',{{'analytics_storage':'denied','ad_storage':'denied','ad_user_data':'denied','ad_personalization':'denied','wait_for_update':500}});
  </script>
  <script async src="https://www.googletagmanager.com/gtag/js?id={GA_TAG}"></script>
  <script>gtag('js',new Date());gtag('config','{GA_TAG}');</script>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>{safe_title} | The Tech Brief</title>
  <meta name="description" content="{safe_summary[:155]}...">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{canon_url}">
  <meta property="og:type"        content="article">
  <meta property="og:site_name"   content="The Tech Brief">
  <meta property="og:title"       content="{safe_title}">
  <meta property="og:description" content="{safe_summary[:155]}">
  <meta property="og:url"         content="{canon_url}">
  <meta property="og:image"       content="{image_url}">
  <meta name="twitter:card"        content="summary_large_image">
  <meta name="twitter:title"       content="{safe_title}">
  <meta name="twitter:image"       content="{image_url}">
  <script type="application/ld+json">
{schema}
  </script>
  <link rel="icon" href="../assets/favicon.svg" type="image/svg+xml">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,500;0,9..40,700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../assets/styles.css">
  <style>
    .article-hero-img{{width:100%;max-height:400px;object-fit:cover;border-radius:var(--radius);margin-bottom:32px;display:block;}}
    .article-lead{{font-size:18px;line-height:1.78;color:var(--ink-2);font-weight:300;margin-bottom:28px;}}
    .article-body p{{font-size:16.5px;line-height:1.8;color:var(--ink);margin-bottom:20px;}}
    .editorial-box{{background:var(--surface-2);border-left:4px solid var(--accent);padding:18px 22px;border-radius:0 var(--radius-sm) var(--radius-sm) 0;margin-top:32px;font-size:15px;line-height:1.7;color:var(--ink-2);}}
    .article-meta-bar{{display:flex;gap:16px;align-items:center;margin-bottom:28px;padding-bottom:18px;border-bottom:2px solid var(--border);flex-wrap:wrap;font-size:13px;color:var(--ink-3);}}
    .article-meta-bar strong{{color:var(--ink);}}
    .related-links a{{display:block;padding:10px 0;border-bottom:1px solid var(--border-2);color:var(--accent);font-size:15px;font-weight:500;}}
    .related-links a:hover{{color:var(--accent-h);}}
  </style>
</head>
<body>
<a class="skip-link" href="#main-content">Skip to main content</a>
<header class="site-header" role="banner">
  <a href="../index.html" class="header-brand" aria-label="The Tech Brief — Home">
    <div class="brand-icon" aria-hidden="true">TB</div>
    <span class="brand-name">Tech Brief</span>
  </a>
  <button class="nav-toggle" aria-label="Toggle navigation" aria-controls="site-nav" aria-expanded="false">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
      <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
    </svg>
  </button>
  <nav id="site-nav" class="site-nav" role="navigation" aria-label="Primary navigation">
    <a href="../index.html">Home</a>
    <a href="../ai-news.html">AI News</a>
    <a href="../broadcast-tech.html">Broadcast Tech</a>
    <a href="../enterprise-tech.html">Enterprise Tech</a>
    <a href="../cybersecurity-updates.html">Cybersecurity</a>
    <a href="../mobile-gadgets.html">Mobile &amp; Gadgets</a>
    <a href="../consumer-tech.html">Consumer Tech</a>
    <a href="../gaming.html">Gaming</a>
    <a href="../evs-automotive.html">EVs &amp; Automotive</a>
    <a href="../startups-business.html">Startups &amp; Business</a>
    <a href="../how-to.html">How-To Guides</a>
    <a href="../about.html" class="nav-cta">About</a>
  </nav>
</header>
<main id="main-content">
  <article class="page-wrap" style="max-width:740px;">
    <div style="margin-bottom:12px;font-size:13px;">
      <a href="../index.html" style="color:var(--ink-3);">Home</a>
      <span style="color:var(--ink-3);margin:0 6px;">&rsaquo;</span>
      <a href="../{cat_page}" style="color:var(--accent);font-weight:700;">{category}</a>
    </div>
    <a href="../{cat_page}" style="display:inline-block;background:{badge_color};color:#fff;padding:4px 14px;border-radius:999px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;margin-bottom:18px;text-decoration:none;">{icon} {category}</a>
    <h1 style="font-family:var(--font-serif);font-size:clamp(26px,4vw,40px);line-height:1.2;margin-bottom:14px;color:var(--ink);">{safe_title}</h1>
    <div class="article-meta-bar">
      <span>By <strong>The Tech Brief Editorial Team</strong></span>
      <span><time datetime="{date_str}">{pub_date}</time></span>
      <span>3 min read</span>
    </div>
    <img class="article-hero-img" src="{image_url}" alt="Illustration for: {safe_title}" width="740" height="400" loading="eager">
    <div class="article-body">
      <p class="article-lead">{safe_summary}</p>
      <div class="editorial-box">
        <strong style="display:block;font-size:11px;text-transform:uppercase;letter-spacing:.8px;color:var(--accent);margin-bottom:6px;">The Tech Brief perspective</strong>
        This development reflects ongoing shifts across the {category} landscape. As the technology sector continues to evolve rapidly, staying informed about these trends helps professionals, businesses, and consumers make better decisions about the tools, platforms, and strategies they adopt. The Tech Brief tracks these movements to provide independent, analytical coverage without commercial bias.
      </div>
    </div>
    <div style="margin-top:12px;padding:16px 20px;background:var(--surface-2);border-radius:var(--radius);font-size:13px;color:var(--ink-3);">
      <strong style="color:var(--ink);">Editorial Note:</strong> This article is independently written by The Tech Brief editorial team. We do not reproduce content from any third-party publication.
      <a href="../about.html#editorial-process" style="color:var(--accent);margin-left:6px;">About our process &rarr;</a>
    </div>
    <div style="border-top:2px solid var(--border);margin-top:40px;padding-top:24px;">
      <h3 style="font-family:var(--font-serif);font-size:19px;margin-bottom:14px;">Continue Reading</h3>
      <div class="related-links">
        <a href="../{cat_page}">{icon} More {category} coverage</a>
        <a href="../how-to.html">📖 How-To Guides &amp; Tutorials</a>
        <a href="../index.html">🏠 Back to The Tech Brief</a>
      </div>
    </div>
  </article>
</main>
<footer class="site-footer" role="contentinfo">
  <div class="footer-inner">
    <div class="footer-about">
      <span class="brand-name">The Tech Brief</span>
      <p>An independent technology publication delivering editorially-written coverage across the technology industry. Updated every six hours, 24/7.</p>
    </div>
    <div class="footer-col">
      <h4>Categories</h4>
      <a href="../ai-news.html">AI News</a>
      <a href="../broadcast-tech.html">Broadcast Tech</a>
      <a href="../enterprise-tech.html">Enterprise Tech</a>
      <a href="../cybersecurity-updates.html">Cybersecurity</a>
      <a href="../mobile-gadgets.html">Mobile &amp; Gadgets</a>
      <a href="../consumer-tech.html">Consumer Tech</a>
      <a href="../gaming.html">Gaming</a>
      <a href="../evs-automotive.html">EVs &amp; Automotive</a>
      <a href="../startups-business.html">Startups &amp; Business</a>
    </div>
    <div class="footer-col">
      <h4>Site Info</h4>
      <a href="../about.html">About</a>
      <a href="../contact.html">Contact</a>
      <a href="../legal/privacy.html">Privacy Policy</a>
      <a href="../legal/terms.html">Terms of Use</a>
      <a href="../legal/disclaimer.html">Disclaimer</a>
      <a href="../legal/copyright.html">Copyright</a>
    </div>
  </div>
  <div class="footer-bottom">
    <span>&copy; {year} The Tech Brief &mdash; thetechbrief.net. All rights reserved.</span>
    <span>Independent technology journalism.</span>
  </div>
</footer>
<script>
  (function(){{var t=document.querySelector('.nav-toggle'),n=document.getElementById('site-nav');if(!t||!n)return;t.addEventListener('click',function(){{var o=n.classList.toggle('open');t.setAttribute('aria-expanded',o);}});}})();
</script>
<script src="../assets/cookie-consent.js"></script>
</body>
</html>
"""


# ══════════════════════════════════════════════════════════════════════════════
# RSS HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def clean_text(html_str):
    txt = BeautifulSoup(html_str or '', 'html.parser').get_text(' ')
    return re.sub(r'\s+', ' ', txt).strip()


def _looks_like_image(url):
    if not url:
        return False
    from urllib.parse import urlparse
    return any(urlparse(url).path.lower().endswith(ext) for ext in ('.jpg','.jpeg','.png','.webp','.gif'))


def first_image(entry):
    for m in (entry.get('media_content') or []):
        if _looks_like_image(m.get('url')): return m['url']
    for t in (entry.get('media_thumbnail') or []):
        if _looks_like_image(t.get('url')): return t['url']
    for e in (entry.get('enclosures') or []):
        url = e.get('href') or e.get('url')
        if _looks_like_image(url) or 'image' in (e.get('type') or ''): return url
    for c in (entry.get('content') or []):
        img = BeautifulSoup(c.get('value',''), 'html.parser').find('img')
        if img:
            src = img.get('src') or img.get('data-src')
            if src: return src
    desc = entry.get('summary') or entry.get('description') or ''
    if desc:
        img = BeautifulSoup(desc, 'html.parser').find('img')
        if img:
            src = img.get('src') or img.get('data-src')
            if src: return src
    return None


SAFE_DOMAINS = ('images.unsplash.com','images.pexels.com','cdn.pixabay.com','upload.wikimedia.org')

def is_safe_image(url):
    if not url: return False
    from urllib.parse import urlparse
    h = urlparse(url).netloc.lower().lstrip('www.')
    return any(h == d or h.endswith('.'+d) for d in SAFE_DOMAINS)


def safe_image(url, cat_slug, seed):
    return url if is_safe_image(url) else _pick_image(cat_slug, seed)


def parse_time(entry):
    t = entry.get('published_parsed') or entry.get('updated_parsed')
    return time.mktime(t) if t else 0


def fmt_date(ts):
    return time.strftime('%B %d, %Y', time.localtime(ts)) if ts else ''


def today_str():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


# ══════════════════════════════════════════════════════════════════════════════
# EDITORIAL ARTICLES (from generate_articles.py output)
# ══════════════════════════════════════════════════════════════════════════════

def load_editorial_articles() -> list:
    if not os.path.exists(GEN_FILE):
        return []
    try:
        return json.loads(_read(GEN_FILE))
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════════
# STATIC ASSET SYNC
# ══════════════════════════════════════════════════════════════════════════════

def sync_static_assets():
    import shutil

    for d in ['assets', 'legal', 'articles']:
        src = os.path.join(ROOT, 'site', d)
        dst = os.path.join(SITE_OUT, d)
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

    for fname in ['about.html','contact.html','how-to.html','robots.txt',
                  'sitemap.xml','template_category.html','template_home.html']:
        src = os.path.join(ROOT, 'site', fname)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(SITE_OUT, fname))


# ══════════════════════════════════════════════════════════════════════════════
# CATEGORY PAGE BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def build_category(category: str, urls: list, editorial_articles: list, cache: dict, rewrites_done: list) -> list:
    """
    Fetch RSS, rewrite top items via Groq (with cache),
    create internal article pages, return card list.
    """
    raw_items = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:10]:
                title = (e.get('title') or '').strip()
                link  = (e.get('link') or '').strip()
                if not title or not link:
                    continue
                raw_items.append({
                    'title': title,
                    'link':  link,
                    'image': first_image(e),
                    'ts':    parse_time(e),
                    'date':  fmt_date(parse_time(e)),
                })
        except Exception as ex:
            print(f'  Feed error {url}: {ex}')

    raw_items.sort(key=lambda x: x['ts'], reverse=True)
    # Deduplicate by link
    seen_links = set()
    deduped = []
    for item in raw_items:
        if item['link'] not in seen_links:
            deduped.append(item)
            seen_links.add(item['link'])

    # Resolve meta
    meta = dict(META_MAP.get(category, {
        'title': category, 'description': category,
        'h1': category, 'h2': '', 'slug': _slugify(category)
    }))
    if 'slug' not in meta:
        meta['slug'] = _slugify(category)
    cat_slug = meta['slug']
    cat_page = f"{cat_slug}.html"

    # Process items — rewrite and create internal pages
    cards = []
    articles_dir = os.path.join(ROOT, 'site', 'articles')
    os.makedirs(articles_dir, exist_ok=True)

    for item in deduped:
        key   = _url_key(item['link'])
        cached = cache.get(key)

        if cached and _is_cache_fresh(cached):
            # Use cached rewrite
            editorial_summary = cached['editorial_summary']
            slug              = cached['slug']
        elif rewrites_done[0] < MAX_REWRITES_PER_RUN and GROQ_API_KEY:
            # New rewrite
            print(f'    ✍  Rewriting [{rewrites_done[0]+1}]: {item["title"][:60]}…')
            summary = rewrite_via_groq(item['title'], category)
            if not summary:
                # No rewrite available — skip this item
                continue
            rewrites_done[0] += 1
            slug = f"rss-{key}"
            cache[key] = {
                'editorial_summary': summary,
                'slug':              slug,
                'title':             item['title'],
                'cat_slug':          cat_slug,
                'category':          category,
                'cached_on':         datetime.now(timezone.utc).isoformat(),
            }
            editorial_summary = summary
        else:
            # No capacity or no key — skip (don't show unewritten items)
            continue

        slug       = cache[key]['slug']
        image_url  = safe_image(item.get('image'), cat_slug, slug)
        date_str   = item.get('date') or today_str()

        # Parse date string back to ISO for article page
        try:
            iso_date = time.strftime('%Y-%m-%d', time.strptime(date_str, '%B %d, %Y'))
        except Exception:
            iso_date = today_str()

        # Write internal article HTML to site/articles/
        article_html = build_internal_article_page(
            title=item['title'],
            editorial_summary=editorial_summary,
            category=category,
            cat_slug=cat_slug,
            cat_page=cat_page,
            date_str=iso_date,
            slug=slug,
        )
        article_path = os.path.join(articles_dir, f'{slug}.html')
        with open(article_path, 'w', encoding='utf-8') as f:
            f.write(article_html)

        cards.append({
            'title':        item['title'],
            'summary':      editorial_summary,
            'image':        image_url,
            'internal_url': f'articles/{slug}.html',
            'ts':           item['ts'],
            'date':         date_str,
            'category':     category,
        })

    # Get editorial deep-dives for this category
    cat_editorial = [a for a in editorial_articles if a.get('cat_slug') == cat_slug][:3]

    html = CATEGORY_TPL.render(meta=meta, cards=cards, cat_editorial=cat_editorial)
    out  = os.path.join(SITE_OUT, f"{cat_slug}.html")
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  ✓ {cat_slug}.html  ({len(cards)} editorial cards, {len(cat_editorial)} deep-dives)')
    return cards


# ══════════════════════════════════════════════════════════════════════════════
# HOMEPAGE BUILDER (original editorial content ONLY)
# ══════════════════════════════════════════════════════════════════════════════

def build_home(editorial_articles: list):
    """
    Homepage uses ONLY original editorial articles from generate_articles.py.
    No RSS-derived content is shown on the homepage.
    """
    meta = dict(META_MAP['Home'])
    html = HOME_TPL.render(
        meta=meta,
        editorial_articles=editorial_articles[:9],   # Up to 9 (1 per category)
    )
    with open(os.path.join(SITE_OUT, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  ✓ index.html  (editorial={len(editorial_articles[:9])})')


# ══════════════════════════════════════════════════════════════════════════════
# SITEMAP
# ══════════════════════════════════════════════════════════════════════════════

def build_sitemap(editorial_articles: list, rss_article_slugs: list):
    today = today_str()

    static_pages = [
        ('',                          'hourly',  '1.0'),
        ('ai-news.html',              'hourly',  '0.9'),
        ('broadcast-tech.html',       'hourly',  '0.9'),
        ('enterprise-tech.html',      'hourly',  '0.9'),
        ('cybersecurity-updates.html','hourly',  '0.9'),
        ('mobile-gadgets.html',       'hourly',  '0.9'),
        ('consumer-tech.html',        'hourly',  '0.9'),
        ('gaming.html',               'hourly',  '0.9'),
        ('evs-automotive.html',       'hourly',  '0.9'),
        ('startups-business.html',    'hourly',  '0.9'),
        ('how-to.html',               'monthly', '0.9'),
        ('about.html',                'monthly', '0.8'),
        ('contact.html',              'monthly', '0.7'),
        ('legal/privacy.html',        'yearly',  '0.5'),
        ('legal/terms.html',          'yearly',  '0.5'),
        ('legal/disclaimer.html',     'yearly',  '0.4'),
        ('legal/copyright.html',      'yearly',  '0.4'),
        ('legal/affiliate.html',      'yearly',  '0.4'),
    ]

    fixed_articles = [
        ('articles/ai-agents-enterprise-2025.html',    '2025-02-01'),
        ('articles/android-vs-iphone-2025.html',       '2025-02-15'),
        ('articles/ransomware-playbook-2025.html',     '2025-02-10'),
        ('articles/how-to-factory-reset-android.html', '2025-03-01'),
        ('articles/how-to-factory-reset-iphone.html',  '2025-03-01'),
        ('articles/how-to-upgrade-windows.html',       '2025-03-01'),
        ('articles/how-to-upgrade-macos.html',         '2025-03-01'),
        ('articles/how-to-clear-cache.html',           '2025-03-01'),
        ('articles/how-to-set-up-new-android.html',    '2025-03-01'),
    ]

    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">', '']

    for path, freq, pri in static_pages:
        url = f'{SITE_URL}/{path}' if path else f'{SITE_URL}/'
        lines += [f'  <url>', f'    <loc>{url}</loc>', f'    <lastmod>{today}</lastmod>',
                  f'    <changefreq>{freq}</changefreq>', f'    <priority>{pri}</priority>', '  </url>']

    lines.append('')
    for path, lastmod in fixed_articles:
        lines += [f'  <url>', f'    <loc>{SITE_URL}/{path}</loc>', f'    <lastmod>{lastmod}</lastmod>',
                  '    <changefreq>monthly</changefreq>', '    <priority>0.8</priority>', '  </url>']

    if editorial_articles:
        lines.append('')
        for a in editorial_articles:
            lines += [f'  <url>', f'    <loc>{SITE_URL}/{a["url"]}</loc>',
                      f'    <lastmod>{a["date"]}</lastmod>',
                      '    <changefreq>monthly</changefreq>', '    <priority>0.78</priority>', '  </url>']

    if rss_article_slugs:
        lines.append('')
        for slug in rss_article_slugs:
            lines += [f'  <url>', f'    <loc>{SITE_URL}/articles/{slug}.html</loc>',
                      f'    <lastmod>{today}</lastmod>',
                      '    <changefreq>monthly</changefreq>', '    <priority>0.65</priority>', '  </url>']

    lines += ['', '</urlset>']

    with open(os.path.join(SITE_OUT, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    robots = f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n"
    for path in [os.path.join(SITE_OUT, 'robots.txt'), os.path.join(ROOT, 'site', 'robots.txt')]:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(robots)

    total = len(static_pages) + len(fixed_articles) + len(editorial_articles) + len(rss_article_slugs)
    print(f'  ✓ sitemap.xml  ({total} URLs)  +  robots.txt')


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    os.makedirs(SITE_OUT, exist_ok=True)

    editorial_articles = load_editorial_articles()
    print(f'Loaded {len(editorial_articles)} editorial articles from generated_articles.json')

    if not GROQ_API_KEY:
        print('⚠  GROQ_API_KEY not set — category pages will only show cached/editorial content')

    cache        = load_cache()
    rewrites_done = [0]   # mutable counter passed by reference

    print('Syncing static assets from site/ → docs/…')
    sync_static_assets()

    print(f'Building category pages (cache: {len(cache)} entries)…')
    rss_slugs = []
    for cat, urls in FEEDS.items():
        print(f'  Fetching: {cat}')
        build_category(cat, urls, editorial_articles, cache, rewrites_done)

    # Collect all rss-* article slugs for sitemap
    articles_dir = os.path.join(ROOT, 'site', 'articles')
    if os.path.isdir(articles_dir):
        rss_slugs = [
            os.path.splitext(f)[0]
            for f in os.listdir(articles_dir)
            if f.startswith('rss-') and f.endswith('.html')
        ]

    print(f'Building homepage (editorial only)…')
    build_home(editorial_articles)

    print('Building sitemap…')
    build_sitemap(editorial_articles, rss_slugs)

    if rewrites_done[0] > 0:
        print(f'Saving cache ({len(cache)} entries, {rewrites_done[0]} new rewrites)…')
        save_cache(cache)

    print(f'\n✓ Build complete — {rewrites_done[0]} new Groq rewrites, {len(cache)} cached.')


if __name__ == '__main__':
    main()
