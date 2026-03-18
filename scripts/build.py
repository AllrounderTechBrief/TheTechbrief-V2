"""
Build script for The Tech Brief — AdSense-ready, never-blank edition.
════════════════════════════════════════════════════════════════════════

FIXES IN THIS VERSION:
  FIX 1 — 404 on "Read more"
    Old: RSS articles written to site/articles/ AFTER sync already ran
    New: RSS articles written directly to docs/articles/ (no sync dependency)

  FIX 2 — Trending section empty
    Old: trending.txt was 0 bytes; generate_articles.py hadn't run
    New: build_trending() generates 6 live trending articles every build
         using Groq (300-500w each) or local fallback. Saves trending.json
         + trending.txt directly to docs/assets/data/ so they're always live.

  FIX 3 — Irrelevant card images
    New: 12 curated, visually specific Unsplash IDs per category.
         Images are relevant to the actual topic (server racks for enterprise,
         phone close-ups for mobile, car charging for EVs, etc.)

  CORE — Never-blank pages
    3-tier fallback: Groq rewrite → stale cache → local editorial template
"""

import os, json, re, time, hashlib, requests
import feedparser
from bs4 import BeautifulSoup
from slugify import slugify as _slugify
from jinja2 import Template
from datetime import datetime, timezone

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT       = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_FILE  = os.path.join(ROOT, 'data', 'feeds.json')
META_FILE  = os.path.join(ROOT, 'data', 'meta.json')
CACHE_FILE = os.path.join(ROOT, 'data', 'article_cache.json')
GEN_FILE   = os.path.join(ROOT, 'data', 'generated_articles.json')
SITE_SRC   = os.path.join(ROOT, 'site')       # source templates/static
SITE_OUT   = os.path.join(ROOT, 'docs')       # GitHub Pages output
SITE_URL   = 'https://www.thetechbrief.net'
GA_TAG     = 'G-YCJEGDPW7G'

# FIX 1: Write RSS articles directly to docs/articles/ — NOT site/articles/
# This bypasses the sync timing issue entirely.
RSS_ARTICLES_OUT = os.path.join(SITE_OUT, 'articles')

# ── Groq config ───────────────────────────────────────────────────────────────
GROQ_API_KEY         = os.environ.get('GROQ_API_KEY', '')
GROQ_URL             = 'https://api.groq.com/openai/v1/chat/completions'
MODEL                = 'llama3-70b-8192'
MAX_REWRITES_PER_RUN = 40
CACHE_MAX_AGE_DAYS   = 60

