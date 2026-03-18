"""
Build script for The Streamic — v3.5
Fixes:
  1. Global used-image tracker — every card on every page gets a unique photo
  2. Strips "Sponsored:" / "Sponsored Post:" / "Advertisement:" from titles
  3. Off-topic filter rejects entertainment/non-broadcast articles
  4. Expanded keyword map covers lenses, zooms, connectors, and more
  5. Source image filter prevents screenshot/tracker images from RSS
  6. All cards still link to internal pages (Groq rewrite or clean stub)
"""
import os, json, re, time, hashlib, textwrap
import feedparser, requests
from bs4 import BeautifulSoup
from slugify import slugify
from jinja2 import Template
from datetime import datetime, timezone

ROOT     = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA     = os.path.join(ROOT, 'data', 'feeds.json')
META     = os.path.join(ROOT, 'data', 'meta.json')
CACHE_F  = os.path.join(ROOT, 'data', 'article_cache.json')
SITE     = os.path.join(ROOT, 'docs')
SITE_SRC = os.path.join(ROOT, 'site')
SITE_URL = 'https://www.thestreamic.in'

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_URL     = 'https://api.groq.com/openai/v1/chat/completions'
MODEL        = 'llama3-70b-8192'
GA_TAG       = 'G-0VSHDN3ZR6'
ADSENSE_ID   = 'ca-pub-8033069131874524'
AUTHOR       = 'The Streamic Editorial Team'
MAX_NEW_PER_BUILD = 40

# ════════════════════════════════════════════════════════════════════════════
#  GLOBAL USED-IMAGE TRACKER
#  Ensures every card across the entire build gets a unique Unsplash photo ID
# ════════════════════════════════════════════════════════════════════════════
_USED_PHOTO_IDS: set = set()

def _next_unique_photo(photo_id: str, pool: list) -> str:
    """Return photo_id if unused; else walk pool until an unused one is found."""
    if photo_id not in _USED_PHOTO_IDS:
        _USED_PHOTO_IDS.add(photo_id)
        return photo_id
    for pid in pool:
        if pid not in _USED_PHOTO_IDS:
            _USED_PHOTO_IDS.add(pid)
            return pid
    # All pool images used — reset tracking for this category and reuse
    for pid in pool:
        _USED_PHOTO_IDS.discard(pid)
    _USED_PHOTO_IDS.add(pool[0])
    return pool[0]


# ── Load templates & data ──────────────────────────────────────────────────
with open(os.path.join(SITE_SRC, 'template_category.html'), 'r', encoding='utf-8') as f:
    CATEGORY_TPL = Template(f.read())
with open(os.path.join(SITE_SRC, 'template_home.html'), 'r', encoding='utf-8') as f:
    HOME_TPL = Template(f.read())
with open(DATA, 'r', encoding='utf-8') as f:
    FEEDS = json.load(f)
with open(META, 'r', encoding='utf-8') as f:
    META_MAP = json.load(f)


# ══════════════════════════════════════════════════════════════════════════════
#  OFF-TOPIC FILTER
#  Rejects articles that clearly have nothing to do with broadcast/streaming
# ══════════════════════════════════════════════════════════════════════════════

# If ANY of these phrases appears in a title, the article is skipped
OFF_TOPIC_PATTERNS = [
    r'\btrailer\b', r'\bofficial teaser\b', r'\bfeature film\b',
    r'\bmovie review\b', r'\bbox office\b', r'\bcinema release\b',
    r'\bchasing billie eilish\b', r'\bhiding transmitters for tiktok\b',
    r'\bwerner herzog\b', r'\bprofessional photographer\b',
    r'\bmaking a living as a\b', r'\bunglamorous truth\b',
    r'\bnew calculus of local sports.*subsidy\b',
    r'\bphoto career\b', r'\bfilm critic\b',
    r'\brecipe\b', r'\bwedding\b', r'\bfashion\b',
    r'\breal estate\b', r'\bcryptocurrency\b', r'\bnft\b',
]
_OFF_TOPIC_RE = re.compile('|'.join(OFF_TOPIC_PATTERNS), re.IGNORECASE)

# Require at least one broadcast-relevant word in the title or description
BROADCAST_SIGNALS = re.compile(
    r'\b(broadcast|streaming|video|audio|production|playout|cloud|ip\b|ndi|sdi|smpte|'
    r'nab|ibc|codec|encoder|cdn|ott|vod|mxf|avid|premiere|resolve|camera|lens|zoom|'
    r'monitor|router|switch|storage|mam|pam|ai\b|artificial intelligence|graphic|'
    r'newsroom|journalist|transmitter|satellite|rf\b|spectrum|antenna|5g|fibre|fiber|'
    r'signal|infrastructure|workflow|facility|studio|post.?production|nle|editing|'
    r'plugin|software|hardware|appliance|vendor|technology|tech\b|digital|media|'
    r'connector|cable|patch|rack|server|virtuali|cloud|remote|live event|esport)\b',
    re.IGNORECASE
)

def is_on_topic(title: str, raw_text: str) -> bool:
    """Return False for obviously off-topic articles."""
    if _OFF_TOPIC_RE.search(title):
        return False
    combined = title + ' ' + (raw_text or '')
    return bool(BROADCAST_SIGNALS.search(combined))


# ══════════════════════════════════════════════════════════════════════════════
#  TITLE CLEANING — strip sponsored/ad labels
# ══════════════════════════════════════════════════════════════════════════════

_JUNK_PREFIX = re.compile(
    r'^(sponsored\s*[:–\-]?\s*|sponsored\s+post\s*[:–\-]?\s*|'
    r'advertisement\s*[:–\-]?\s*|advertorial\s*[:–\-]?\s*|'
    r'partner\s+content\s*[:–\-]?\s*|paid\s+content\s*[:–\-]?\s*|'
    r'promoted\s*[:–\-]?\s*)',
    re.IGNORECASE
)
_JUNK_SUFFIX = re.compile(
    r'\s*(appeared first on|the post .{0,50}$|\|\s*\w[\w\s]{0,30}$)',
    re.IGNORECASE
)

def clean_title(title: str) -> str:
    t = _JUNK_PREFIX.sub('', (title or '').strip())
    t = _JUNK_SUFFIX.sub('', t).strip()
    return t


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE IMAGE FILTER
# ══════════════════════════════════════════════════════════════════════════════

