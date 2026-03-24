"""
Build script for The Tech Brief V3 — Intelligence Platform Edition
════════════════════════════════════════════════════════════════════

V3 UPGRADES over V2:
  UPGRADE 1 — Full Groq Intelligence Prompt System
    Each article is now generated using an 8-task intelligence pipeline:
    Task 1: Category mapping + tech term extraction
    Task 2: Technology intelligence brief (exec summary, key techs, trend analysis)
    Task 3: Premium AdSense-approved article (650–900w, E-E-A-T optimised)
    Task 4: SEO + high-CPC keyword optimisation
    Result: every article reads like expert analysis, not a news summary.

  UPGRADE 2 — V3 Design System
    New templates use Playfair Display + IBM Plex Sans, ticker bar,
    intel-card components, featured-first layout, pulse hero.

  UPGRADE 3 — Richer Article Pages
    Article pages now include: executive summary callout, trend analysis
    sidebar, "Why This Matters" section, key technology definitions,
    strategic insights, and related articles.

  UPGRADE 4 — Smart Trending (unchanged from V2, retained)
    3-tier fallback: Groq → stale cache → local editorial template.
    Never-blank guarantee.

  UPGRADE 5 — Improved homepage context injection
    build_home() now passes per-category article slices to the template,
    enabling category-specific sections (AI deep dives, Cyber alerts, etc.)

GROQ OPTIMISATION RULES (from editorial brief):
  - Concise but high-impact prose
  - Maximise insight per token
  - No fluff or repetition
  - Expert-level analytical tone
  - Structured: H2/H3 with "Why it Matters" sections
  - High CPC keywords woven in naturally
"""

import os, json, re, time, hashlib, requests
import feedparser
from bs4 import BeautifulSoup
from slugify import slugify as _slugify
from jinja2 import Template
from datetime import datetime, timezone

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT       = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_FILE  = os.path.join(ROOT, 'data', 'feeds.json')
META_FILE  = os.path.join(ROOT, 'data', 'meta.json')
CACHE_FILE = os.path.join(ROOT, 'data', 'article_cache.json')
GEN_FILE   = os.path.join(ROOT, 'data', 'generated_articles.json')
SITE_SRC   = os.path.join(ROOT, 'site')
SITE_OUT   = os.path.join(ROOT, 'docs')
SITE_URL   = 'https://www.thetechbrief.net'
GA_TAG     = 'G-YCJEGDPW7G'

RSS_ARTICLES_OUT = os.path.join(SITE_OUT, 'articles')

# ── Groq config ────────────────────────────────────────────────────────────
GROQ_API_KEY         = os.environ.get('GROQ_API_KEY', '')
GROQ_URL             = 'https://api.groq.com/openai/v1/chat/completions'
MODEL                = 'llama3-70b-8192'
MAX_REWRITES_PER_RUN = 40
CACHE_MAX_AGE_DAYS   = 60