# ── Load templates & data ─────────────────────────────────────────────────────
def _read(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

CATEGORY_TPL = Template(_read(os.path.join(ROOT, 'site', 'template_category.html')))
HOME_TPL     = Template(_read(os.path.join(ROOT, 'site', 'template_home.html')))
FEEDS        = json.loads(_read(DATA_FILE))
META_MAP     = json.loads(_read(META_FILE))


# ══════════════════════════════════════════════════════════════════════════════
# FIX 3: CURATED IMAGE POOLS (12 specific, visually relevant IDs per category)
# All photos are free under the Unsplash licence: unsplash.com/license
# ══════════════════════════════════════════════════════════════════════════════

_IMAGE_POOLS = {
    # AI: neural networks, glowing chips, digital brain, robots, data visualisations
    'ai-news': [
        'photo-1677442135703-1787eea5ce01',  # glowing neural network purple
        'photo-1620712943543-bcc4688e7485',  # humanoid robot face
        'photo-1655635643532-fa9ba2648cbe',  # AI chip close-up blue
        'photo-1633356122544-f134324a6cee',  # robot hand and human hand
        'photo-1591453089816-0fbb971b454c',  # data center blue glow
        'photo-1526374965328-7f61d4dc18c5',  # matrix code green
        'photo-1531297484001-80022131f5a1',  # laptop with code dark
        'photo-1451187580459-43490279c0fa',  # earth seen from space (tech context)
        'photo-1504639725590-34d0984388bd',  # code on screen
        'photo-1560472354-b33ff0c44a43',     # server row blue light
        'photo-1518770660439-4636190af475',  # circuit board macro
        'photo-1635070041078-e363dbe005cb',  # digital brain illustration
    ],
    # Enterprise: server rooms, office infrastructure, cloud, data centres, meetings
    'enterprise-tech': [
        'photo-1558494949-ef010cbdcc31',     # server rack blue LEDs
        'photo-1544197150-b99a580bb7a8',     # dark server room corridor
        'photo-1560472354-b33ff0c44a43',     # server row lit up
        'photo-1497366216548-37526070297c',  # modern open-plan office
        'photo-1486312338219-ce68d2c6f44d',  # person on MacBook Pro
        'photo-1542744094-3a31f272c490',     # laptop business graphs
        'photo-1521737711867-e3b97375f902',  # team around table laptop
        'photo-1454165804606-c3d57bc86b40',  # business graphs & analytics
        'photo-1461749280684-dccba630e2f6',  # code IDE screen
        'photo-1600880292203-757bb62b4baf',  # remote work setup home office
        'photo-1553877522-43269d4ea984',     # abstract office architecture
        'photo-1568952433726-3896e3881c65',  # business team meeting
    ],
    # Cybersecurity: padlocks, code, dark screens, shields, encrypted data
    'cybersecurity-updates': [
        'photo-1550751827-4bd374c3f58b',     # blue security shield digital
        'photo-1563986768609-322da13575f3',  # padlock on keyboard
        'photo-1614064641938-3bbee52942c7',  # hacker dark hoodie screen
        'photo-1510511233900-1982d92bd835',  # code lock green
        'photo-1555949963-aa79dcee981c',     # server lock security
        'photo-1573164713988-8665fc963095',  # dark screen hacker
        'photo-1516321318423-f06f85e504b3',  # network globe connections
        'photo-1504384308090-c894fdcc538d',  # dark cyber abstract blue
        'photo-1591696205602-2f950c417cb9',  # circuit security
        'photo-1569396116180-210c182bedb8',  # locked server room
        'photo-1603808033192-082d6919d3e1',  # encrypted code
        'photo-1662026911591-335639b11db6',  # cybersecurity lock concept
    ],
    # Mobile: phones in hand, phone flat-lay, earbuds, smartwatch, unboxing
    'mobile-gadgets': [
        'photo-1511707171634-5f897ff02aa9',  # iPhone on desk angled
        'photo-1592750475338-74b7b21085ab',  # white iPhone close-up
        'photo-1601784551446-20c9e07cdbdb',  # white AirPods case open
        'photo-1583394838336-acd977736f90',  # black headphones desk
        'photo-1523206489230-c012c64b2b48',  # phone held in hand
        'photo-1567581935884-3349723552ca',  # smartwatch on wrist
        'photo-1565849904461-04a58ad377e0',  # phone unboxing
        'photo-1616348436168-de43ad0db179',  # close-up phone screen
        'photo-1585060544812-6b45742d762f',  # gadgets flat-lay table
        'photo-1570891836654-d4590d13d073',  # tablet and phone together
        'photo-1542751371-adc38448a05e',     # various devices spread
        'photo-1512941937669-90a1b58e7e9c',  # colorful phone cases
    ],
    # Consumer Tech: laptops, smart speakers, home tech, keyboards, monitors
    'consumer-tech': [
        'photo-1593642632559-0c6d3fc62b89',  # silver laptop open
        'photo-1517694712202-14dd9538aa97',  # MacBook keyboard close-up
        'photo-1496181133206-80ce9b88a853',  # laptop open on desk
        'photo-1547658719-da2b51169166',     # smart speaker Alexa-style
        'photo-1550009158-9ebf69173e03',     # mechanical keyboard RGB
        'photo-1484788984921-03950022c9ef',  # home tech setup aesthetic
        'photo-1587829741301-dc798b83add3',  # PC desktop setup RGB
        'photo-1519389950473-47ba0277781c',  # tech workspace multiple screens
        'photo-1560472355-536de3962603',     # tech lifestyle coffee laptop
        'photo-1468495244123-6c6c332eeece',  # headphones music listen
        'photo-1498049794561-7780e7231661',  # tech products spread
        'photo-1504707748692-419802cf939d',  # consumer electronics store
    ],
    # Broadcast: TV cameras, studio, audio mixer, streaming setup, podcast mic
    'broadcast-tech': [
        'photo-1598488035139-bdbb2231ce04',  # audio mixer studio
        'photo-1567095761054-7003afd47020',  # podcast mic close-up
        'photo-1478737270239-2f02b77fc618',  # radio broadcast desk
        'photo-1574717024653-61fd2cf4d44d',  # professional video camera
        'photo-1590602847861-f357a9332bbc',  # camera lens close-up
        'photo-1516321497487-e288fb19713f',  # TV production studio
        'photo-1612420696760-0a0f34d3e7d0',  # broadcasting equipment
        'photo-1611532736597-de2d4265fba3',  # live streaming setup
        'photo-1540575467063-178a50c2df87',  # event live broadcast
        'photo-1492619375914-88005aa9e8fb',  # film camera professional
        'photo-1623039405147-547794f92e9e',  # media production team
        'photo-1478737270239-2f02b77fc618',  # radio studio desk repeat
    ],
    # Gaming: gaming setup, controllers, RGB monitor, console, esports arena
    'gaming': [
        'photo-1552820728-8b83bb6b773f',     # gaming setup RGB monitors
        'photo-1538481199705-c710c4e965fc',  # gaming monitor glow
        'photo-1493711662062-fa541adb3fc8',  # gaming controller close-up
        'photo-1574375927938-d5a98e8ffe85',  # PS5 DualSense controller
        'photo-1580327344181-c1163234e5a0',  # gaming headset mic
        'photo-1601887389937-0b02f7683064',  # PC gaming rig RGB
        'photo-1612287230202-1ff1d85d1bdf',  # Nintendo Switch handheld
        'photo-1511512578047-dfb367046420',  # FPS game on screen
        'photo-1560419015-7c427e8ae5ba',     # joystick controller retro
        'photo-1606144042614-b2417e99c4e3',  # neon arcade cabinet
        'photo-1586182987320-4f376d39d787',  # esports arena audience
        'photo-1569429593410-b498b3fb3387',  # retro gaming cartridges
    ],
    # EVs: electric car charging, Tesla side, car cockpit, charging station
    'evs-automotive': [
        'photo-1593941707882-a5bba14938c7',  # EV charging plug in car
        'photo-1558618666-fcd25c85cd64',     # sleek Tesla side view
        'photo-1617469767053-d3b523a0b982',  # charging station street
        'photo-1616455579100-2ceaa4eb2d37',  # electric car interior cockpit
        'photo-1549317661-bd32c8ce0db2',     # car dashboard screen
        'photo-1580274455191-1c62238fa1f4',  # white EV front
        'photo-1590362891991-f776e747a588',  # car on highway dusk
        'photo-1502161254119-e1f02c5b5e4b',  # car headlights night
        'photo-1568605117036-5fe5e7bab0b7',  # luxury car front angle
        'photo-1606016159991-dfe4f2746ad5',  # automotive tech interior
        'photo-1571987502227-9231b837d92a',  # electric motor cutaway
        'photo-1583121274602-3e2820c69888',  # sports car dramatic
    ],
    # Startups: co-working, whiteboard, pitch meeting, handshake, team
    'startups-business': [
        'photo-1559136555-9303baea8ebd',     # startup open-plan office
        'photo-1579532537598-459ecdaf39cc',  # pitch meeting boardroom
        'photo-1450101499163-c8848c66ca85',  # contract signing deal
        'photo-1553484771-371a605b060b',     # fintech phone graphs
        'photo-1537511446984-935f663eb1f4',  # co-working café laptop
        'photo-1486406146926-c627a92ad1ab',  # corporate glass building
        'photo-1573164713714-d95e436ab8d6',  # handshake business deal
        'photo-1521737604893-d14cc237f11d',  # startup team huddle
        'photo-1444653389962-8149286c578a',  # strategy planning map
        'photo-1460925895917-afdab827c52f',  # laptop analytics graphs
        'photo-1507003211169-0a1dd7228f2d',  # professional portrait desk
        'photo-1600880292203-757bb62b4baf',  # team meeting remote
    ],
}


def _pick_image(cat_slug: str, seed: str) -> str:
    pool = _IMAGE_POOLS.get(cat_slug, _IMAGE_POOLS['ai-news'])
    idx  = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(pool)
    return f'https://images.unsplash.com/{pool[idx]}?w=900&auto=format&fit=crop&q=80'


# ══════════════════════════════════════════════════════════════════════════════
# LOCAL FALLBACK SUMMARIES (Tier 3 — no API needed, never blank)
# ══════════════════════════════════════════════════════════════════════════════

_FRAMING = [
    "The technology sector is witnessing significant movement around {topic}. This shift carries meaningful implications for professionals, enterprises, and everyday users navigating a rapidly evolving digital environment. Understanding what drives this development — and the forces likely to shape its trajectory — helps businesses and individuals make more informed decisions about the platforms and tools they rely on. The pace of change in this area shows no signs of slowing, and the decisions being made now will set important precedents for the years ahead.",
    "Few technology developments have drawn as much attention recently as {topic}. Analysts and practitioners are closely tracking the implications, which span strategy, infrastructure, and user experience in equal measure. The broader context — competitive pressures, shifting regulatory frameworks, and evolving consumer expectations — shapes how this will unfold in practice. Organisations that stay informed and move with agility will be best positioned to turn this moment into a genuine advantage.",
    "The story of {topic} reflects a recurring pattern in modern technology: rapid change driven by competitive pressure and the relentless push for better performance. Those closest to the industry are watching closely, as the decisions being made now could define market dynamics for years ahead. The implications extend across multiple dimensions — from how organisations manage their infrastructure to how end users experience the products and services they depend on daily.",
    "Technology rarely moves in isolation, and {topic} is no exception. It connects to broader trends around digital transformation, platform consolidation, and the growing demand for smarter, more connected experiences. For businesses weighing their next strategic move and consumers evaluating their options, this moment offers both clarity and important new questions worth exploring carefully. The decisions taken in response will have lasting effects on the organisations and markets involved.",
    "A clearer picture is emerging around {topic}, and it points to meaningful change ahead for the sector. Industry observers are paying close attention to how key players respond, given the competitive and commercial stakes involved. What makes this development particularly notable is its potential to shift established assumptions about performance, cost, and user value in ways that go beyond incremental improvement.",
]
_CAT_CLOSINGS = {
    'AI News': "Artificial intelligence continues to reshape how software is built, deployed, and experienced — making each new development an important reference point for the year ahead.",
    'Cybersecurity Updates': "Maintaining awareness of developments in cybersecurity is essential for any organisation operating in today's threat environment, where the cost of being caught unprepared continues to rise.",
    'Mobile & Gadgets': "Consumer expectations for mobile and personal technology continue to rise, and the industry is responding with products and experiences of increasing sophistication.",
    'Enterprise Tech': "Enterprise technology decisions are rarely reversible in the short term, making it all the more important for organisations to stay informed about the directions the market is taking.",
    'EVs & Automotive': "The electric vehicle revolution is accelerating on multiple fronts simultaneously, and the decisions being made today will shape mobility for the next decade.",
    'Gaming': "The gaming industry sits at the intersection of technology, culture, and commerce — making each significant development a signal worth reading carefully.",
    'Consumer Tech': "Consumer technology choices increasingly involve complex trade-offs between capability, value, and ecosystem compatibility — and the market is responding with more options than ever before.",
    'Broadcast Tech': "Broadcast and media technology is undergoing profound structural change, driven by IP workflow migration, cloud adoption, and rapidly shifting viewer behaviour.",
    'Startups & Business': "The startup and investment landscape remains dynamic and selective, reflecting continued confidence in technology as a driver of value alongside disciplined capital allocation.",
}
_DEFAULT_CLOSING = "Technology continues to evolve at a pace that rewards informed decision-making — staying current remains one of the most valuable competitive advantages available."


def _extract_topic(title: str) -> str:
    t = re.sub(r'^(BREAKING|EXCLUSIVE|REVIEW|UPDATE|WATCH|NEW|REVEALED?)[\s:–\-]+', '', title, flags=re.IGNORECASE)
    t = t.rstrip('.,;:!?').strip()
    return (t[:82].rsplit(' ', 1)[0] + '…' if len(t) > 85 else t).lower() or 'this area of technology'


def local_fallback_summary(title: str, category: str, seed: str) -> str:
    topic    = _extract_topic(title)
    idx      = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(_FRAMING)
    framing  = _FRAMING[idx].format(topic=topic)
    closing  = _CAT_CLOSINGS.get(category, _DEFAULT_CLOSING)
    return f"{framing} {closing}"


# ══════════════════════════════════════════════════════════════════════════════
# GROQ HELPERS
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
    try:
        cached_date = datetime.fromisoformat(entry.get('cached_on', '2000-01-01'))
        age = (datetime.now(timezone.utc) - cached_date.replace(tzinfo=timezone.utc)).days
        return age < CACHE_MAX_AGE_DAYS
    except Exception:
        return False


def _groq_post(system: str, user: str, max_tokens: int = 350) -> str | None:
    """Low-level Groq call with retry. Returns text or None."""
    if not GROQ_API_KEY:
        return None
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


def rewrite_via_groq(title: str, category: str) -> str | None:
    system = ("You are a senior technology journalist at The Tech Brief. Write 100% original editorial content. "
              "Never copy, quote, or reference any source, publication, or website by name.")
    user = (f"Write an original 130–160 word editorial paragraph for The Tech Brief's {category} section.\n\n"
            f"Topic context (do NOT copy — use as subject inspiration only):\n\"{title}\"\n\n"
            "Requirements: original prose, industry implications, broader tech trend, no source names, no quotes, "
            "confident analytical tone. End with one forward-looking sentence.\n\nReturn ONLY the paragraph.")
    text = _groq_post(system, user, 350)
    if text:
        text = re.sub(r'^["\'\s]+|["\'\s]+$', '', text).strip()
        return text if len(text) > 80 else None
    return None


# ══════════════════════════════════════════════════════════════════════════════
# FIX 2: TRENDING ARTICLE GENERATOR
# Runs during every build. Fetches top RSS stories, rewrites each to 300-500w
# via Groq (or uses local fallback). Saves trending.json + trending.txt to
# docs/assets/data/ so the trending section always shows real content.
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
    'ai-news': ('AI',        '#7C3AED'),
    'cybersecurity-updates': ('Security', '#DC2626'),
    'mobile-gadgets':        ('Gadgets',  '#0891B2'),
    'evs-automotive':        ('EVs',      '#059669'),
    'startups-business':     ('Business', '#D97706'),
    'enterprise-tech':       ('Enterprise','#2563EB'),
    'gaming':                ('Gaming',   '#7C3AED'),
    'consumer-tech':         ('Tech',     '#0891B2'),
    'broadcast-tech':        ('Broadcast','#BE185D'),
}