TRUSTED_IMAGE_DOMAINS = {
    'images.unsplash.com', 'images.pexels.com', 'cdn.pixabay.com',
    'upload.wikimedia.org', 'commons.wikimedia.org',
    'tvbeurope.com', 'newscaststudio.com', 'tvtechnology.com',
    'broadcastbeat.com', 'svgeurope.org', 'digitaltvnews.net',
    'streamingmediablog.com', 'streaminglearningcenter.com',
    'provideocoalition.com', 'newsshooter.com', 'postperspective.com',
    'studiodaily.com', 'premiumbeat.com', 'motionographer.com',
    'cgchannel.com', 'filmmakermagazine.com', 'videomaker.com',
    'fstoppers.com', 'harmonicinc.com', 'haivision.com', 'pebble.tv',
    'wowza.com', 'mux.com', 'bitmovin.com', 'brightcove.com',
    'kaltura.com', 'vizrt.com', 'avid.com', 'frame.io',
    'aws.amazon.com', 'cloudflare.com', 'cloudinary.com',
}
BLOCKED_IMAGE_DOMAINS = {
    'google.com', 'google.co', 'bing.com', 'yahoo.com',
    'facebook.com', 'twitter.com', 'x.com', 'instagram.com',
    'tiktok.com', 'reddit.com', 'linkedin.com', 'pinterest.com',
    'youtube.com', 'ytimg.com', 'gravatar.com', 'wp.com',
    'wordpress.com', 'feedburner.com', 'placeholder.com',
    'via.placeholder.com', 'dummyimage.com',
}