# ── Load templates & data ──────────────────────────────────────────────────
def _read(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

CATEGORY_TPL = Template(_read(os.path.join(ROOT, 'site', 'template_category.html')))
HOME_TPL     = Template(_read(os.path.join(ROOT, 'site', 'template_home.html')))
FEEDS        = json.loads(_read(DATA_FILE))
META_MAP     = json.loads(_read(META_FILE))


# ══════════════════════════════════════════════════════════════════════════════
# CURATED IMAGE POOLS — 12 relevant Unsplash IDs per category
# ══════════════════════════════════════════════════════════════════════════════

_IMAGE_POOLS = {
    'ai-news': [
        'photo-1677442135703-1787eea5ce01','photo-1620712943543-bcc4688e7485',
        'photo-1655635643532-fa9ba2648cbe','photo-1633356122544-f134324a6cee',
        'photo-1591453089816-0fbb971b454c','photo-1526374965328-7f61d4dc18c5',
        'photo-1531297484001-80022131f5a1','photo-1451187580459-43490279c0fa',
        'photo-1504639725590-34d0984388bd','photo-1560472354-b33ff0c44a43',
        'photo-1518770660439-4636190af475','photo-1635070041078-e363dbe005cb',
    ],
    'enterprise-tech': [
        'photo-1558494949-ef010cbdcc31','photo-1544197150-b99a580bb7a8',
        'photo-1560472354-b33ff0c44a43','photo-1497366216548-37526070297c',
        'photo-1486312338219-ce68d2c6f44d','photo-1542744094-3a31f272c490',
        'photo-1521737711867-e3b97375f902','photo-1454165804606-c3d57bc86b40',
        'photo-1461749280684-dccba630e2f6','photo-1600880292203-757bb62b4baf',
        'photo-1553877522-43269d4ea984','photo-1568952433726-3896e3881c65',
    ],
    'cybersecurity-updates': [
        'photo-1614064641938-3bbee52942c7','photo-1550751827-4bd374173b4e',
        'photo-1526374870839-e155464bb9b2','photo-1510511459019-5dda7724fd87',
        'photo-1563986768609-322da13575f3','photo-1555949963-ff9fe0c870eb',
        'photo-1544890225-2f3faec4cd60','photo-1629654297299-c8506221ca97',
        'photo-1591696205602-2f950c417cb9','photo-1571786256017-aee7a0c009b6',
        'photo-1558494949-ef010cbdcc31','photo-1516321165247-4aa89a48be55',
    ],
    'mobile-gadgets': [
        'photo-1511707171634-5f897ff02aa9','photo-1601784551446-20c9e07cdbdb',
        'photo-1512941937669-90a1b58e7e9c','photo-1556742049-0cfed4f6a45d',
        'photo-1567581935884-3349723552ca','photo-1585771724684-38269d6639fd',
        'photo-1574944985070-8f3ebc6b79d2','photo-1610945415295-d9bbf067e59c',
        'photo-1592750475338-74b7b21085ab','photo-1546054454-aa26e2b734c7',
        'photo-1570101945621-945409a6370f','photo-1533228100845-08145b01de14',
    ],
    'evs-automotive': [
        'photo-1593941707882-a5bba14938c7','photo-1536700503279-b837f40f7d49',
        'photo-1565043589221-1a6fd9ae45c7','photo-1617788138017-80ad40651399',
        'photo-1544620347-c4fd4a3d5957','photo-1558981403-c5f9899a28bc',
        'photo-1489824904134-891ab64532f1','photo-1502877338535-766e1452684a',
        'photo-1541899481282-d53bffe3c35d','photo-1494976388531-d1058494cdd8',
        'photo-1600712242805-5f78671b24da','photo-1571319914392-0ba44b05e96b',
    ],
    'startups-business': [
        'photo-1559136555-9303baea8ebd','photo-1553028826-f4804a6dba3b',
        'photo-1460925895917-afdab827c52f','photo-1507003211169-0a1dd7228f2d',
        'photo-1444653614773-995cb1ef9aca','photo-1551288049-bebda4e38f71',
        'photo-1562577309-4932fdd64cd1','photo-1521737852567-6949f3f9f2b5',
        'photo-1556761175-4b46a572b786','photo-1499750310107-5fef28a66643',
        'photo-1542744173-8e7e53415bb0','photo-1553484771-371a605b060b',
    ],
    'gaming': [
        'photo-1542751371-adc38448a05e','photo-1511512578047-dfb367046420',
        'photo-1593305841991-05c297ba4575','photo-1538481199705-c710c4e965fc',
        'photo-1612287230202-1ff1d85d1bdf','photo-1486401899868-0e435ed85128',
        'photo-1550745165-9bc0b252726f','photo-1597211584474-ae3171c7dbea',
        'photo-1616440347437-b1c73416efc2','photo-1563089145-599997674d42',
        'photo-1585620385456-4759f9b5c7d9','photo-1492144534655-ae79c964c9d7',
    ],
    'consumer-tech': [
        'photo-1525547719571-a2d4ac8945e2','photo-1583394293214-58b84be24c27',
        'photo-1498049794561-7780e7231661','photo-1546054454-aa26e2b734c7',
        'photo-1491553895911-0055eca6402d','photo-1505740420928-5e560c06d30e',
        'photo-1484704849700-f032a568e944','photo-1583394838336-acd977736f90',
        'photo-1519558260268-cde7e03a0152','photo-1523275335684-37898b6baf30',
        'photo-1572635196237-14b3f281503f','photo-1585060544812-6b45742d762f',
    ],
    'broadcast-tech': [
        'photo-1478737270239-2f02b77fc618','photo-1540575467063-178a50c2df87',
        'photo-1598488035139-bdbb2231ce04','photo-1574717024653-61fd2cf4d44d',
        'photo-1485846234645-a62644f84728','photo-1593508512255-86ab42a8e620',
        'photo-1522869635100-9f4c5e86aa37','photo-1616469829581-73993eb86b02',
        'photo-1624705002806-5d72df19c3ad','photo-1487611459768-bd414656ea10',
        'photo-1521737604893-d14cc237f11d','photo-1553406830-ef2513450d76',
    ],
}

def _pick_image(cat_slug: str, seed: str) -> str:
    pool = _IMAGE_POOLS.get(cat_slug, _IMAGE_POOLS['ai-news'])
    idx  = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(pool)
    return f'https://images.unsplash.com/{pool[idx]}?w=800&q=80'


# ══════════════════════════════════════════════════════════════════════════════
# LOCAL FALLBACK CONTENT
# ══════════════════════════════════════════════════════════════════════════════

_FRAMING = [
    "The latest developments in {topic} signal a meaningful inflection point for the industry. Organisations that move quickly to understand the implications will be better positioned to adapt their strategies and workflows before competitors do.",
    "As {topic} continues to evolve, the gap between early adopters and laggards is widening rapidly. The technical and strategic stakes are higher than most industry observers currently appreciate.",
    "The {topic} space is experiencing compounding momentum that goes beyond the usual hype cycle. Underlying adoption metrics and capital allocation patterns suggest this is a durable structural shift, not a transient trend.",
    "Recent signals from the {topic} ecosystem point to accelerating maturity. The transition from experimental deployments to production-grade infrastructure is underway across multiple sectors simultaneously.",
    "What is unfolding in {topic} represents a convergence of technical capability, regulatory clarity, and market readiness that rarely occurs simultaneously. The window to act strategically is narrowing.",
]
_CAT_CLOSINGS = {
    'AI News': 'Organisations that treat AI adoption as a strategic imperative rather than a tactical experiment will define the competitive landscape of the next decade.',
    'Cybersecurity Updates': 'In an environment of persistent, sophisticated threats, security posture is no longer an IT concern — it is a board-level business risk that demands continuous investment.',
    'Enterprise Tech': 'The enterprises that win in this environment will be those that align technology investment with measurable business outcomes, not those that simply accumulate tools.',
    'Mobile & Gadgets': 'Mobile hardware and software are converging faster than most roadmaps anticipated, creating new opportunities for developers and new expectations for consumers.',
    'EVs & Automotive': 'The EV transition is accelerating faster than legacy automakers planned for, and the supply chain, software, and infrastructure implications are still being absorbed.',
    'Startups & Business': 'Capital is flowing to founders who can demonstrate not just technical innovation but clear paths to defensible, scalable business models.',
    'Gaming': 'The gaming industry is rapidly becoming the most technically sophisticated consumer entertainment medium, with implications that extend far beyond entertainment.',
    'Consumer Tech': 'Consumer expectations are being reset by rapid hardware and software iteration, and the brands that fail to keep pace risk rapid commoditisation.',
    'Broadcast Tech': 'The broadcast technology sector is undergoing its most disruptive decade since the shift to digital, driven by IP infrastructure, AI, and streaming-first consumption.',
}
_DEFAULT_CLOSING = 'The pace of change in this sector demands continuous monitoring and proactive adaptation from every stakeholder.'

def _extract_topic(title: str) -> str:
    stop = {'the','a','an','of','in','on','at','to','for','with','by','as','is','are','was','were','has','have','had','will','would','could','should','that','this','these','those','and','or','but','not','from','into','over','after','before','about'}
    words = [w for w in re.sub(r'[^a-zA-Z0-9\s]', '', title).split() if w.lower() not in stop and len(w) > 3]
    return ' '.join(words[:4]) if words else 'technology'

def local_fallback_summary(title: str, category: str, seed: str) -> str:
    topic    = _extract_topic(title)
    hash_val = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    closing  = _CAT_CLOSINGS.get(category, _DEFAULT_CLOSING)
    frame    = _FRAMING[hash_val % len(_FRAMING)].format(topic=topic)
    return f"{frame} {closing}"


# ══════════════════════════════════════════════════════════════════════════════
# GROQ HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _url_key(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:16]

def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try: return json.loads(_read(CACHE_FILE))
        except Exception: pass
    return {}

def save_cache(cache: dict):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

def _is_cache_fresh(entry: dict) -> bool:
    try:
        cached_date = datetime.fromisoformat(entry.get('cached_on', '2000-01-01'))
        age = (datetime.now(timezone.utc) - cached_date.replace(tzinfo=timezone.utc)).days
        return age < CACHE_MAX_AGE_DAYS
    except Exception: return False

def _groq_post(system: str, user: str, max_tokens: int = 500) -> str | None:
    """Low-level Groq call with retry. Returns text or None."""
    if not GROQ_API_KEY: return None
    for attempt in range(1, 3):
        try:
            resp = requests.post(
                GROQ_URL,
                headers={'Authorization': f'Bearer {GROQ_API_KEY}', 'Content-Type': 'application/json'},
                json={'model': MODEL, 'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], 'max_tokens': max_tokens, 'temperature': 0.72},
                timeout=45,
            )
            resp.raise_for_status()
            return resp.json()['choices'][0]['message']['content'].strip()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429 and attempt == 1:
                print(f'    ⏳ Rate limit — waiting 20s…'); time.sleep(20)
            else:
                print(f'    ✗ HTTP {e.response.status_code}'); return None
        except Exception as ex:
            print(f'    ✗ Groq error: {ex}'); return None
    return None


# ══════════════════════════════════════════════════════════════════════════════
# V3 INTELLIGENCE REWRITE — 8-TASK GROQ PIPELINE
# Each article is transformed through:
#   Task 1: Category mapping + tech term extraction
#   Task 2: Technology intelligence brief (exec summary, key techs, trends)
#   Task 3: Full AdSense-approved editorial article (650–900w, E-E-A-T)
#   Task 4: SEO + high-CPC keyword pack
# ══════════════════════════════════════════════════════════════════════════════

_INTELLIGENCE_SYSTEM = """You are a senior technology intelligence analyst at The Tech Brief — a premium, AdSense-approved technology intelligence platform. You combine the expertise of a technology journalist, industry analyst, and SEO strategist.

GROQ OPTIMISATION RULES:
- Be concise but high-impact
- Maximise insight per token
- No fluff or repetition
- Expert analytical tone (like Gartner meets The Economist)
- Strong E-E-A-T signals
- No generic AI explanations
- Named technologies, attack models, frameworks
- Data points where relevant (realistic estimates)
- Return ONLY valid JSON — no markdown fences, no preamble"""

def intelligence_rewrite(title: str, category: str) -> dict | None:
    """
    V3 UPGRADE: Full intelligence pipeline.
    Returns a rich dict with exec_summary, key_techs, why_it_matters,
    trend_analysis, strategic_insights, editorial_body, seo_title,
    meta_description, and keywords.
    Falls back to basic rewrite if full pipeline fails.
    """
    user = f"""Topic: "{title}"
Category: {category}

Generate a Technology Intelligence Brief for The Tech Brief platform.
Return ONLY this JSON structure (no markdown, no fences):

{{
  "exec_summary": "3-4 line dense executive summary. Industry implications, not news recap.",
  "key_techs": [
    {{"name": "TechName", "definition": "1 line practical definition"}}
  ],
  "why_it_matters": "2-3 sentences on business impact, industry disruption, or security/competitive implications. Be specific.",
  "trend_outlook": "2 sentences: what's accelerating, what's real vs hype in 2025-2027.",
  "strategic_insight": "1-2 actionable sentences for organisations or professionals.",
  "editorial_body": "Write a 140-180 word original editorial paragraph for The Tech Brief's {category} section. Analytical tone. Include industry implications, broader tech context, one forward-looking sentence. No source names, no quotes.",
  "seo_title": "SEO-optimised article title (60 chars max, authority + CTR)",
  "meta_description": "Meta description 140-155 chars, includes primary keyword",
  "primary_keyword": "single most valuable keyword phrase (high CPC)",
  "secondary_keywords": ["keyword2", "keyword3", "keyword4"]
}}"""

    raw = _groq_post(_INTELLIGENCE_SYSTEM, user, max_tokens=800)
    if not raw: return None
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'\s*```$', '', raw.strip()).strip()
    try:
        data = json.loads(raw)
        required = {'exec_summary', 'why_it_matters', 'editorial_body'}
        if not required.issubset(data.keys()): return None
        return data
    except Exception:
        return None


def rewrite_via_groq(title: str, category: str) -> str | None:
    """
    V3: Try full intelligence pipeline first, fall back to simple rewrite.
    Returns the editorial_body paragraph for the card summary.
    """
    intel = intelligence_rewrite(title, category)
    if intel and intel.get('editorial_body'):
        text = intel['editorial_body'].strip().strip('"\'')
        return text if len(text) > 80 else None

    # Simple fallback rewrite
    system = ("You are a senior technology journalist at The Tech Brief. Write 100% original editorial content. "
              "Never copy, quote, or reference any source, publication, or website by name.")
    user = (f"Write an original 130–160 word editorial paragraph for The Tech Brief's {category} section.\n\n"
            f"Topic context (do NOT copy — use as subject inspiration only):\n\"{title}\"\n\n"
            "Requirements: original prose, industry implications, broader tech trend, no source names, no quotes, "
            "confident analytical tone. End with one forward-looking sentence.\n\nReturn ONLY the paragraph.")
    text = _groq_post(system, user, 400)
    if text:
        text = re.sub(r'^["\'\\s]+|["\'\\s]+$', '', text).strip()
        return text if len(text) > 80 else None
    return None


# ══════════════════════════════════════════════════════════════════════════════
# TRENDING ARTICLE GENERATOR (V3 — enhanced prompts)
# ══════════════════════════════════════════════════════════════════════════════

_TRENDING_FEEDS = [
    {'cat': 'AI News',             'slug': 'ai-news',              'url': 'https://techcrunch.com/tag/ai/feed/'},
    {'cat': 'Mobile & Gadgets',    'slug': 'mobile-gadgets',       'url': 'https://www.theverge.com/rss/gadgets/index.xml'},
    {'cat': 'Cybersecurity',       'slug': 'cybersecurity-updates','url': 'https://www.darkreading.com/rss.xml'},
    {'cat': 'Enterprise Tech',     'slug': 'enterprise-tech',      'url': 'https://venturebeat.com/category/enterprise/feed/'},
    {'cat': 'EVs & Automotive',    'slug': 'evs-automotive',       'url': 'https://electrek.co/feed/'},
    {'cat': 'Startups & Business', 'slug': 'startups-business',    'url': 'https://techcrunch.com/feed/'},
    {'cat': 'Gaming',              'slug': 'gaming',               'url': 'https://kotaku.com/rss'},
    {'cat': 'Consumer Tech',       'slug': 'consumer-tech',        'url': 'https://www.cnet.com/rss/all/'},
    {'cat': 'Broadcast Tech',      'slug': 'broadcast-tech',       'url': 'https://www.newscaststudio.com/feed/'},
]

_TREND_BADGE = {
    'ai-news':               ('AI',         '#7C3AED'),
    'cybersecurity-updates': ('Security',   '#DC2626'),
    'mobile-gadgets':        ('Gadgets',    '#0891B2'),
    'evs-automotive':        ('EVs',        '#059669'),
    'startups-business':     ('Business',   '#D97706'),
    'enterprise-tech':       ('Enterprise', '#1A56DB'),
    'gaming':                ('Gaming',     '#7C3AED'),
    'consumer-tech':         ('Tech',       '#0891B2'),
    'broadcast-tech':        ('Broadcast',  '#BE185D'),
}


def _groq_trending_article(title: str, category: str) -> dict | None:
    """V3: Generate a trending article with full intelligence structure."""
    system = ("You are a senior technology intelligence analyst at The Tech Brief. "
              "Write 100% original editorial content. Never copy or quote external sources. "
              "Return valid JSON only, no markdown fences, no preamble.")
    user = (
        f"Write an original 300-500 word technology intelligence article for The Tech Brief's trending section.\n\n"
        f"Topic inspiration (do NOT copy this headline, use as subject only):\n\"{title}\"\nCategory: {category}\n\n"
        "Apply the Technology Intelligence Brief format:\n"
        "- Executive insight, not news recap\n"
        "- Named technologies and frameworks\n"
        "- Business/industry implications\n"
        "- Expert analytical tone\n\n"
        "Return JSON with this exact structure:\n"
        "{\"headline\":\"compelling 8-12 word intelligence headline\","
        "\"intro\":\"2-sentence executive hook — industry implication first, then context\","
        "\"body\":\"3-4 paragraphs of original intelligence analysis (300+ words). "
        "Include: key technologies involved, why it matters for enterprises/consumers/developers, "
        "trend context. Separate paragraphs with \\n\\n. No subheadings, flowing expert prose only.\","
        "\"conclusion\":\"1-2 sentence strategic forward-looking close\","
        "\"summary\":\"25-word meta description with primary keyword\"}"
    )
    raw = _groq_post(system, user, max_tokens=1000)
    if not raw: return None
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'\s*```$', '', raw.strip()).strip()
    try:
        data = json.loads(raw)
        required = {'headline', 'intro', 'body', 'conclusion', 'summary'}
        if not required.issubset(data.keys()): return None
        return data
    except Exception: return None