def _groq_trending_article(title: str, category: str) -> dict | None:
    """Generate a 300-500w trending article via Groq. Returns dict or None."""
    system = ("You are a senior technology journalist at The Tech Brief. Write 100% original editorial content. "
              "Never copy, quote, or reference any external source. Return valid JSON only, no markdown fences.")
    user = (
        f"Write an original 300-500 word technology article for The Tech Brief's trending section.\n\n"
        f"Topic inspiration (do NOT copy this headline):\n\"{title}\"\nCategory: {category}\n\n"
        "Return JSON with this exact structure:\n"
        "{\"headline\":\"compelling 8-12 word title\","
        "\"intro\":\"2-sentence hook paragraph\","
        "\"body\":\"3-4 paragraphs of original analysis (300+ words total). "
        "Separate paragraphs with \\n\\n. No subheadings, flowing prose only.\","
        "\"conclusion\":\"1-2 sentence forward-looking close\","
        "\"summary\":\"25-word meta description\"}"
    )
    raw = _groq_post(system, user, max_tokens=900)
    if not raw:
        return None
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'\s*```$', '', raw.strip()).strip()
    try:
        data = json.loads(raw)
        required = {'headline', 'intro', 'body', 'conclusion', 'summary'}
        if not required.issubset(data.keys()):
            return None
        return data
    except Exception:
        return None