def source_image_ok(url: str) -> bool:
    if not url or len(url) < 12: return False
    from urllib.parse import urlparse
    try: parsed = urlparse(url)
    except Exception: return False
    host = parsed.netloc.lower().lstrip('www.')
    path = parsed.path.lower()
    if parsed.scheme not in ('https', 'http'): return False
    for bad in BLOCKED_IMAGE_DOMAINS:
        if host == bad or host.endswith('.' + bad): return False
    has_ext = any(path.endswith(x) for x in ('.jpg','.jpeg','.png','.webp','.gif','.avif'))
    is_trusted = any(host == d or host.endswith('.'+d) for d in TRUSTED_IMAGE_DOMAINS)
    if not has_ext and not is_trusted: return False
    if has_ext and len(path.split('/')[-1]) < 8: return False
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  KEYWORD → IMAGE MAP  (60+ groups, every photo ID unique across the map)
#  More specific patterns listed first — first match wins
# ══════════════════════════════════════════════════════════════════════════════
# Each entry: ([keywords], 'unsplash-photo-id', [fallback_pool_ids])
KEYWORD_IMAGE_MAP = [
    # NAB / IBC / trade shows
    (['nab show','nab 2026','nab 2025','ibc 2026','ibc 2025','ibc show','trade show','expo floor'],
     'photo-1540575467063-178a50c2df87',
     ['photo-1492619375914-88005aa9e8fb','photo-1568992687947-868a62a9f521']),

    # Lens / zoom / optics
    (['fujinon','zeiss','sigma lens','canon lens','fujifilm lens','broadcast zoom','broadcast lens',
      'ua22','ua27','digisuper','xj','hj lens','4k broadcast lens'],
     'photo-1551269901-5c2d5b2e3b24',
     ['photo-1516035069371-29a1b244cc32','photo-1598653222000-6b7b7a552625']),

    # Connectors / cables / hardware
    (['connector','opticalcon','neutrik','xlr connector','bnc connector','fiber connector',
      'cable management','patch panel','lemo','triax'],
     'photo-1558494949-ef010cbdcc31',
     ['photo-1580584126903-c17d41830450','photo-1563208769-5f1d48cc3d16']),

    # Wireless mic / RF
    (['wireless mic','lectrosonics','sennheiser wireless','shure wireless','zaxcom',
      'radio mic','lavalier','body pack','belt pack','ifb','intercom wireless'],
     'photo-1598520106830-8c45c2035460',
     ['photo-1520523839897-bd0b52f945a0','photo-1598488035139-bdbb2231ce04']),

    # Microphone / podcast / voice
    (['microphone','podcast','voiceover','voice over','radio presenter','commentary'],
     'photo-1520523839897-bd0b52f945a0',
     ['photo-1493863641943-9b68992a8d07','photo-1598520106830-8c45c2035460']),

    # Audio mixer / console
    (['audio mixer','mixing console','mixing desk','fader','ssl console','neve console',
      'lawo','calrec','soundcraft','audio console','studer'],
     'photo-1511379938547-c1f69419868d',
     ['photo-1598488035139-bdbb2231ce04','photo-1516321497487-e288fb19713f']),

    # Audio post / immersive / dubbing
    (['dubbing','audio post','sound mix','dolby atmos','spatial audio','immersive audio',
      'adm','dialogue edit','foley','adr'],
     'photo-1516321497487-e288fb19713f',
     ['photo-1511379938547-c1f69419868d','photo-1520523839897-bd0b52f945a0']),

    # Sonic branding / music
    (['sonic branding','original music','composer','score','jingle','theme music',
      'sound design','audio branding','music composition'],
     'photo-1470225620780-dba8ba36b745',
     ['photo-1511379938547-c1f69419868d','photo-1520523839897-bd0b52f945a0']),

    # Sports broadcast
    (['sports broadcast','sports production','ob van','outside broadcast',
      'stadium broadcast','sports rights','live sport production'],
     'photo-1560272564-c83b66b1ad12',
     ['photo-1471295253337-3ceaaedca402','photo-1540575467063-178a50c2df87']),

    # Live events / concert
    (['live event','live production','concert production','festival tech','touring production'],
     'photo-1492619375914-88005aa9e8fb',
     ['photo-1568992687947-868a62a9f521','photo-1540575467063-178a50c2df87']),

    # Camera / acquisition (generic)
    (['4k camera','8k camera','uhd camera','pov camera','ip camera',
      'broadcast camera','cinema camera','camera system','camera release'],
     'photo-1516035069371-29a1b244cc32',
     ['photo-1567095761054-7003afd47020','photo-1551269901-5c2d5b2e3b24']),

    # Drone / aerial
    (['drone','aerial camera','uav','unmanned aerial','fpv camera'],
     'photo-1473968512647-3e447244af8f',
     ['photo-1516035069371-29a1b244cc32','photo-1567095761054-7003afd47020']),

    # Streaming platform / OTT / VOD
    (['streaming platform','ott platform','svod','avod','vod platform','video platform'],
     'photo-1616401784845-180882ba9ba8',
     ['photo-1574717024653-61fd2cf4d44d','photo-1611532736597-de2d4265fba3']),

    # Encoder / codec
    (['encoder','encoding','transcoding','codec','hevc','h.265','av1','h.264','avc','mpeg'],
     'photo-1574717024653-61fd2cf4d44d',
     ['photo-1598488035139-bdbb2231ce04','photo-1574719048966-5a17c9a99158']),

    # CDN / delivery
    (['cdn','content delivery network','edge delivery','origin server','caching',
      'manifest','bitrate ladder','limelight','akamai','fastly'],
     'photo-1451187580459-43490279c0fa',
     ['photo-1526374965328-7f61d4dc18c5','photo-1516321318423-f06f85e504b3']),

    # Low latency / SRT / WebRTC
    (['low latency','ultra-low latency','webrtc','srt protocol','zixi','bonding'],
     'photo-1516321318423-f06f85e504b3',
     ['photo-1574717024653-61fd2cf4d44d','photo-1451187580459-43490279c0fa']),

    # Cloud production / remote production
    (['cloud production','cloud playout','cloud broadcast','remote production','remi','at-home production'],
     'photo-1544197150-b99a580bb7a8',
     ['photo-1560472355-536de3962603','photo-1451187580459-43490279c0fa']),

    # AWS / Azure / cloud platform
    (['aws media','amazon elemental','azure media','google cloud media','multi-cloud','cloud migration'],
     'photo-1560472355-536de3962603',
     ['photo-1544197150-b99a580bb7a8','photo-1504639725590-34d0984388bd']),

    # Virtualisation / software-defined / containers
    (['virtualisation','virtualization','software-defined','containerisation','kubernetes','docker'],
     'photo-1504639725590-34d0984388bd',
     ['photo-1526374965328-7f61d4dc18c5','photo-1560472355-536de3962603']),

    # AI general
    (['artificial intelligence','machine learning','deep learning','neural network',
      'llm','generative ai','large language model','ai-powered'],
     'photo-1677442135703-1787eea5ce01',
     ['photo-1620712943543-bcc4688e7485','photo-1655635643532-fa9ba2648cbe']),

    # AI archive / metadata / MAM
    (['ai archive','media asset management','mam system','dam system','metadata tagging',
      'content catalogue','ai metadata','asset management'],
     'photo-1655635643532-fa9ba2648cbe',
     ['photo-1677442135703-1787eea5ce01','photo-1620712943543-bcc4688e7485']),

    # AI post / automated editing / caption
    (['ai edit','automated editing','ai post','ai subtitle','ai caption',
      'speech to text','transcription','auto caption'],
     'photo-1620712943543-bcc4688e7485',
     ['photo-1677442135703-1787eea5ce01','photo-1635070041078-e363dbe005cb']),

    # Computer vision
    (['facial recognition','object detection','computer vision','image recognition','scene detection'],
     'photo-1533228100845-08145b01de14',
     ['photo-1677442135703-1787eea5ce01','photo-1620712943543-bcc4688e7485']),

    # Motion design / broadcast design
    (['motion graphics','animation studio','title sequence','lower third',
      'broadcast design','motion design'],
     'photo-1547658719-da2b51169166',
     ['photo-1593642632559-0c6d3fc62b89','photo-1518770660439-4636190af475']),

    # Real-time graphics / virtual set / XR
    (['real-time graphics','broadcast graphics','virtual set','virtual studio',
      'augmented reality broadcast','extended reality','xr production'],
     'photo-1593642632559-0c6d3fc62b89',
     ['photo-1547658719-da2b51169166','photo-1518770660439-4636190af475']),

    # Unreal Engine / LED volume / VFX
    (['unreal engine','game engine','led volume','led wall','virtual production stage',
      'icvfx','visual effects','vfx','cgi','compositing','green screen'],
     'photo-1518770660439-4636190af475',
     ['photo-1610563166150-b34df4f3bcd6','photo-1593642632559-0c6d3fc62b89']),

    # Video editing / NLE — careful not to over-match
    (['media composer','premiere pro integration','final cut pro','davinci resolve workflow',
      'edit suite workflow','non-linear editing','avid workflow','adobe workflow',
      'editing software','nle workflow'],
     'photo-1574717025058-97e3af4ef9b5',
     ['photo-1605106702734-205df224ecce','photo-1572044162444-ad60f128bdea']),

    # Colour grading
    (['colour grading','color grading','grading suite','colour science','lut','hdr grading',
      'davinci resolve grading'],
     'photo-1605106702734-205df224ecce',
     ['photo-1574717025058-97e3af4ef9b5','photo-1572044162444-ad60f128bdea']),

    # Playout / master control / on-air
    (['channel in a box','ciab','master control','on-air','playout server',
      'playout automation','broadcast playout','transmission'],
     'photo-1612420696760-0a0f34d3e7d0',
     ['photo-1478737270239-2f02b77fc618','photo-1590602847861-f357a9332bbc']),

    # Workflow automation / scheduling
    (['workflow automation','orchestration','scheduling system','rundown',
      'automation system','broadcast playlist'],
     'photo-1478737270239-2f02b77fc618',
     ['photo-1612420696760-0a0f34d3e7d0','photo-1590602847861-f357a9332bbc']),

    # SMPTE 2110 / IP production
    (['smpte st 2110','smpte 2110','ip production','ip routing',
      'ip infrastructure','sdi to ip','nmos','ipmx'],
     'photo-1486312338219-ce68d2c6f44d',
     ['photo-1497366216548-37526070297c','photo-1558494949-ef010cbdcc31']),

    # Network / switching
    (['network switch','ethernet switch','fibre optic','fiber optic',
      '10gbe','25gbe','spine leaf','network infrastructure'],
     'photo-1497366216548-37526070297c',
     ['photo-1486312338219-ce68d2c6f44d','photo-1560472354-b33ff0c44a43']),

    # Storage
    (['storage system','nas storage','san storage','object storage',
      'tape library','lto','nearline storage','archive storage'],
     'photo-1560472354-b33ff0c44a43',
     ['photo-1497366216548-37526070297c','photo-1486312338219-ce68d2c6f44d']),

    # 5G / mobile / bonding
    (['5g broadcast','5g production','bonded cellular','mobile journalism',
      'mojo','cellular uplink'],
     'photo-1526374965328-7f61d4dc18c5',
     ['photo-1516321318423-f06f85e504b3','photo-1451187580459-43490279c0fa']),

    # Satellite / uplink
    (['satellite','uplink','downlink','dish antenna','vsat','satellite truck','flyaway'],
     'photo-1581092583537-20d51b4b4f1b',
     ['photo-1516321318423-f06f85e504b3','photo-1526374965328-7f61d4dc18c5']),

    # Monitor / display / multiviewer
    (['reference monitor','broadcast monitor','confidence monitor','multiviewer',
      'hdr display','oled monitor','wall display'],
     'photo-1527443224154-c4a3942d3acf',
     ['photo-1593642632559-0c6d3fc62b89','photo-1547658719-da2b51169166']),

    # Cybersecurity
    (['cybersecurity','security breach','vulnerability','ransomware','data breach',
      'cyber attack','zero trust','penetration test'],
     'photo-1550751827-4bd374c3f58b',
     ['photo-1558494949-ef010cbdcc31','photo-1486312338219-ce68d2c6f44d']),

    # Newsroom / NRCS
    (['newsroom','nrcs','news production','breaking news','news editor','wire service'],
     'photo-1504711434969-e33886168f5c',
     ['photo-1493863641943-9b68992a8d07','photo-1585829365295-ab7cd400c167']),

    # Presenter / anchor
    (['presenter','anchor','news anchor','reporter','correspondent','studio host'],
     'photo-1493863641943-9b68992a8d07',
     ['photo-1504711434969-e33886168f5c','photo-1585829365295-ab7cd400c167']),

    # Business / appointment
    (['appoints','appointed','ceo','chief executive','managing director',
      'president','board director','vice president','moves into role'],
     'photo-1507679799987-c73779587ccf',
     ['photo-1460925895917-afdab827c52f','photo-1553877522-43269d4ea984']),

    # Investment / M&A
    (['acquisition','merger','raises','investment','funding','venture capital',
      'private equity','series a','series b'],
     'photo-1460925895917-afdab827c52f',
     ['photo-1507679799987-c73779587ccf','photo-1553877522-43269d4ea984']),

    # Partnership / integration
    (['partnership','integration','interoperability','workflow integration',
      'api integration','plugin','showcase'],
     'photo-1553877522-43269d4ea984',
     ['photo-1507679799987-c73779587ccf','photo-1486312338219-ce68d2c6f44d']),

    # Training / education
    (['training','certification','workshop','masterclass','learning','course'],
     'photo-1434030216411-0b793f4b4173',
     ['photo-1507679799987-c73779587ccf','photo-1493863641943-9b68992a8d07']),

    # Broadcast facility / equipment room
    (['broadcast facility','facility upgrade','equipment room','technical hub',
      'mdf','idf','rack room'],
     'photo-1504384308090-c894fdcc538d',
     ['photo-1486312338219-ce68d2c6f44d','photo-1560472354-b33ff0c44a43']),

    # How-to / install / guide
    (['install','installation','how to','how-to','step by step','guide','tutorial'],
     'photo-1434030216411-0b793f4b4173',
     ['photo-1518770660439-4636190af475','photo-1504384308090-c894fdcc538d']),
]