def _local_trending_fallback(title: str, category: str, seed: str) -> dict:
    topic    = _extract_topic(title)
    hash_val = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    closing  = _CAT_CLOSINGS.get(category, _DEFAULT_CLOSING)
    paragraphs = [
        _FRAMING[hash_val % len(_FRAMING)].format(topic=topic),
        _FRAMING[(hash_val + 1) % len(_FRAMING)].format(topic=topic + ' developments'),
        _FRAMING[(hash_val + 2) % len(_FRAMING)].format(topic='this area of ' + category.lower()),
    ]
    body = '\n\n'.join(paragraphs)
    prefixes = ['What the Latest', 'Understanding', 'The Strategic Significance of', 'Why', 'The Rise of', 'Inside the']
    prefix = prefixes[hash_val % len(prefixes)]
    headline = f"{prefix} {category} Developments Signal a Major Shift"
    return {
        'headline':   headline,
        'intro':      paragraphs[0][:220],
        'body':       body,
        'conclusion': closing,
        'summary':    f"Original intelligence analysis of the latest {category} developments from The Tech Brief editorial team.",
    }


def build_trending():
    """Generate 6 trending articles every build run. Writes to docs/assets/data/."""
    print('  Building trending articles…')
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    stories = []
    for feed_cfg in _TRENDING_FEEDS:
        try:
            feed = feedparser.parse(feed_cfg['url'])
            for entry in feed.entries[:2]:
                t = (entry.get('title') or '').strip()
                l = (entry.get('link') or '').strip()
                if t and l and len(t) > 20:
                    ts = entry.get('published_parsed') or entry.get('updated_parsed')
                    stories.append({'title': t, 'link': l, 'cat': feed_cfg['cat'], 'slug': feed_cfg['slug'], 'ts': time.mktime(ts) if ts else 0})
        except Exception: pass

    stories.sort(key=lambda x: x['ts'], reverse=True)
    used_cats, selected = set(), []
    for s in stories:
        if s['slug'] not in used_cats and len(selected) < 6:
            selected.append(s); used_cats.add(s['slug'])
    for s in stories:
        if len(selected) >= 6: break
        if s not in selected: selected.append(s)

    output = []
    txt_lines = []

    for story in selected:
        seed  = _url_key(story['link'])
        badge, bcolor = _TREND_BADGE.get(story['slug'], ('Tech', '#1A56DB'))
        image = _pick_image(story['slug'], seed)

        if GROQ_API_KEY:
            print(f'    ✍  Trending: {story["title"][:55]}…')
            article = _groq_trending_article(story['title'], story['cat'])
            if not article: article = _local_trending_fallback(story['title'], story['cat'], seed)
        else:
            article = _local_trending_fallback(story['title'], story['cat'], seed)

        record = {
            'headline':    article['headline'],
            'intro':       article['intro'],
            'body':        article['body'],
            'conclusion':  article['conclusion'],
            'summary':     article['summary'],
            'category':    story['cat'],
            'cat_slug':    story['slug'],
            'cat_url':     f"{story['slug']}.html",
            'badge':       badge,
            'badge_color': bcolor,
            'image':       image,
            'date':        today,
        }
        output.append(record)
        txt_lines += [article['headline'], article['summary'], badge, 'The Tech Brief', f"{story['slug']}.html", '']

    data_dir = os.path.join(SITE_OUT, 'assets', 'data')
    os.makedirs(data_dir, exist_ok=True)
    json_path = os.path.join(data_dir, 'trending.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({'updated': today, 'stories': output}, f, indent=2, ensure_ascii=False)
    txt_path = os.path.join(data_dir, 'trending.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(txt_lines))
    site_data_dir = os.path.join(SITE_SRC, 'assets', 'data')
    os.makedirs(site_data_dir, exist_ok=True)
    import shutil
    shutil.copy2(json_path, os.path.join(site_data_dir, 'trending.json'))
    shutil.copy2(txt_path,  os.path.join(site_data_dir, 'trending.txt'))
    print(f'  ✓ trending.json + trending.txt written ({len(output)} stories)')


# ══════════════════════════════════════════════════════════════════════════════
# RSS HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def clean_text(html_str):
    txt = BeautifulSoup(html_str or '', 'html.parser').get_text(' ')
    return re.sub(r'\s+', ' ', txt).strip()

def _looks_like_image(url):
    if not url: return False
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

def load_editorial_articles() -> list:
    if not os.path.exists(GEN_FILE): return []
    try: return json.loads(_read(GEN_FILE))
    except Exception: return []


# ══════════════════════════════════════════════════════════════════════════════
# STATIC ASSET SYNC
# ══════════════════════════════════════════════════════════════════════════════

def sync_static_assets():
    import shutil
    for d in ['assets', 'legal', 'articles']:
        src = os.path.join(SITE_SRC, d)
        dst = os.path.join(SITE_OUT, d)
        if os.path.isdir(src):
            if os.path.exists(dst): shutil.rmtree(dst)
            shutil.copytree(src, dst)
    for fname in ['about.html', 'contact.html', 'how-to.html', 'robots.txt',
                  'sitemap.xml', 'template_category.html', 'template_home.html']:
        src = os.path.join(SITE_SRC, fname)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(SITE_OUT, fname))


# ══════════════════════════════════════════════════════════════════════════════
# V3 ARTICLE PAGE BUILDER — Rich Intelligence Format
# ══════════════════════════════════════════════════════════════════════════════

_BADGE_COLORS = {
    'ai-news':'#7C3AED','cybersecurity-updates':'#DC2626','mobile-gadgets':'#0891B2',
    'evs-automotive':'#059669','startups-business':'#D97706','enterprise-tech':'#1A56DB',
    'gaming':'#7C3AED','consumer-tech':'#0891B2','broadcast-tech':'#BE185D',
}
_CAT_ICONS = {
    'ai-news':'🤖','cybersecurity-updates':'🔐','mobile-gadgets':'📱',
    'evs-automotive':'🚗','startups-business':'💼','enterprise-tech':'🏢',
    'gaming':'🎮','consumer-tech':'🛒','broadcast-tech':'📡',
}


def build_internal_article_page(title, editorial_summary, category, cat_slug, cat_page, date_str, slug, intel_data=None):
    """
    V3: Builds a rich article page. If intel_data is present (from intelligence_rewrite),
    includes exec summary, key techs, why it matters, trend outlook, and strategic insights sections.
    """
    image_url    = _pick_image(cat_slug, slug)
    canon_url    = f'{SITE_URL}/articles/{slug}.html'
    badge_color  = _BADGE_COLORS.get(cat_slug, '#1A56DB')
    icon         = _CAT_ICONS.get(cat_slug, '📰')
    year         = datetime.now(timezone.utc).year
    try:    pub_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %d, %Y')
    except: pub_date = date_str
    safe_title   = title.replace('"','&quot;').replace('<','&lt;').replace('>','&gt;')
    safe_summary = editorial_summary.replace('<','&lt;').replace('>','&gt;')
    schema = json.dumps({
        "@context":"https://schema.org","@type":"Article","headline":title,
        "image":image_url,"datePublished":date_str,"dateModified":date_str,
        "author":{"@type":"Organization","name":"The Tech Brief Editorial Team"},
        "publisher":{"@type":"Organization","name":"The Tech Brief","url":SITE_URL},
        "mainEntityOfPage":canon_url,"articleSection":category
    }, indent=2)

    # Build optional intelligence sections from intel_data
    intel_sections = ''
    if intel_data:
        # Executive Summary callout
        exec_sum = (intel_data.get('exec_summary') or '').replace('<','&lt;').replace('>','&gt;')
        if exec_sum:
            intel_sections += f'''
    <div class="intel-callout" style="background:rgba(26,86,219,.05);border:1px solid rgba(26,86,219,.2);border-left:4px solid #1A56DB;border-radius:0 8px 8px 0;padding:18px 22px;margin:28px 0;">
      <div style="font-size:10px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:#1A56DB;font-family:var(--font-mono);margin-bottom:8px;">Executive Summary</div>
      <p style="font-size:15px;line-height:1.68;color:var(--ink);margin:0;font-weight:500;">{exec_sum}</p>
    </div>'''

        # Why It Matters
        why = (intel_data.get('why_it_matters') or '').replace('<','&lt;').replace('>','&gt;')
        if why:
            intel_sections += f'''
    <h2 style="font-family:var(--font-serif);font-size:22px;margin:32px 0 12px;color:var(--ink);">Why This Matters</h2>
    <p style="font-size:16px;line-height:1.75;color:var(--ink-2);">{why}</p>'''

        # Key Technologies
        key_techs = intel_data.get('key_techs') or []
        if key_techs:
            tech_items = ''.join([
                f'<li style="margin-bottom:10px;"><strong style="color:var(--ink);">{t.get("name","")}</strong> — <span style="color:var(--ink-2);">{t.get("definition","")}</span></li>'
                for t in key_techs if t.get('name')
            ])
            intel_sections += f'''
    <h2 style="font-family:var(--font-serif);font-size:22px;margin:32px 0 12px;color:var(--ink);">Key Technologies</h2>
    <ul style="list-style:none;padding:0;margin:0 0 24px;">{tech_items}</ul>'''

        # Trend Outlook
        trend = (intel_data.get('trend_outlook') or '').replace('<','&lt;').replace('>','&gt;')
        if trend:
            intel_sections += f'''
    <h2 style="font-family:var(--font-serif);font-size:22px;margin:32px 0 12px;color:var(--ink);">2025–2027 Trend Outlook</h2>
    <p style="font-size:16px;line-height:1.75;color:var(--ink-2);">{trend}</p>'''

        # Strategic Insight
        strategic = (intel_data.get('strategic_insight') or '').replace('<','&lt;').replace('>','&gt;')
        if strategic:
            intel_sections += f'''
    <div style="background:var(--surface-2);border-radius:8px;padding:18px 22px;margin:28px 0;">
      <div style="font-size:10px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:var(--ink-3);font-family:var(--font-mono);margin-bottom:8px;">Strategic Insight</div>
      <p style="font-size:15px;line-height:1.68;color:var(--ink);margin:0;font-style:italic;">{strategic}</p>
    </div>'''

    read_time = '4' if not intel_sections else '6'

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('consent','default',{{'analytics_storage':'denied','ad_storage':'denied','ad_user_data':'denied','ad_personalization':'denied','wait_for_update':500}});</script>
  <script async src="https://www.googletagmanager.com/gtag/js?id={GA_TAG}"></script>
  <script>gtag('js',new Date());gtag('config','{GA_TAG}');</script>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>{safe_title} | The Tech Brief</title>
  <meta name="description" content="{(intel_data or {}).get('meta_description') or safe_summary[:155]}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{canon_url}">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="The Tech Brief">
  <meta property="og:title" content="{safe_title}">
  <meta property="og:description" content="{safe_summary[:155]}">
  <meta property="og:url" content="{canon_url}">
  <meta property="og:image" content="{image_url}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{safe_title}">
  <meta name="twitter:image" content="{image_url}">
  <script type="application/ld+json">
{schema}
  </script>
  <link rel="icon" href="../assets/favicon.svg" type="image/svg+xml">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=IBM+Plex+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../assets/styles.css">
</head>
<body>
<a class="skip-link" href="#main-content">Skip to main content</a>

<header class="site-header" role="banner">
  <a href="../index.html" class="header-brand" aria-label="The Tech Brief — Home">
    <div class="brand-icon">TB</div>
    <div>
      <span class="brand-name">The Tech Brief</span>
      <span class="brand-tagline">Technology Intelligence</span>
    </div>
  </a>
  <button class="nav-toggle" aria-label="Toggle navigation" aria-controls="site-nav" aria-expanded="false">
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none"><rect y="4" width="22" height="2" rx="1" fill="currentColor"/><rect y="10" width="22" height="2" rx="1" fill="currentColor"/><rect y="16" width="22" height="2" rx="1" fill="currentColor"/></svg>
  </button>
  <nav id="site-nav" class="site-nav" role="navigation" aria-label="Primary navigation">
    <a href="../index.html">Home</a>
    <a href="../ai-news.html">AI</a>
    <a href="../enterprise-tech.html">Enterprise</a>
    <a href="../cybersecurity-updates.html">Cybersecurity</a>
    <a href="../mobile-gadgets.html">Mobile</a>
    <a href="../evs-automotive.html">EVs</a>
    <a href="../gaming.html">Gaming</a>
    <a href="../startups-business.html">Startups</a>
    <a href="../about.html" class="nav-cta">About</a>
  </nav>
</header>

<div class="article-hero">
  <div class="article-hero-inner">
    <p style="font-size:12px;color:rgba(255,255,255,.4);font-family:var(--font-mono);margin-bottom:10px;">
      <a href="../index.html" style="color:rgba(255,255,255,.4);">Home</a>
      &rsaquo; <a href="../{cat_page}" style="color:rgba(255,255,255,.5);">{category}</a>
      &rsaquo; <span style="color:rgba(255,255,255,.6);">Article</span>
    </p>
    <a href="../{cat_page}" class="article-cat-badge">{icon} {category}</a>
    <h1 class="article-hero h1" style="font-family:var(--font-serif);font-size:clamp(24px,4vw,40px);color:#fff;line-height:1.18;letter-spacing:-.4px;font-weight:900;">{safe_title}</h1>
    <div class="article-meta">
      <span>By <strong style="color:rgba(255,255,255,.7);">The Tech Brief Editorial Team</strong></span>
      <time datetime="{date_str}" style="color:rgba(255,255,255,.5);">{pub_date}</time>
      <span>{read_time} min read</span>
    </div>
  </div>
</div>

<main id="main-content">
  <div class="article-layout" style="padding:0 24px 60px;">
    <img src="{image_url}" alt="{safe_title}" style="width:100%;max-height:440px;object-fit:cover;border-radius:var(--radius);margin:32px 0;display:block;" loading="eager">

    <div class="article-body">
      <p style="font-size:18px;line-height:1.75;color:var(--ink-2);font-weight:300;margin-bottom:28px;">{safe_summary}</p>
      {intel_sections}
    </div>

    <div style="margin-top:32px;padding:14px 20px;background:var(--surface-2);border-radius:var(--radius);font-size:13px;color:var(--ink-3);">
      <strong style="color:var(--ink);">Editorial Note:</strong> This analysis is independently produced by The Tech Brief editorial team.
      <a href="../about.html" style="color:var(--accent);margin-left:4px;">About our editorial process →</a>
    </div>

    <div style="border-top:2px solid var(--border);margin-top:40px;padding-top:24px;">
      <h3 style="font-family:var(--font-serif);font-size:20px;margin-bottom:16px;">Continue Reading</h3>
      <div style="display:flex;flex-direction:column;gap:0;">
        <a href="../{cat_page}" style="display:block;padding:12px 0;border-bottom:1px solid var(--border);color:var(--accent);font-weight:600;font-size:15px;">{icon} More {category} coverage</a>
        <a href="../how-to.html" style="display:block;padding:12px 0;border-bottom:1px solid var(--border);color:var(--accent);font-weight:600;font-size:15px;">📖 How-To Guides & Tutorials</a>
        <a href="../index.html" style="display:block;padding:12px 0;color:var(--accent);font-weight:600;font-size:15px;">🏠 Back to Home</a>
      </div>
    </div>
  </div>
</main>

<footer class="site-footer" role="contentinfo">
  <div class="footer-inner">
    <div class="footer-about">
      <span class="brand-name">The Tech Brief</span>
      <p>Independent technology publication delivering original editorial analysis. Updated daily.</p>
    </div>
    <div class="footer-col">
      <h4>Categories</h4>
      <a href="../ai-news.html">AI News</a>
      <a href="../enterprise-tech.html">Enterprise Tech</a>
      <a href="../cybersecurity-updates.html">Cybersecurity</a>
      <a href="../mobile-gadgets.html">Mobile & Gadgets</a>
      <a href="../evs-automotive.html">EVs & Automotive</a>
      <a href="../gaming.html">Gaming</a>
      <a href="../startups-business.html">Startups & Business</a>
    </div>
    <div class="footer-col">
      <h4>Site Info</h4>
      <a href="../about.html">About</a>
      <a href="../contact.html">Contact</a>
      <a href="../legal/privacy.html">Privacy Policy</a>
      <a href="../legal/terms.html">Terms of Use</a>
      <a href="../legal/disclaimer.html">Disclaimer</a>
    </div>
  </div>
  <div class="footer-bottom">
    <span>&copy; {year} The Tech Brief — thetechbrief.net. All rights reserved.</span>
  </div>
</footer>

<div class="cookie-banner" id="cookieBanner" role="dialog" aria-label="Cookie consent">
  <p>We use cookies to improve experience. See our <a href="../legal/privacy.html">Privacy Policy</a>.</p>
  <div class="cookie-actions">
    <button class="btn primary" id="cookieAccept">Accept</button>
    <button class="btn secondary" id="cookieReject">Decline</button>
  </div>
</div>

<script>
(function(){{
  var t=document.querySelector('.nav-toggle'), n=document.getElementById('site-nav');
  if(!t||!n) return;
  t.addEventListener('click', function(){{ var o=n.classList.toggle('open'); t.setAttribute('aria-expanded',o); }});
}})();
(function(){{
  var c=localStorage.getItem('cookieConsent');
  if(c){{ document.getElementById('cookieBanner').remove(); return; }}
  document.getElementById('cookieAccept').onclick=function(){{
    localStorage.setItem('cookieConsent','yes');
    document.getElementById('cookieBanner').remove();
    gtag('consent','update',{{'analytics_storage':'granted','ad_storage':'granted','ad_user_data':'granted','ad_personalization':'granted'}});
  }};
  document.getElementById('cookieReject').onclick=function(){{
    localStorage.setItem('cookieConsent','no');
    document.getElementById('cookieBanner').remove();
  }};
}})();
</script>
</body>
</html>"""


# ══════════════════════════════════════════════════════════════════════════════
# CATEGORY PAGE BUILDER — V3: passes richer context to template
# ══════════════════════════════════════════════════════════════════════════════

def build_category(category: str, urls: list, editorial_articles: list, cache: dict, rewrites_done: list) -> list:
    raw_items = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:10]:
                title = (e.get('title') or '').strip()
                link  = (e.get('link') or '').strip()
                if not title or not link: continue
                raw_items.append({'title': title, 'link': link, 'image': first_image(e), 'ts': parse_time(e), 'date': fmt_date(parse_time(e))})
        except Exception as ex:
            print(f'    Feed error {url}: {ex}')

    raw_items.sort(key=lambda x: x['ts'], reverse=True)
    seen_links, deduped = set(), []
    for item in raw_items:
        if item['link'] not in seen_links:
            deduped.append(item); seen_links.add(item['link'])

    meta = dict(META_MAP.get(category, {'title': category, 'description': category, 'h1': category, 'h2': '', 'slug': _slugify(category)}))
    if 'slug' not in meta: meta['slug'] = _slugify(category)
    cat_slug = meta['slug']
    cat_page = f"{cat_slug}.html"
    os.makedirs(RSS_ARTICLES_OUT, exist_ok=True)

    cards = []
    for item in deduped:
        key    = _url_key(item['link'])
        cached = cache.get(key)
        intel_data = None

        if cached and _is_cache_fresh(cached):
            editorial_summary = cached['editorial_summary']
            slug = cached['slug']
            intel_data = cached.get('intel_data')
        elif rewrites_done[0] < MAX_REWRITES_PER_RUN and GROQ_API_KEY:
            print(f'    ✍  Intel [{rewrites_done[0]+1}]: {item["title"][:50]}…')
            # V3: try full intelligence pipeline
            intel_data = intelligence_rewrite(item['title'], category)
            if intel_data and intel_data.get('editorial_body'):
                summary = intel_data['editorial_body'].strip().strip('"\'')
            else:
                summary = rewrite_via_groq(item['title'], category)
            if not summary:
                summary = local_fallback_summary(item['title'], category, key)
                intel_data = None
            rewrites_done[0] += 1
            slug = f"rss-{key}"
            cache[key] = {
                'editorial_summary': summary, 'slug': slug,
                'title': item['title'], 'cat_slug': cat_slug,
                'category': category, 'intel_data': intel_data,
                'cached_on': datetime.now(timezone.utc).isoformat()
            }
            editorial_summary = summary
        elif cached:
            editorial_summary = cached['editorial_summary']
            slug = cached['slug']
            intel_data = cached.get('intel_data')
        else:
            slug = f"rss-{key}"
            editorial_summary = local_fallback_summary(item['title'], category, key)
            cache[key] = {
                'editorial_summary': editorial_summary, 'slug': slug,
                'title': item['title'], 'cat_slug': cat_slug,
                'category': category, 'intel_data': None,
                'cached_on': datetime.now(timezone.utc).isoformat()
            }

        image_url = safe_image(item.get('image'), cat_slug, slug)
        try:    iso_date = time.strftime('%Y-%m-%d', time.strptime(item['date'], '%B %d, %Y')) if item['date'] else today_str()
        except: iso_date = today_str()

        article_html = build_internal_article_page(
            item['title'], editorial_summary, category, cat_slug,
            cat_page, iso_date, slug, intel_data
        )
        with open(os.path.join(RSS_ARTICLES_OUT, f'{slug}.html'), 'w', encoding='utf-8') as f:
            f.write(article_html)

        cards.append({
            'title': item['title'],
            'summary': editorial_summary,
            'image': image_url,
            'internal_url': f'articles/{slug}.html',
            'ts': item['ts'],
            'date': item['date'],
            'pub_date': iso_date,
            'pub_date_fmt': item['date'],
            'url': f'articles/{slug}.html',
            'image_url': image_url,
            'category': category,
            'cat_slug': cat_slug,
            'read_time': f"{5 if intel_data else 4} min read",
        })

    cat_editorial = [a for a in editorial_articles if a.get('cat_slug') == cat_slug][:3]
    cat_icon = _CAT_ICONS.get(cat_slug, '📰')
    build_ts = datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC')

    html = CATEGORY_TPL.render(
        meta=meta,
        articles=cards,
        editorial_articles=cat_editorial,
        page_slug=cat_slug,
        category=category,
        cat_icon=cat_icon,
        article_count=len(cards),
        build_ts=build_ts,
    )
    with open(os.path.join(SITE_OUT, f'{cat_slug}.html'), 'w', encoding='utf-8') as f:
        f.write(html)

    tier = f"Intel({rewrites_done[0]})" if GROQ_API_KEY else "local-fallback"
    print(f'  ✓ {cat_slug}.html — {len(cards)} cards [{tier}], {len(cat_editorial)} deep-dives')
    return cards


# ══════════════════════════════════════════════════════════════════════════════
# HOMEPAGE — V3: injects per-category article slices
# ══════════════════════════════════════════════════════════════════════════════

def build_home(editorial_articles: list, all_category_cards: dict):
    meta = dict(META_MAP['Home'])
    build_ts = datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC')

    # Collect top 3 across all categories (sorted by timestamp)
    all_cards = []
    for cards in all_category_cards.values():
        all_cards.extend(cards)
    all_cards.sort(key=lambda x: x.get('ts', 0), reverse=True)

    html = HOME_TPL.render(
        meta=meta,
        articles=all_cards[:3],
        ai_articles=all_category_cards.get('AI News', [])[:3],
        cyber_articles=all_category_cards.get('Cybersecurity Updates', [])[:4],
        enterprise_articles=all_category_cards.get('Enterprise Tech', [])[:2],
        ev_articles=all_category_cards.get('EVs & Automotive', [])[:2],
        startup_articles=all_category_cards.get('Startups & Business', [])[:2],
        mobile_articles=all_category_cards.get('Mobile & Gadgets', [])[:2],
        gaming_articles=all_category_cards.get('Gaming', [])[:2],
        consumer_articles=all_category_cards.get('Consumer Tech', [])[:2],
        editorial_articles=editorial_articles[:9],
        build_ts=build_ts,
    )
    with open(os.path.join(SITE_OUT, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  ✓ index.html ({len(all_cards[:3])} lead articles, {len(editorial_articles[:9])} editorial)')


# ══════════════════════════════════════════════════════════════════════════════
# SITEMAP
# ══════════════════════════════════════════════════════════════════════════════

def build_sitemap(editorial_articles: list, rss_slugs: list):
    today = today_str()
    static = [
        ('','hourly','1.0'), ('ai-news.html','hourly','0.9'),
        ('broadcast-tech.html','hourly','0.9'), ('enterprise-tech.html','hourly','0.9'),
        ('cybersecurity-updates.html','hourly','0.9'), ('mobile-gadgets.html','hourly','0.9'),
        ('consumer-tech.html','hourly','0.9'), ('gaming.html','hourly','0.9'),
        ('evs-automotive.html','hourly','0.9'), ('startups-business.html','hourly','0.9'),
        ('how-to.html','monthly','0.9'), ('about.html','monthly','0.8'),
        ('contact.html','monthly','0.7'), ('legal/privacy.html','yearly','0.5'),
        ('legal/terms.html','yearly','0.5'), ('legal/disclaimer.html','yearly','0.4'),
        ('legal/copyright.html','yearly','0.4'), ('legal/affiliate.html','yearly','0.4'),
    ]
    fixed = [
        ('articles/ai-agents-enterprise-2025.html','2025-02-01'),
        ('articles/android-vs-iphone-2025.html','2025-02-15'),
        ('articles/ransomware-playbook-2025.html','2025-02-10'),
        ('articles/how-to-factory-reset-android.html','2025-03-01'),
        ('articles/how-to-factory-reset-iphone.html','2025-03-01'),
        ('articles/how-to-upgrade-windows.html','2025-03-01'),
    ]

    def u(loc, lastmod, freq, pri):
        return f'  <url>\n    <loc>{loc}</loc>\n    <lastmod>{lastmod}</lastmod>\n    <changefreq>{freq}</changefreq>\n    <priority>{pri}</priority>\n  </url>'

    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">', '']
    for path, freq, pri in static:
        lines.append(u(f'{SITE_URL}/{path}' if path else f'{SITE_URL}/', today, freq, pri))
    lines.append('')
    for path, lastmod in fixed:
        lines.append(u(f'{SITE_URL}/{path}', lastmod, 'monthly', '0.8'))
    if editorial_articles:
        lines.append('')
        for a in editorial_articles:
            lines.append(u(f'{SITE_URL}/{a["url"]}', a.get("date", today), 'monthly', '0.78'))
    if rss_slugs:
        lines.append('')
        for slug in rss_slugs:
            lines.append(u(f'{SITE_URL}/articles/{slug}.html', today, 'monthly', '0.65'))
    lines += ['', '</urlset>']
    with open(os.path.join(SITE_OUT, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    robots = f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n"
    for p in [os.path.join(SITE_OUT, 'robots.txt'), os.path.join(SITE_SRC, 'robots.txt')]:
        with open(p, 'w', encoding='utf-8') as f: f.write(robots)
    print(f'  ✓ sitemap.xml ({len(static)+len(fixed)+len(editorial_articles)+len(rss_slugs)} URLs)')


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    os.makedirs(SITE_OUT, exist_ok=True)
    os.makedirs(RSS_ARTICLES_OUT, exist_ok=True)

    editorial_articles = load_editorial_articles()
    print(f'Loaded {len(editorial_articles)} editorial articles')
    print(f'Groq: {"ENABLED — V3 Intelligence Pipeline" if GROQ_API_KEY else "DISABLED — local fallbacks active (never blank)"}')

    cache         = load_cache()
    rewrites_done = [0]

    print('Syncing static assets…')
    sync_static_assets()
    os.makedirs(RSS_ARTICLES_OUT, exist_ok=True)

    print('Building trending section…')
    build_trending()

    print(f'Building {len(FEEDS)} category pages…')
    all_category_cards = {}
    for cat, urls in FEEDS.items():
        print(f'  [{cat}]')
        cards = build_category(cat, urls, editorial_articles, cache, rewrites_done)
        all_category_cards[cat] = cards

    rss_slugs = [
        os.path.splitext(f)[0]
        for f in os.listdir(RSS_ARTICLES_OUT)
        if f.startswith('rss-') and f.endswith('.html')
    ] if os.path.isdir(RSS_ARTICLES_OUT) else []

    print('Building homepage…')
    build_home(editorial_articles, all_category_cards)

    print('Building sitemap…')
    build_sitemap(editorial_articles, rss_slugs)

    print(f'Saving cache ({len(cache)} entries)…')
    save_cache(cache)

    print(f'\n✅ V3 Build complete')
    print(f'   Intelligence rewrites : {rewrites_done[0]}')
    print(f'   Cache entries         : {len(cache)}')
    print(f'   Article pages         : {len(rss_slugs)}')
    print(f'   Editorial articles    : {len(editorial_articles)}')
    print(f'   Category pages        : {len(FEEDS)}')


if __name__ == '__main__':
    main()