def _local_trending_fallback(title: str, category: str, seed: str) -> dict:
    """Generate a full trending article without Groq using local templates."""
    topic    = _extract_topic(title)
    hash_val = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    closing  = _CAT_CLOSINGS.get(category, _DEFAULT_CLOSING)

    paragraphs = [
        _FRAMING[hash_val % len(_FRAMING)].format(topic=topic),
        _FRAMING[(hash_val + 1) % len(_FRAMING)].format(topic=topic + ' developments'),
        _FRAMING[(hash_val + 2) % len(_FRAMING)].format(topic='this area of ' + category.lower()),
    ]
    body = '\n\n'.join(paragraphs)

    # Manufacture a plausible editorial headline
    prefixes = ['What the Latest', 'Understanding the', 'The Significance of', 'How', 'Why', 'The Rise of']
    prefix   = prefixes[hash_val % len(prefixes)]
    headline = f"{prefix} {category} Developments Matter Right Now"

    return {
        'headline':   headline,
        'intro':      paragraphs[0][:220],
        'body':       body,
        'conclusion': closing,
        'summary':    f"Original analysis of the latest {category} developments from The Tech Brief editorial team.",
    }


def build_trending():
    """
    FIX 2: Generate 6 trending articles every build run.
    Writes directly to docs/assets/data/trending.json + trending.txt.
    The trending widget reads trending.json first, then falls back to trending.txt.
    """
    print('  Building trending articles…')
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    # Fetch candidate stories
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
        except Exception:
            pass

    stories.sort(key=lambda x: x['ts'], reverse=True)
    # One per category, max 6
    used_cats, selected = set(), []
    for s in stories:
        if s['slug'] not in used_cats and len(selected) < 6:
            selected.append(s); used_cats.add(s['slug'])
    # Fill if < 6
    for s in stories:
        if len(selected) >= 6: break
        if s not in selected: selected.append(s)

    output = []
    txt_lines = []

    for story in selected:
        seed  = _url_key(story['link'])
        badge, bcolor = _TREND_BADGE.get(story['slug'], ('Tech', '#2563EB'))
        image = _pick_image(story['slug'], seed)

        if GROQ_API_KEY:
            print(f'    ✍  Trending: {story["title"][:55]}…')
            article = _groq_trending_article(story['title'], story['cat'])
            if not article:
                article = _local_trending_fallback(story['title'], story['cat'], seed)
        else:
            article = _local_trending_fallback(story['title'], story['cat'], seed)

        record = {
            'headline':   article['headline'],
            'intro':      article['intro'],
            'body':       article['body'],
            'conclusion': article['conclusion'],
            'summary':    article['summary'],
            'category':   story['cat'],
            'cat_slug':   story['slug'],
            'cat_url':    f"{story['slug']}.html",
            'badge':      badge,
            'badge_color': bcolor,
            'image':      image,
            'date':       today,
        }
        output.append(record)

        # Also build trending.txt entry (5-line format for JS fallback)
        txt_lines += [
            article['headline'],
            article['summary'],
            badge,
            'The Tech Brief',
            f"{story['slug']}.html",
            '',
        ]

    # Write trending.json
    data_dir = os.path.join(SITE_OUT, 'assets', 'data')
    os.makedirs(data_dir, exist_ok=True)

    json_path = os.path.join(data_dir, 'trending.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({'updated': today, 'stories': output}, f, indent=2, ensure_ascii=False)

    # Write trending.txt (fallback)
    txt_path = os.path.join(data_dir, 'trending.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(txt_lines))

    # Also keep site/ copies in sync
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
    # Copy asset dirs: assets, legal, articles (static evergreen only)
    for d in ['assets', 'legal', 'articles']:
        src = os.path.join(SITE_SRC, d)
        dst = os.path.join(SITE_OUT, d)
        if os.path.isdir(src):
            if os.path.exists(dst): shutil.rmtree(dst)
            shutil.copytree(src, dst)
    # Copy static HTML pages
    for fname in ['about.html', 'contact.html', 'how-to.html', 'robots.txt',
                  'sitemap.xml', 'template_category.html', 'template_home.html']:
        src = os.path.join(SITE_SRC, fname)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(SITE_OUT, fname))


# ══════════════════════════════════════════════════════════════════════════════
# INTERNAL ARTICLE PAGE BUILDER
# ══════════════════════════════════════════════════════════════════════════════

_BADGE_COLORS = {'ai-news':'#7C3AED','cybersecurity-updates':'#DC2626','mobile-gadgets':'#0891B2','evs-automotive':'#059669','startups-business':'#D97706','enterprise-tech':'#2563EB','gaming':'#7C3AED','consumer-tech':'#0891B2','broadcast-tech':'#BE185D'}
_CAT_ICONS    = {'ai-news':'🤖','cybersecurity-updates':'🔐','mobile-gadgets':'📱','evs-automotive':'🚗','startups-business':'💼','enterprise-tech':'🏢','gaming':'🎮','consumer-tech':'🛒','broadcast-tech':'📡'}


def build_internal_article_page(title, editorial_summary, category, cat_slug, cat_page, date_str, slug):
    image_url   = _pick_image(cat_slug, slug)
    canon_url   = f'{SITE_URL}/articles/{slug}.html'
    badge_color = _BADGE_COLORS.get(cat_slug, '#2563EB')
    icon        = _CAT_ICONS.get(cat_slug, '📰')
    year        = datetime.now(timezone.utc).year
    try:    pub_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %d, %Y')
    except: pub_date = date_str
    safe_title   = title.replace('"','&quot;').replace('<','&lt;').replace('>','&gt;')
    safe_summary = editorial_summary.replace('<','&lt;').replace('>','&gt;')
    schema = json.dumps({"@context":"https://schema.org","@type":"Article","headline":title,"image":image_url,"datePublished":date_str,"dateModified":date_str,"author":{"@type":"Organization","name":"The Tech Brief Editorial Team"},"publisher":{"@type":"Organization","name":"The Tech Brief","url":SITE_URL},"mainEntityOfPage":canon_url,"articleSection":category},indent=2)

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
  <meta name="description" content="{safe_summary[:155]}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{canon_url}">
  <meta property="og:type" content="article"><meta property="og:site_name" content="The Tech Brief">
  <meta property="og:title" content="{safe_title}"><meta property="og:description" content="{safe_summary[:155]}">
  <meta property="og:url" content="{canon_url}"><meta property="og:image" content="{image_url}">
  <meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{safe_title}"><meta name="twitter:image" content="{image_url}">
  <script type="application/ld+json">
{schema}
  </script>
  <link rel="icon" href="../assets/favicon.svg" type="image/svg+xml">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,500;0,9..40,700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../assets/styles.css">
  <style>
    .art-img{{width:100%;max-height:420px;object-fit:cover;border-radius:var(--radius);margin-bottom:32px;display:block;}}
    .art-lead{{font-size:18px;line-height:1.78;color:var(--ink-2);font-weight:300;margin-bottom:28px;}}
    .art-body p{{font-size:16.5px;line-height:1.8;color:var(--ink);margin-bottom:20px;}}
    .art-perspective{{background:var(--surface-2);border-left:4px solid var(--accent);padding:18px 22px;border-radius:0 var(--radius-sm) var(--radius-sm) 0;margin-top:32px;font-size:15px;line-height:1.7;color:var(--ink-2);}}
    .art-meta{{display:flex;gap:16px;align-items:center;margin-bottom:28px;padding-bottom:18px;border-bottom:2px solid var(--border);flex-wrap:wrap;font-size:13px;color:var(--ink-3);}}
    .art-meta strong{{color:var(--ink);}}
    .rel-links a{{display:block;padding:10px 0;border-bottom:1px solid var(--border-2);color:var(--accent);font-size:15px;font-weight:500;}}
  </style>
</head>
<body>
<a class="skip-link" href="#main-content">Skip to main content</a>
<header class="site-header" role="banner">
  <a href="../index.html" class="header-brand" aria-label="The Tech Brief — Home"><div class="brand-icon" aria-hidden="true">TB</div><span class="brand-name">Tech Brief</span></a>
  <button class="nav-toggle" aria-label="Toggle navigation" aria-controls="site-nav" aria-expanded="false"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg></button>
  <nav id="site-nav" class="site-nav" role="navigation" aria-label="Primary navigation">
    <a href="../index.html">Home</a><a href="../ai-news.html">AI News</a><a href="../broadcast-tech.html">Broadcast Tech</a><a href="../enterprise-tech.html">Enterprise Tech</a><a href="../cybersecurity-updates.html">Cybersecurity</a><a href="../mobile-gadgets.html">Mobile &amp; Gadgets</a><a href="../consumer-tech.html">Consumer Tech</a><a href="../gaming.html">Gaming</a><a href="../evs-automotive.html">EVs &amp; Automotive</a><a href="../startups-business.html">Startups &amp; Business</a><a href="../how-to.html">How-To Guides</a><a href="../about.html" class="nav-cta">About</a>
  </nav>
</header>
<main id="main-content">
  <article class="page-wrap" style="max-width:740px;">
    <div style="margin-bottom:12px;font-size:13px;"><a href="../index.html" style="color:var(--ink-3);">Home</a><span style="color:var(--ink-3);margin:0 6px;">&rsaquo;</span><a href="../{cat_page}" style="color:var(--accent);font-weight:700;">{category}</a></div>
    <a href="../{cat_page}" style="display:inline-block;background:{badge_color};color:#fff;padding:4px 14px;border-radius:999px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;margin-bottom:18px;text-decoration:none;">{icon} {category}</a>
    <h1 style="font-family:var(--font-serif);font-size:clamp(26px,4vw,40px);line-height:1.2;margin-bottom:14px;color:var(--ink);">{safe_title}</h1>
    <div class="art-meta"><span>By <strong>The Tech Brief Editorial Team</strong></span><span><time datetime="{date_str}">{pub_date}</time></span><span>3 min read</span></div>
    <img class="art-img" src="{image_url}" alt="{safe_title}" width="740" height="400" loading="eager">
    <div class="art-body">
      <p class="art-lead">{safe_summary}</p>
      <div class="art-perspective">
        <strong style="display:block;font-size:11px;text-transform:uppercase;letter-spacing:.8px;color:var(--accent);margin-bottom:6px;">The Tech Brief Perspective</strong>
        This development is part of an ongoing shift reshaping the {category} landscape. Staying ahead of these changes helps businesses, developers, and consumers make better decisions about the platforms, tools, and strategies they invest in.
      </div>
    </div>
    <div style="margin-top:32px;padding:14px 20px;background:var(--surface-2);border-radius:var(--radius);font-size:13px;color:var(--ink-3);">
      <strong style="color:var(--ink);">Editorial Note:</strong> This article is independently written by The Tech Brief editorial team.
      <a href="../about.html" style="color:var(--accent);margin-left:4px;">About our process &rarr;</a>
    </div>
    <div style="border-top:2px solid var(--border);margin-top:36px;padding-top:22px;">
      <h3 style="font-family:var(--font-serif);font-size:19px;margin-bottom:14px;">Continue Reading</h3>
      <div class="rel-links">
        <a href="../{cat_page}">{icon} More {category}</a>
        <a href="../how-to.html">📖 How-To Guides</a>
        <a href="../index.html">🏠 Back to Home</a>
      </div>
    </div>
  </article>
</main>
<footer class="site-footer" role="contentinfo">
  <div class="footer-inner">
    <div class="footer-about"><span class="brand-name">The Tech Brief</span><p>Independent technology publication delivering original editorial analysis. Updated daily.</p></div>
    <div class="footer-col"><h4>Categories</h4><a href="../ai-news.html">AI News</a><a href="../broadcast-tech.html">Broadcast Tech</a><a href="../enterprise-tech.html">Enterprise Tech</a><a href="../cybersecurity-updates.html">Cybersecurity</a><a href="../mobile-gadgets.html">Mobile &amp; Gadgets</a><a href="../consumer-tech.html">Consumer Tech</a><a href="../gaming.html">Gaming</a><a href="../evs-automotive.html">EVs &amp; Automotive</a><a href="../startups-business.html">Startups &amp; Business</a></div>
    <div class="footer-col"><h4>Site Info</h4><a href="../about.html">About</a><a href="../contact.html">Contact</a><a href="../legal/privacy.html">Privacy Policy</a><a href="../legal/terms.html">Terms of Use</a></div>
  </div>
  <div class="footer-bottom"><span>&copy; {year} The Tech Brief &mdash; thetechbrief.net. All rights reserved.</span></div>
</footer>
<script>(function(){{var t=document.querySelector('.nav-toggle'),n=document.getElementById('site-nav');if(!t||!n)return;t.addEventListener('click',function(){{var o=n.classList.toggle('open');t.setAttribute('aria-expanded',o);}});}})();</script>
<script src="../assets/cookie-consent.js"></script>
</body>
</html>"""


# ══════════════════════════════════════════════════════════════════════════════
# CATEGORY PAGE BUILDER — 3-TIER, NEVER BLANK
# FIX 1: Writes to RSS_ARTICLES_OUT (docs/articles/) not site/articles/
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

    # FIX 1: Write directly to docs/articles/
    os.makedirs(RSS_ARTICLES_OUT, exist_ok=True)

    cards = []
    for item in deduped:
        key    = _url_key(item['link'])
        cached = cache.get(key)

        # Tier 1a: fresh cache
        if cached and _is_cache_fresh(cached):
            editorial_summary = cached['editorial_summary']
            slug = cached['slug']
        # Tier 1b: new Groq rewrite
        elif rewrites_done[0] < MAX_REWRITES_PER_RUN and GROQ_API_KEY:
            print(f'    ✍  Groq [{rewrites_done[0]+1}]: {item["title"][:50]}…')
            summary = rewrite_via_groq(item['title'], category)
            if not summary:
                summary = local_fallback_summary(item['title'], category, key)
            rewrites_done[0] += 1
            slug = f"rss-{key}"
            cache[key] = {'editorial_summary': summary, 'slug': slug, 'title': item['title'], 'cat_slug': cat_slug, 'category': category, 'cached_on': datetime.now(timezone.utc).isoformat()}
            editorial_summary = summary
        # Tier 2: stale cache
        elif cached:
            editorial_summary = cached['editorial_summary']
            slug = cached['slug']
        # Tier 3: local fallback — NEVER BLANK
        else:
            slug = f"rss-{key}"
            editorial_summary = local_fallback_summary(item['title'], category, key)
            cache[key] = {'editorial_summary': editorial_summary, 'slug': slug, 'title': item['title'], 'cat_slug': cat_slug, 'category': category, 'cached_on': datetime.now(timezone.utc).isoformat()}

        image_url = safe_image(item.get('image'), cat_slug, slug)
        try:    iso_date = time.strftime('%Y-%m-%d', time.strptime(item['date'], '%B %d, %Y')) if item['date'] else today_str()
        except: iso_date = today_str()

        # FIX 1: Write to docs/articles/ directly
        article_html = build_internal_article_page(item['title'], editorial_summary, category, cat_slug, cat_page, iso_date, slug)
        with open(os.path.join(RSS_ARTICLES_OUT, f'{slug}.html'), 'w', encoding='utf-8') as f:
            f.write(article_html)

        cards.append({'title': item['title'], 'summary': editorial_summary, 'image': image_url, 'internal_url': f'articles/{slug}.html', 'ts': item['ts'], 'date': item['date'], 'category': category})

    cat_editorial = [a for a in editorial_articles if a.get('cat_slug') == cat_slug][:3]
    html = CATEGORY_TPL.render(meta=meta, cards=cards, cat_editorial=cat_editorial)
    with open(os.path.join(SITE_OUT, f"{cat_slug}.html"), 'w', encoding='utf-8') as f:
        f.write(html)

    tier = f"Groq({rewrites_done[0]})" if GROQ_API_KEY else "local-fallback"
    print(f'  ✓ {cat_slug}.html — {len(cards)} cards [{tier}], {len(cat_editorial)} deep-dives')
    return cards


# ══════════════════════════════════════════════════════════════════════════════
# HOMEPAGE + SITEMAP
# ══════════════════════════════════════════════════════════════════════════════

def build_home(editorial_articles: list):
    meta = dict(META_MAP['Home'])
    html = HOME_TPL.render(meta=meta, editorial_articles=editorial_articles[:9])
    with open(os.path.join(SITE_OUT, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  ✓ index.html ({len(editorial_articles[:9])} editorial articles)')


def build_sitemap(editorial_articles: list, rss_slugs: list):
    today = today_str()
    static = [('','hourly','1.0'),('ai-news.html','hourly','0.9'),('broadcast-tech.html','hourly','0.9'),('enterprise-tech.html','hourly','0.9'),('cybersecurity-updates.html','hourly','0.9'),('mobile-gadgets.html','hourly','0.9'),('consumer-tech.html','hourly','0.9'),('gaming.html','hourly','0.9'),('evs-automotive.html','hourly','0.9'),('startups-business.html','hourly','0.9'),('how-to.html','monthly','0.9'),('about.html','monthly','0.8'),('contact.html','monthly','0.7'),('legal/privacy.html','yearly','0.5'),('legal/terms.html','yearly','0.5'),('legal/disclaimer.html','yearly','0.4'),('legal/copyright.html','yearly','0.4'),('legal/affiliate.html','yearly','0.4')]
    fixed = [('articles/ai-agents-enterprise-2025.html','2025-02-01'),('articles/android-vs-iphone-2025.html','2025-02-15'),('articles/ransomware-playbook-2025.html','2025-02-10'),('articles/how-to-factory-reset-android.html','2025-03-01'),('articles/how-to-factory-reset-iphone.html','2025-03-01'),('articles/how-to-upgrade-windows.html','2025-03-01'),('articles/how-to-upgrade-macos.html','2025-03-01'),('articles/how-to-clear-cache.html','2025-03-01'),('articles/how-to-set-up-new-android.html','2025-03-01')]

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
            lines.append(u(f'{SITE_URL}/{a["url"]}', a['date'], 'monthly', '0.78'))
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
    os.makedirs(RSS_ARTICLES_OUT, exist_ok=True)  # FIX 1: ensure docs/articles/ exists first

    editorial_articles = load_editorial_articles()
    print(f'Loaded {len(editorial_articles)} editorial articles')
    print(f'Groq: {"ENABLED" if GROQ_API_KEY else "DISABLED — local fallbacks active (no blank pages)"}')

    cache         = load_cache()
    rewrites_done = [0]

    # Sync static assets (templates, legal, evergreen articles, JS/CSS)
    print('Syncing static assets…')
    sync_static_assets()

    # FIX 1: docs/articles/ already exists; RSS articles go there directly
    os.makedirs(RSS_ARTICLES_OUT, exist_ok=True)

    # FIX 2: Build trending BEFORE category pages (writes trending.json live)
    print('Building trending section…')
    build_trending()

    # Build category pages
    print(f'Building {len(FEEDS)} category pages…')
    for cat, urls in FEEDS.items():
        print(f'  [{cat}]')
        build_category(cat, urls, editorial_articles, cache, rewrites_done)

    # Collect rss slugs for sitemap (now from docs/articles/)
    rss_slugs = [
        os.path.splitext(f)[0]
        for f in os.listdir(RSS_ARTICLES_OUT)
        if f.startswith('rss-') and f.endswith('.html')
    ] if os.path.isdir(RSS_ARTICLES_OUT) else []

    print('Building homepage…')
    build_home(editorial_articles)

    print('Building sitemap…')
    build_sitemap(editorial_articles, rss_slugs)

    print(f'Saving cache ({len(cache)} entries)…')
    save_cache(cache)

    print(f'\n✅ Build complete')
    print(f'   Groq rewrites : {rewrites_done[0]}')
    print(f'   Cache entries : {len(cache)}')
    print(f'   Article pages : {len(rss_slugs)}')
    print(f'   Editorial     : {len(editorial_articles)}')


if __name__ == '__main__':
    main()