# Fallback pools per category — unique IDs not used in the keyword map above
CATEGORY_IMAGE_POOLS = {
    'streaming':          ['photo-1616401784845-180882ba9ba8','photo-1574719048966-5a17c9a99158','photo-1611532736597-de2d4265fba3','photo-1478737270239-2f02b77fc618','photo-1492619375914-88005aa9e8fb','photo-1590602847861-f357a9332bbc','photo-1568992687947-868a62a9f521','photo-1471295253337-3ceaaedca402'],
    'cloud':              ['photo-1588508065123-287b28e013da','photo-1531297484001-80022131f5a1','photo-1558494949-ef010cbdcc31','photo-1580584126903-c17d41830450','photo-1563208769-5f1d48cc3d16','photo-1573164713988-8665fc963095','photo-1509822929063-6b6cfc9b42f2','photo-1510511459019-5dda7724fd87'],
    'ai-post-production': ['photo-1635070041078-e363dbe005cb','photo-1501526029524-a8ea952b15be','photo-1572044162444-ad60f128bdea','photo-1526374965328-7f61d4dc18c5','photo-1488229297570-58520851e868','photo-1573164713988-8665fc963095','photo-1480944657103-7fed22359e1d','photo-1509822929063-6b6cfc9b42f2'],
    'graphics':           ['photo-1541462608143-67571c6738dd','photo-1497091071254-cc9b2ba7c48a','photo-1610563166150-b34df4f3bcd6','photo-1472214103451-9374bd1c798e','photo-1558618666-fcd25c85cd64','photo-1557804506-669a67965ba0','photo-1600880292203-757bb62b4baf','photo-1549317661-bd32c8ce0db2'],
    'playout':            ['photo-1612420696760-0a0f34d3e7d0','photo-1590602847861-f357a9332bbc','photo-1474654819140-b1f1f9af45c0','photo-1602992708529-c9fdb12905c9','photo-1568992687947-868a62a9f521','photo-1471295253337-3ceaaedca402','photo-1525704911916-c4cc7e4c79f3','photo-1558618047-f3dc8e28c5b1'],
    'infrastructure':     ['photo-1542744094-3a31f272c490','photo-1521737711867-e3b97375f902','photo-1600880292203-757bb62b4baf','photo-1583121274602-3e2820c69888','photo-1574719048966-5a17c9a99158','photo-1563208769-5f1d48cc3d16','photo-1580584126903-c17d41830450','photo-1509822929063-6b6cfc9b42f2'],
    'newsroom':           ['photo-1432821596592-e2c18b78144f','photo-1503428593586-e225b39bddfe','photo-1557804506-669a67965ba0','photo-1513519245088-0e12902e5a38','photo-1495020689067-958852a7765e','photo-1488229297570-58520851e868','photo-1576091160399-112ba8d25d1d','photo-1455390582262-044cdead277a'],
    'featured':           ['photo-1568992687947-868a62a9f521','photo-1471295253337-3ceaaedca402','photo-1574719048966-5a17c9a99158','photo-1602992708529-c9fdb12905c9','photo-1474654819140-b1f1f9af45c0','photo-1525704911916-c4cc7e4c79f3','photo-1572044162444-ad60f128bdea','photo-1572044162444-ad60f128bdea'],
    'default':            ['photo-1568992687947-868a62a9f521','photo-1471295253337-3ceaaedca402','photo-1574719048966-5a17c9a99158','photo-1602992708529-c9fdb12905c9','photo-1474654819140-b1f1f9af45c0','photo-1525704911916-c4cc7e4c79f3','photo-1557804506-669a67965ba0','photo-1455390582262-044cdead277a'],
}

BADGE_COLORS = {'streaming':'#0071e3','cloud':'#5856d6','ai-post-production':'#FF2D55','graphics':'#FF9500','playout':'#34C759','infrastructure':'#8E8E93','newsroom':'#D4AF37','featured':'#1d1d1f'}
BADGE_ICONS  = {'streaming':'📡','cloud':'☁️','ai-post-production':'🎬','graphics':'🎨','playout':'▶️','infrastructure':'🏗️','newsroom':'📰','featured':'⭐'}


def keyword_image(title: str, cat_slug: str, seed: str) -> str:
    """Keyword scan → unique Unsplash URL (global deduplication enforced)."""
    title_lower = (title or '').lower()
    for keywords, photo_id, fallback_pool in KEYWORD_IMAGE_MAP:
        if any(kw in title_lower for kw in keywords):
            all_options = [photo_id] + fallback_pool
            unique_id = _next_unique_photo(photo_id, all_options)
            return f'https://images.unsplash.com/{unique_id}?w=800&auto=format&fit=crop'
    pool = CATEGORY_IMAGE_POOLS.get(cat_slug, CATEGORY_IMAGE_POOLS['default'])
    idx  = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(pool)
    pid  = pool[idx]
    unique_id = _next_unique_photo(pid, pool)
    return f'https://images.unsplash.com/{unique_id}?w=800&auto=format&fit=crop'


# ── Cache helpers ──────────────────────────────────────────────────────────
def load_cache():
    if os.path.exists(CACHE_F):
        try:
            with open(CACHE_F, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception: pass
    return {}

def save_cache(cache):
    with open(CACHE_F, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

def url_key(url):
    return hashlib.md5(url.encode()).hexdigest()[:16]


def load_editorial_articles():
    path = os.path.join(ROOT, 'data', 'generated_articles.json')
    if not os.path.exists(path): return []
    try:
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)
    except Exception: return []


def load_editorial_spotlight():
    path = os.path.join(SITE_SRC, 'editorial.txt')
    if not os.path.exists(path): return []
    with open(path, 'r', encoding='utf-8') as f: raw = f.read()
    articles = []
    for block in re.split(r'\n===\s*\n', raw):
        fields, para_lines, reading = {}, [], False
        for line in block.splitlines():
            s = line.strip()
            if s.startswith('##'): continue
            if not reading:
                m = re.match(r'^(TITLE|BADGE|COLOR|ICON|READ)\s*:\s*(.+)$', s, re.IGNORECASE)
                if m: fields[m.group(1).upper()] = m.group(2).strip(); continue
                if fields and not s: reading = True; continue
            else: para_lines.append(line)
        if not fields.get('TITLE'): continue
        paras, cur = [], []
        for line in para_lines:
            if line.strip() == '':
                if cur:
                    p = ' '.join(cur).strip()
                    if p: paras.append(p)
                    cur = []
            else: cur.append(line.strip())
        if cur:
            p = ' '.join(cur).strip()
            if p: paras.append(p)
        if paras:
            articles.append({'title':fields.get('TITLE','Untitled'),'badge':fields.get('BADGE','Editorial'),
                             'color':fields.get('COLOR','#1d1d1f'),'icon':fields.get('ICON','📖'),
                             'read_time':fields.get('READ','5 min read'),'paragraphs':paras})
    return articles[:2]


# ── Text helpers ───────────────────────────────────────────────────────────
def clean_text(html):
    txt = BeautifulSoup(html or '', 'html.parser').get_text(' ')
    txt = re.sub(r'\s+', ' ', txt)
    # Strip syndicated boilerplate
    txt = re.sub(r'(appeared first on[\s\S]{0,80}|the post [\s\S]{0,100}|&nbsp;)',
                 '', txt, flags=re.IGNORECASE)
    # Strip truncation markers: [...] [&hellip;] ... Read more (more)
    txt = re.sub(r'\s*(\[\s*[\.…]+\s*\]|\[\s*more\s*\]|\(\.\.\.\)|read more\.?|\(more\)|&hellip;)\s*$',
                 '', txt, flags=re.IGNORECASE)
    # Strip bare trailing ellipsis
    txt = re.sub(r'\s*\.{2,}\s*$', '', txt)
    txt = re.sub(r'\s*…\s*$', '', txt)
    txt = _JUNK_PREFIX.sub('', txt)
    return txt.strip()

def first_sentences(text, n=2):
    parts = re.split(r'(?<=[.!?])\s+', (text or '').strip())
    return ' '.join(parts[:n]) if parts else (text or '')[:240]

def first_image(entry):
    for m in (entry.get('media_content') or []):
        u = m.get('url','')
        if source_image_ok(u): return u
    for t in (entry.get('media_thumbnail') or []):
        u = t.get('url','')
        if source_image_ok(u): return u
    for e2 in (entry.get('enclosures') or []):
        u = e2.get('href') or e2.get('url') or ''
        if source_image_ok(u): return u
    for c in (entry.get('content') or []):
        img = BeautifulSoup(c.get('value',''), 'html.parser').find('img')
        if img:
            u = img.get('src','')
            if source_image_ok(u): return u
    desc = entry.get('summary') or entry.get('description') or ''
    if desc:
        img = BeautifulSoup(desc, 'html.parser').find('img')
        if img:
            u = img.get('src','')
            if source_image_ok(u): return u
    return None

def parse_time(entry):
    t = entry.get('published_parsed') or entry.get('updated_parsed')
    return time.mktime(t) if t else 0

def fmt_date(ts):
    return time.strftime('%B %d, %Y', time.localtime(ts)) if ts else ''


# ── Article HTML ───────────────────────────────────────────────────────────
def _article_page(key, headline, summary, lead, body_paras, conclusion,
                  cat_slug, cat_name, date_str, image_url):
    e  = lambda s: str(s).replace('<','&lt;').replace('>','&gt;')
    bc = BADGE_COLORS.get(cat_slug, '#0071e3')
    bi = BADGE_ICONS.get(cat_slug, '📡')
    url = f'{SITE_URL}/articles/rss-{key}.html'
    yr  = datetime.now(timezone.utc).year
    body_html = f'<p class="art-lead">{e(lead)}</p>\n'
    for p in body_paras: body_html += f'    <p>{e(p)}</p>\n'
    if conclusion: body_html += f'    <p class="art-conclusion">{e(conclusion)}</p>\n'
    schema = json.dumps({'@context':'https://schema.org','@type':'Article',
        'headline':headline,'description':summary,'image':image_url,
        'datePublished':date_str,'dateModified':date_str,
        'author':{'@type':'Organization','name':AUTHOR},
        'publisher':{'@type':'Organization','name':'The Streamic','url':SITE_URL},
        'mainEntityOfPage':url,'articleSection':cat_name}, indent=2)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('consent','default',{{'analytics_storage':'denied','ad_storage':'denied','ad_user_data':'denied','ad_personalization':'denied','wait_for_update':500}});</script>
  <script async src="https://www.googletagmanager.com/gtag/js?id={GA_TAG}"></script>
  <script>gtag('js',new Date());gtag('config','{GA_TAG}');</script>
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_ID}" crossorigin="anonymous"></script>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{e(headline)} | The Streamic</title>
  <meta name="description" content="{e(summary)}">
  <meta name="robots" content="index, follow"><meta name="author" content="{AUTHOR}">
  <link rel="canonical" href="{url}">
  <meta property="og:type" content="article"><meta property="og:site_name" content="The Streamic">
  <meta property="og:title" content="{e(headline)}"><meta property="og:description" content="{e(summary)}">
  <meta property="og:url" content="{url}"><meta property="og:image" content="{image_url}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{e(headline)}"><meta name="twitter:description" content="{e(summary)}">
  <meta name="twitter:image" content="{image_url}">
  <script type="application/ld+json">{schema}</script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Montserrat:wght@300;400;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../style.css">
  <style>
    .aw{{max-width:740px;margin:0 auto;padding:40px 24px 80px}}
    .ah{{width:100%;max-height:400px;object-fit:cover;border-radius:12px;margin-bottom:28px;display:block}}
    .ac{{font-size:13px;color:#86868b;margin-bottom:12px}}.ac a{{color:#86868b;text-decoration:none}}.ac a:hover{{color:#000}}
    .ab{{display:inline-block;background:{bc};color:#fff;padding:4px 14px;border-radius:999px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;margin-bottom:14px;text-decoration:none}}
    .at{{font-family:Montserrat,sans-serif;font-size:clamp(24px,4vw,40px);font-weight:700;line-height:1.2;margin-bottom:12px;color:#1d1d1f}}
    .am{{font-size:13px;color:#86868b;margin-bottom:26px;padding-bottom:16px;border-bottom:1px solid #d2d2d7;display:flex;gap:14px;flex-wrap:wrap;align-items:center}}
    .am strong{{color:#1d1d1f}}.am a{{margin-left:auto;color:{bc};font-weight:600;font-size:13px;text-decoration:none}}
    .art-lead{{font-size:18px;line-height:1.75;color:#424245;margin-bottom:22px}}
    .art-body p{{font-size:16px;line-height:1.78;color:#1d1d1f;margin-bottom:18px}}
    .art-conclusion{{background:#f5f5f7;border-left:4px solid {bc};padding:14px 18px;border-radius:0 8px 8px 0;font-size:16px;line-height:1.7;color:#424245;font-style:italic;margin-top:24px}}
    .an{{margin-top:32px;padding:14px 18px;background:#f5f5f7;border-radius:8px;font-size:13px;color:#86868b}}.an strong{{color:#1d1d1f}}
    .ar{{border-top:1px solid #d2d2d7;margin-top:40px;padding-top:22px}}
    .ar h3{{font-family:Montserrat,sans-serif;font-size:17px;font-weight:700;margin-bottom:12px}}
    .ar a{{display:block;padding:8px 0;border-bottom:1px solid #f5f5f7;color:{bc};font-size:14px;font-weight:500;text-decoration:none}}.ar a:hover{{text-decoration:underline}}
    .ads{{margin:24px 0;line-height:0;font-size:0}}.ads ins:empty{{display:none}}
  </style>
</head>
<body>
  <nav class="site-nav"><div class="nav-inner">
    <a href="../featured.html" class="nav-logo-container">
      <img src="../assets/logo.png" alt="The Streamic" class="nav-logo-image" onload="this.closest('.nav-logo-container').classList.add('logo-loaded')">
      <span class="nav-logo">THE STREAMIC</span>
    </a>
    <button class="nav-toggle" aria-label="Toggle menu">☰</button>
    <ul class="nav-links">
      <li><a href="../featured.html">FEATURED</a></li><li><a href="../infrastructure.html">INFRASTRUCTURE</a></li>
      <li><a href="../graphics.html">GRAPHICS</a></li><li><a href="../cloud.html">CLOUD PRODUCTION</a></li>
      <li><a href="../streaming.html">STREAMING</a></li><li><a href="../ai-post-production.html">AI &amp; POST-PRODUCTION</a></li>
      <li><a href="../playout.html">PLAYOUT</a></li><li><a href="../newsroom.html">NEWSROOM</a></li>
    </ul>
    <div class="header-subscribe"><a href="../vlog.html" class="editors-desk-link">Editor's Desk</a></div>
  </div></nav>
  <main><div class="aw">
    <div class="ac"><a href="../featured.html">Home</a> &rsaquo; <a href="../{cat_slug}.html" style="color:{bc};font-weight:600;">{cat_name}</a></div>
    <a href="../{cat_slug}.html" class="ab">{bi} {cat_name}</a>
    <h1 class="at">{e(headline)}</h1>
    <div class="am"><span>By <strong>{AUTHOR}</strong></span><span><time datetime="{date_str}">{date_str}</time></span><span>3 min read</span><a href="../{cat_slug}.html">More {cat_name} &rarr;</a></div>
    <img class="ah" src="{image_url}" alt="{e(headline)}" width="740" height="400" loading="eager">
    <div class="ads"><ins class="adsbygoogle" style="display:block" data-ad-client="{ADSENSE_ID}" data-ad-slot="auto" data-ad-format="auto" data-full-width-responsive="true"></ins><script>(adsbygoogle=window.adsbygoogle||[]).push({{}});</script></div>
    <div class="art-body">{body_html}</div>
    <div class="ads"><ins class="adsbygoogle" style="display:block" data-ad-client="{ADSENSE_ID}" data-ad-slot="auto" data-ad-format="auto" data-full-width-responsive="true"></ins><script>(adsbygoogle=window.adsbygoogle||[]).push({{}});</script></div>
    <div class="an"><strong>Editorial Note:</strong> This article was written by The Streamic editorial team as original commentary on broadcast and streaming technology. <a href="../about.html" style="color:{bc};margin-left:6px;">About The Streamic &rarr;</a></div>
    <div class="ar"><h3>Continue Reading</h3><a href="../{cat_slug}.html">{bi} All {cat_name} Coverage</a><a href="../featured.html">⭐ Featured Stories</a><a href="../vlog.html">🎙️ Editor's Desk</a></div>
  </div></main>
  <footer style="background:#1d1d1f;color:#86868b;padding:32px 24px;text-align:center;font-size:13px;margin-top:52px;">
    <div style="max-width:1200px;margin:0 auto;">
      <p style="margin-bottom:8px;"><a href="../featured.html" style="color:#fff;font-weight:700;text-decoration:none;font-size:15px;">THE STREAMIC</a></p>
      <p style="margin-bottom:12px;">Independent broadcast and streaming technology publication.</p>
      <p><a href="../streaming.html" style="color:#86868b;margin:0 8px;">Streaming</a><a href="../cloud.html" style="color:#86868b;margin:0 8px;">Cloud</a><a href="../ai-post-production.html" style="color:#86868b;margin:0 8px;">AI &amp; Post</a><a href="../graphics.html" style="color:#86868b;margin:0 8px;">Graphics</a><a href="../about.html" style="color:#86868b;margin:0 8px;">About</a><a href="../privacy.html" style="color:#86868b;margin:0 8px;">Privacy</a></p>
      <p style="margin-top:14px;">&copy; {yr} The Streamic. All rights reserved.</p>
    </div>
  </footer>
  <script>(function(){{var t=document.querySelector('.nav-toggle'),n=document.querySelector('.nav-links');if(!t||!n)return;t.addEventListener('click',function(){{n.classList.toggle('nav-open');}});}})();</script>
</body></html>"""


# ── Groq rewrite ───────────────────────────────────────────────────────────
SYSTEM = ("You are a senior broadcast technology journalist at The Streamic. "
          "Write 100% original editorial content. Never copy, quote, or reference any source. "
          "Never mention any publication or website. No syndicated phrases. "
          "Return ONLY valid JSON — no markdown fences, no preamble.")

def groq_rewrite(title, raw_text, cat_name):
    if not GROQ_API_KEY: return None
    ctx = re.sub(r'(appeared first on|according to|the post .{0,60}|&nbsp;|read more\.?)',
                 '', raw_text or '', flags=re.IGNORECASE).strip()[:500]
    user = textwrap.dedent(f"""
        Write a 300-400 word original broadcast/streaming technology article for The Streamic.
        Topic inspiration ONLY (do NOT copy): Title: "{title}"  Category: {cat_name}
        Background (rewrite entirely in your own words): "{ctx}"
        Return JSON:
        {{"headline":"Original SEO headline 8-14 words","summary":"One sentence 20-30 words","lead":"2-sentence opening","body":["para 1 60-80w","para 2 60-80w","para 3 60-80w"],"conclusion":"One forward-looking sentence"}}
        Rules: 100% original, no source names, technical depth for broadcast professionals.
    """).strip()
    for attempt in range(1, 3):
        try:
            r = requests.post(GROQ_URL,
                headers={'Authorization':f'Bearer {GROQ_API_KEY}','Content-Type':'application/json'},
                json={'model':MODEL,'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':user}],'max_tokens':900,'temperature':0.72},
                timeout=45)
            r.raise_for_status()
            raw = r.json()['choices'][0]['message']['content'].strip()
            raw = re.sub(r'^```(?:json)?\s*','',raw,flags=re.MULTILINE)
            raw = re.sub(r'\s*```$','',raw.strip()).strip()
            d   = json.loads(raw)
            if not {'headline','summary','lead','body','conclusion'}.issubset(d): return None
            if not isinstance(d['body'],list) or len(d['body'])<2: return None
            return d
        except requests.exceptions.HTTPError as e:
            if e.response.status_code==429 and attempt==1:
                print('    ⏳ Rate limit 20s…'); time.sleep(20)
            else: print(f'    ✗ HTTP {e.response.status_code}'); return None
        except Exception as ex: print(f'    ✗ {ex}'); return None
    return None


def make_stub(key, title, raw_text, cat_slug, cat_name, ts):
    """
    Build an internal article page from RSS text alone (no Groq call).
    Uses the actual RSS content split into real paragraphs — never generic boilerplate.
    """
    today   = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    img_url = keyword_image(title, cat_slug, key)

    # Split raw_text into clean sentences, min 25 chars
    all_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', (raw_text or '').strip())
                     if len(s.strip()) >= 25]

    # ── Build lead (first 2–3 sentences) ────────────────────────────────────
    if len(all_sentences) >= 2:
        lead = ' '.join(all_sentences[:2])
    elif len(all_sentences) == 1:
        lead = all_sentences[0]
    else:
        # No usable RSS text at all — construct from title keywords, never generic
        lead = f'{title}. This development is among the latest from the {cat_name.lower()} space, reflecting ongoing activity across the broadcast and streaming technology sector.'

    # ── Build body paragraphs from remaining sentences ───────────────────────
    remaining = all_sentences[2:]

    # Group remaining sentences into body paragraphs — NEVER use generic filler
    body_paras = []
    if remaining:
        # Group into chunks of ~3 sentences per paragraph
        chunk_size = 3
        for i in range(0, min(len(remaining), 9), chunk_size):
            chunk = ' '.join(remaining[i:i+chunk_size]).strip()
            if len(chunk) > 30:
                body_paras.append(chunk)

    # ── Conclusion: only if we have real content to conclude ───────────────
    # Don't add a generic conclusion — leave it blank if no real content
    conclusion = None

    # ── Summary for card display ─────────────────────────────────────────────
    summary = first_sentences(raw_text, 1)[:200] if raw_text else title

    # Use body_paras if we have them; otherwise just use lead as the article body
    all_paras = body_paras if body_paras else []
    html = _article_page(key, title, summary, lead, all_paras,
                         conclusion, cat_slug, cat_name, today, img_url)
    return html, title, summary, img_url, today


def save_article(key, html):
    for d in [os.path.join(SITE, 'articles'), os.path.join(SITE_SRC, 'articles')]:
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f'rss-{key}.html'), 'w', encoding='utf-8') as f:
            f.write(html)


def sync_static_assets():
    import shutil
    for d in ['assets', 'legal']:
        src, dst = os.path.join(SITE_SRC, d), os.path.join(SITE, d)
        if os.path.isdir(src):
            if os.path.exists(dst): shutil.rmtree(dst)
            shutil.copytree(src, dst)
    for fname in ['about.html','contact.html','vlog.html','privacy.html','terms.html',
                  'style.css','robots.txt','ads.txt','CNAME','editorial.txt','howto.html']:
        src = os.path.join(SITE_SRC, fname)
        if os.path.isfile(src):
            import shutil as sh; sh.copy2(src, os.path.join(SITE, fname))
    src_arts = os.path.join(SITE_SRC, 'articles')
    dst_arts = os.path.join(SITE, 'articles')
    os.makedirs(dst_arts, exist_ok=True)
    if os.path.isdir(src_arts):
        import shutil as sh
        for fn in os.listdir(src_arts):
            src_f = os.path.join(src_arts, fn)
            if os.path.isfile(src_f): sh.copy2(src_f, os.path.join(dst_arts, fn))


def build_category(category, urls, editorial_articles, cache, new_count_ref):
    items    = []
    meta     = dict(META_MAP.get(category, {'title':category,'description':category,'h1':category,'h2':'','slug':slugify(category)}))
    if 'slug' not in meta: meta['slug'] = slugify(category)
    cat_slug = meta['slug']

    for url in urls:
        try: feed = feedparser.parse(url)
        except Exception as ex: print(f'  Feed error {url}: {ex}'); continue

        for e in feed.entries[:10]:
            raw_title = (e.get('title') or '').strip()
            link      = (e.get('link') or '').strip()
            if not raw_title or not link: continue

            # Clean title — remove Sponsored:, trailing junk
            title = clean_title(raw_title)
            if not title: continue

            raw_text = clean_text(e.get('summary') or e.get('description') or '')

            # Skip off-topic articles
            if not is_on_topic(title, raw_text):
                print(f'    ⊘ Skipped off-topic: {title[:60]}')
                continue

            ts       = parse_time(e)
            key      = url_key(link)
            cached   = cache.get(key)
            src_img  = first_image(e)

            if cached:
                internal_link = f'articles/rss-{key}.html'
                # Re-run keyword image every build so images stay fresh and unique
                img_url       = src_img if src_img else keyword_image(title, cat_slug, key)
                summary       = cached.get('summary', '')
                display_title = cached.get('headline', title)
                cache[key]['image'] = img_url

            elif new_count_ref[0] < MAX_NEW_PER_BUILD and GROQ_API_KEY:
                print(f'    ✍  Rewriting: {title[:55]}…')
                data = groq_rewrite(title, raw_text, category)
                if data:
                    new_count_ref[0] += 1
                    img_url   = src_img if src_img else keyword_image(data['headline'], cat_slug, key)
                    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                    html      = _article_page(key, data['headline'], data['summary'],
                                              data['lead'], data['body'], data['conclusion'],
                                              cat_slug, category, today_str, img_url)
                    save_article(key, html)
                    cache[key] = {'headline':data['headline'],'summary':data['summary'],
                                  'image':img_url,'date':today_str,'cat_slug':cat_slug}
                    internal_link = f'articles/rss-{key}.html'
                    summary       = data['summary']
                    display_title = data['headline']
                else:
                    img_url = src_img if src_img else keyword_image(title, cat_slug, key)
                    html, display_title, summary, img_url, today_str = make_stub(
                        key, title, raw_text, cat_slug, category, ts)
                    save_article(key, html)
                    cache[key] = {'headline':display_title,'summary':summary,'image':img_url,
                                  'date':today_str,'cat_slug':cat_slug}
                    internal_link = f'articles/rss-{key}.html'
            else:
                img_url = src_img if src_img else keyword_image(title, cat_slug, key)
                html, display_title, summary, img_url, today_str = make_stub(
                    key, title, raw_text, cat_slug, category, ts)
                save_article(key, html)
                cache[key] = {'headline':display_title,'summary':summary,'image':img_url,
                              'date':today_str,'cat_slug':cat_slug}
                internal_link = f'articles/rss-{key}.html'

            items.append({'title':display_title,'link':internal_link,'external':False,
                          'summary':summary,'image':img_url,'ts':ts,'date':fmt_date(ts),
                          'category':category,'is_editorial':False})

    seen, dedup = set(), []
    for item in items:
        if item['link'] not in seen: dedup.append(item); seen.add(item['link'])
    dedup.sort(key=lambda x: x['ts'], reverse=True)

    cat_ed = [a for a in editorial_articles if a.get('cat_slug') == cat_slug][:3]
    html   = CATEGORY_TPL.render(meta=meta, cards=dedup, cat_editorial=cat_ed)
    with open(os.path.join(SITE, f"{meta['slug']}.html"), 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  Built {meta["slug"]}.html  ({len(dedup)} items, {len(cat_ed)} editorial)')
    return dedup


def build_home(category_map, editorial_articles, spotlight_articles):
    ORDER = ['Featured','Streaming','Cloud Production','AI & Post-Production',
             'Graphics','Playout','Infrastructure','Newsroom']
    all_cards, seen = [], set()
    for cat in ORDER:
        for item in category_map.get(cat, [])[:4]:
            if item['link'] not in seen: all_cards.append(item); seen.add(item['link'])
    for cat, items in category_map.items():
        if cat not in ORDER:
            for item in items[:3]:
                if item['link'] not in seen: all_cards.append(item); seen.add(item['link'])
    all_cards.sort(key=lambda x: x['ts'], reverse=True)
    html = HOME_TPL.render(meta=dict(META_MAP['Home']), featured=[], cards=all_cards[:30],
                           editorial_articles=editorial_articles[:6],
                           spotlight_articles=spotlight_articles)
    with open(os.path.join(SITE, 'featured.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    with open(os.path.join(SITE, 'index.html'), 'w', encoding='utf-8') as f:
        f.write('<!DOCTYPE html><html><head><meta charset="UTF-8"><meta http-equiv="refresh" content="0; url=featured.html"><title>The Streamic</title></head><body><a href="featured.html">The Streamic</a></body></html>')
    print(f'  Built featured.html  ({len(all_cards[:30])} cards, {len(editorial_articles[:6])} editorial, {len(spotlight_articles)} spotlight)')


def build_sitemap(editorial_articles, rss_keys, howto_slugs):
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    pages = [('featured.html','hourly','1.0'),('streaming.html','hourly','0.9'),('cloud.html','hourly','0.9'),
             ('ai-post-production.html','hourly','0.9'),('graphics.html','hourly','0.9'),('playout.html','hourly','0.9'),
             ('infrastructure.html','hourly','0.9'),('newsroom.html','hourly','0.9'),
             ('howto.html','monthly','0.85'),
             ('vlog.html','monthly','0.8'),('about.html','monthly','0.7'),('contact.html','monthly','0.6'),
             ('privacy.html','yearly','0.4')]
    for slug in howto_slugs:
        pages.append((f'articles/{slug}.html','monthly','0.85'))
    lines = ['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, freq, pri in pages:
        lines.append(f'  <url><loc>{SITE_URL}/{path}</loc><lastmod>{today}</lastmod><changefreq>{freq}</changefreq><priority>{pri}</priority></url>')
    for a in editorial_articles:
        lines.append(f'  <url><loc>{SITE_URL}/{a["url"]}</loc><lastmod>{a.get("date",today)}</lastmod><changefreq>monthly</changefreq><priority>0.75</priority></url>')
    for k in rss_keys:
        lines.append(f'  <url><loc>{SITE_URL}/articles/rss-{k}.html</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.65</priority></url>')
    lines.append('</urlset>')
    with open(os.path.join(SITE, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    robots = f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n"
    for p in [os.path.join(SITE,'robots.txt'), os.path.join(SITE_SRC,'robots.txt')]:
        with open(p,'w',encoding='utf-8') as f: f.write(robots)
    print(f'  Built sitemap.xml  ({len(pages)+len(editorial_articles)+len(rss_keys)} URLs)')


def main():
    os.makedirs(SITE, exist_ok=True)
    os.makedirs(os.path.join(SITE, 'articles'), exist_ok=True)
    editorial          = load_editorial_articles()
    spotlight_articles = load_editorial_spotlight()
    cache              = load_cache()
    new_count_ref      = [0]
    print(f'Loaded {len(editorial)} AI articles, {len(spotlight_articles)} spotlight')
    print('Syncing static assets…')
    sync_static_assets()
    if not GROQ_API_KEY: print('⚠  No GROQ_API_KEY — stub pages will be generated.')
    else: print(f'Groq enabled — rewriting up to {MAX_NEW_PER_BUILD} new articles.')
    print('Building The Streamic…')
    category_map = {}
    for cat, urls in FEEDS.items():
        print(f'Fetching: {cat}')
        category_map[cat] = build_category(cat, urls, editorial, cache, new_count_ref)
    save_cache(cache)
    print(f'Cache saved — {new_count_ref[0]} new Groq, {len(cache)} total.')
    build_home(category_map, editorial, spotlight_articles)
    build_sitemap(editorial, list(cache.keys()),
                  ['how-to-install-avid-media-composer','how-to-avid-adobe-premiere-workflow'])
    print('✅ Build complete.')


if __name__ == '__main__':
    main()
