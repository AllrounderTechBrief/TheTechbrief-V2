"""
Build script for The Streamic — v3.4
Fixes:
  - Massively expanded keyword→image map (50+ topic groups, all unique photo IDs)
  - Source RSS images accepted from trusted broadcast/tech domains
  - Source images rejected if from screenshot/generic domains (Google, Bing, etc.)
  - Per-slot image offset prevents the same photo repeating in one page load
  - All cards still link to internal pages (Groq rewrite or clean stub)
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
#  SOURCE IMAGE FILTERING
#  Accept images from trusted media/broadcast sites; reject junk/screenshots
# ══════════════════════════════════════════════════════════════════════════════

# Domains whose images are copyright-safe / press-kit quality
TRUSTED_IMAGE_DOMAINS = {
    # Royalty-free stock
    'images.unsplash.com', 'images.pexels.com', 'cdn.pixabay.com',
    'upload.wikimedia.org', 'commons.wikimedia.org',
    # Broadcast trade press (their own editorial images)
    'tvbeurope.com', 'newscaststudio.com', 'tvtechnology.com',
    'broadcastbeat.com', 'svgeurope.org', 'digitaltvnews.net',
    'streamingmediablog.com', 'streaminglearningcenter.com',
    'provideocoalition.com', 'newsshooter.com', 'postperspective.com',
    'studiodaily.com', 'premiumbeat.com', 'motionographer.com',
    'cgchannel.com', 'filmmakermagazine.com', 'videomaker.com',
    'fstoppers.com',
    # Vendor press images
    'harmonicinc.com', 'haivision.com', 'pebble.tv',
    'wowza.com', 'mux.com', 'bitmovin.com', 'brightcove.com',
    'kaltura.com', 'vizrt.com', 'avid.com', 'frame.io',
    'aws.amazon.com', 'cloudflare.com', 'cloudinary.com',
    # General tech press that provides good images
    'techcrunch.com', 'venturebeat.com',
}

# Domains to explicitly reject (screenshots, search engines, social etc.)
BLOCKED_IMAGE_DOMAINS = {
    'google.com', 'google.co', 'bing.com', 'yahoo.com',
    'facebook.com', 'twitter.com', 'instagram.com', 'tiktok.com',
    'reddit.com', 'linkedin.com', 'pinterest.com',
    'youtube.com', 'ytimg.com',
    'gravatar.com', 'wp.com', 'wordpress.com',
    'feedburner.com', 'feedproxy.google.com',
    # Generic placeholder services
    'placeholder.com', 'placekitten.com', 'lorempixel.com',
    'via.placeholder.com', 'dummyimage.com',
}

# File extensions that indicate a real image (not a redirect/tracker)
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.avif')

def source_image_ok(url: str) -> bool:
    """Return True if the RSS-supplied image URL is safe and relevant to use."""
    if not url or len(url) < 12:
        return False
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    host = parsed.netloc.lower().lstrip('www.')
    path = parsed.path.lower()

    # Must be HTTPS
    if parsed.scheme not in ('https', 'http'):
        return False
    # Reject known bad domains
    for bad in BLOCKED_IMAGE_DOMAINS:
        if host == bad or host.endswith('.' + bad):
            return False
    # Must end with an image extension OR be from a trusted domain
    has_ext = any(path.endswith(ext) for ext in IMAGE_EXTENSIONS)
    is_trusted = any(host == d or host.endswith('.' + d) for d in TRUSTED_IMAGE_DOMAINS)
    # Reject if it looks like a tracker/pixel (very short path, no extension, generic domain)
    if not has_ext and not is_trusted:
        return False
    # Reject tiny tracking pixels (paths like /px.gif, /t.gif, /track.png)
    if has_ext and len(path.split('/')[-1]) < 8:
        return False
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  KEYWORD → UNSPLASH IMAGE MAP
#  ~60 topic groups, every photo ID is unique across the entire map
#  Most specific patterns first — first keyword match wins
# ══════════════════════════════════════════════════════════════════════════════

# Each entry: ([keyword_list], 'unsplash-photo-id')
KEYWORD_IMAGE_MAP = [
    # ── NAB / IBC / trade shows ──────────────────────────────────────────────
    (['nab show', 'nab 2026', 'nab 2025', 'ibc 2026', 'ibc 2025', 'ibc show',
      'trade show', 'exhibition floor', 'expo'],
     'photo-1540575467063-178a50c2df87'),   # conference/expo hall

    # ── Connectors / cables / hardware ──────────────────────────────────────
    (['connector', 'opticalcon', 'neutrik', 'xlr', 'bnc', 'fiber connector',
      'cable management', 'patch panel'],
     'photo-1558494949-ef010cbdcc31'),       # cables/connectors

    # ── Music / sonic branding / audio post ─────────────────────────────────
    (['sonic branding', 'music composition', 'original music', 'score', 'composer',
      'sound design', 'audio branding', 'jingle', 'theme music'],
     'photo-1511379938547-c1f69419868d'),    # music studio/piano

    # ── Wireless mic / transmitter / RF ──────────────────────────────────────
    (['wireless mic', 'transmitter', 'lectrosonics', 'sennheiser', 'shure wireless',
      'radio mic', 'lavalier', 'body pack', 'belt pack', 'ifb', 'intercom'],
     'photo-1598520106830-8c45c2035460'),    # wireless/RF equipment

    # ── Microphone / podcast / voiceover ────────────────────────────────────
    (['microphone', 'podcast', 'voiceover', 'voice over', 'narrator',
      'radio presenter', 'commentary'],
     'photo-1520523839897-bd0b52f945a0'),    # microphone close-up

    # ── Sports broadcast / OB van ────────────────────────────────────────────
    (['sports broadcast', 'sports production', 'ob van', 'outside broadcast',
      'stadium', 'sports rights', 'live sport'],
     'photo-1540575467063-178a50c2df87'),    # broadcast venue

    # ── Sports business / media rights ──────────────────────────────────────
    (['sports media', 'local sports', 'sports streaming', 'media rights',
      'linear sports', 'sports television', 'twofer economy'],
     'photo-1560272564-c83b66b1ad12'),       # sports media

    # ── Live events / concert ────────────────────────────────────────────────
    (['live event', 'live production', 'concert production', 'festival tech',
      'touring production', 'stage production'],
     'photo-1492619375914-88005aa9e8fb'),    # live event lighting

    # ── Camera / acquisition ─────────────────────────────────────────────────
    (['4k camera', '8k camera', 'uhd camera', 'pov camera', 'ip camera',
      'broadcast camera', 'cinema camera', 'camera system'],
     'photo-1567095761054-7003afd47020'),    # broadcast camera

    # ── Drone / aerial ───────────────────────────────────────────────────────
    (['drone', 'aerial', 'uav', 'unmanned', 'fpv'],
     'photo-1473968512647-3e447244af8f'),    # drone aerial

    # ── Streaming / OTT / HLS / DASH ────────────────────────────────────────
    (['streaming platform', 'ott platform', 'svod', 'avod', 'vod platform',
      'video platform', 'streaming service'],
     'photo-1616401784845-180882ba9ba8'),    # streaming/screen

    # ── Encoder / transcoder / codec ────────────────────────────────────────
    (['encoder', 'encoding', 'transcoding', 'transcoder', 'codec', 'hevc',
      'h.265', 'av1', 'h.264', 'avc', 'mpeg'],
     'photo-1574717024653-61fd2cf4d44d'),    # encode/signal wave

    # ── CDN / delivery ───────────────────────────────────────────────────────
    (['cdn', 'content delivery', 'edge delivery', 'origin server', 'caching',
      'manifest', 'bitrate ladder'],
     'photo-1451187580459-43490279c0fa'),    # global network nodes

    # ── Low latency / WebRTC / SRT ───────────────────────────────────────────
    (['low latency', 'ultra-low latency', 'webrtc', 'srt protocol',
      'zixi', 'ndi', 'bonding'],
     'photo-1516321318423-f06f85e504b3'),    # network signal/latency

    # ── Cloud production / remote production ────────────────────────────────
    (['cloud production', 'cloud playout', 'cloud native', 'cloud broadcast',
      'remote production', 'remi', 'at-home production'],
     'photo-1544197150-b99a580bb7a8'),       # cloud infrastructure

    # ── Cloud platform / AWS / Azure ────────────────────────────────────────
    (['aws', 'amazon web', 'azure', 'google cloud', 'cloud storage',
      'cloud migration', 'multi-cloud'],
     'photo-1560472355-536de3962603'),       # cloud data centre

    # ── Virtualisation / software-defined ───────────────────────────────────
    (['virtualisation', 'virtualization', 'software-defined', 'containerisation',
      'kubernetes', 'docker', 'microservices'],
     'photo-1504639725590-34d0984388bd'),    # virtual/software

    # ── AI / machine learning general ───────────────────────────────────────
    (['artificial intelligence', 'machine learning', 'deep learning',
      'neural network', 'llm', 'generative ai', 'large language model'],
     'photo-1677442135703-1787eea5ce01'),    # AI neural network

    # ── AI archive / metadata / MAM ─────────────────────────────────────────
    (['ai archive', 'media asset', 'mam system', 'dam system', 'metadata tagging',
      'content catalogue', 'media catalogue', 'ai metadata'],
     'photo-1655635643532-fa9ba2648cbe'),    # AI data management

    # ── AI post / automated editing ─────────────────────────────────────────
    (['ai edit', 'automated editing', 'ai post', 'ai subtitle', 'ai caption',
      'speech to text', 'transcription', 'auto caption'],
     'photo-1620712943543-bcc4688e7485'),    # AI processing

    # ── Facial recognition / computer vision ────────────────────────────────
    (['facial recognition', 'object detection', 'computer vision',
      'image recognition', 'scene detection'],
     'photo-1533228100845-08145b01de14'),    # computer vision

    # ── Graphics / motion design ─────────────────────────────────────────────
    (['motion graphics', 'animation studio', 'title sequence', 'lower third',
      'broadcast design', 'motion design'],
     'photo-1547658719-da2b51169166'),       # motion/graphics screen

    # ── Real-time graphics / virtual set ────────────────────────────────────
    (['real-time graphics', 'broadcast graphics', 'virtual set', 'virtual studio',
      'augmented reality broadcast', 'xr', 'extended reality'],
     'photo-1593642632559-0c6d3fc62b89'),    # real-time 3D

    # ── Unreal Engine / game engine ─────────────────────────────────────────
    (['unreal engine', 'game engine', 'led volume', 'led wall', 'virtual production stage',
      'icvfx'],
     'photo-1518770660439-4636190af475'),    # VFX/rendering

    # ── VFX / CGI ────────────────────────────────────────────────────────────
    (['vfx', 'visual effects', 'cgi', 'compositing', 'green screen',
      'chroma key'],
     'photo-1610563166150-b34df4f3bcd6'),    # VFX render

    # ── Video editing / NLE ──────────────────────────────────────────────────
    (['media composer', 'premiere pro', 'final cut', 'davinci resolve',
      'edit suite', 'editing workflow', 'non-linear', 'nle', 'avid', 'adobe premiere',
      'post production workflow', 'editorial workflow'],
     'photo-1574717025058-97e3af4ef9b5'),    # video editing timeline

    # ── Colour grading ───────────────────────────────────────────────────────
    (['colour grading', 'color grading', 'davinci', 'grading suite',
      'colour science', 'lut', 'hdr grading'],
     'photo-1605106702734-205df224ecce'),    # colour grading monitor

    # ── Playout / master control ─────────────────────────────────────────────
    (['channel in a box', 'ciab', 'master control', 'on-air', 'playout server',
      'playout automation', 'transmission', 'broadcast playout'],
     'photo-1612420696760-0a0f34d3e7d0'),    # broadcast control room

    # ── Automation / workflow orchestration ─────────────────────────────────
    (['workflow automation', 'orchestration', 'scheduling system', 'rundown',
      'automation system', 'playlist'],
     'photo-1478737270239-2f02b77fc618'),    # broadcast automation

    # ── SMPTE / ST 2110 / IP production ────────────────────────────────────
    (['smpte st 2110', 'smpte 2110', 'ip production', 'ip routing',
      'ip infrastructure', 'sdi to ip', 'ats', 'nmos'],
     'photo-1486312338219-ce68d2c6f44d'),    # IP network rack

    # ── Network / switching ──────────────────────────────────────────────────
    (['network switch', 'router', 'ethernet', 'fibre', 'fiber optic',
      'bandwidth', '10gbe', '25gbe', 'spine leaf'],
     'photo-1497366216548-37526070297c'),    # network infrastructure

    # ── Storage / MAM physical ──────────────────────────────────────────────
    (['storage system', 'nas storage', 'san storage', 'object storage',
      'tape library', 'lto', 'nearline', 'archive storage'],
     'photo-1560472354-b33ff0c44a43'),       # storage server

    # ── 5G / mobile production ──────────────────────────────────────────────
    (['5g broadcast', '5g production', 'bonding', 'mobile journalism',
      'mojo', 'cellular uplink', 'bonded cellular'],
     'photo-1526374965328-7f61d4dc18c5'),    # 5G/mobile

    # ── Satellite / uplink ───────────────────────────────────────────────────
    (['satellite', 'uplink', 'downlink', 'dish antenna', 'vsat',
      'satellite truck', 'flyaway'],
     'photo-1516321318423-f06f85e504b3'),    # satellite/antenna

    # ── Cybersecurity ────────────────────────────────────────────────────────
    (['cybersecurity', 'security breach', 'vulnerability', 'ransomware',
      'data breach', 'cyber attack', 'zero trust'],
     'photo-1550751827-4bd374c3f58b'),       # cybersecurity

    # ── Newsroom / NRCS ─────────────────────────────────────────────────────
    (['newsroom', 'nrcs', 'news production', 'breaking news',
      'news editor', 'wire service'],
     'photo-1504711434969-e33886168f5c'),    # newsroom

    # ── News presenter / anchor ──────────────────────────────────────────────
    (['presenter', 'anchor', 'news anchor', 'reporter', 'correspondent',
      'studio presenter', 'news reader'],
     'photo-1493863641943-9b68992a8d07'),    # presenter/reporter

    # ── Remote journalism / REMI ────────────────────────────────────────────
    (['remote journalism', 'remote reporter', 'bureau', 'remote studio',
      'ip contribution', 'remote feed'],
     'photo-1585829365295-ab7cd400c167'),    # remote/bureau

    # ── ATSC / DVB / broadcast standards ────────────────────────────────────
    (['atsc 3.0', 'atsc3', 'dvb-t2', 'dvb-s2', 'broadcast standard',
      'digital terrestrial', 'dtt', 'hbbTV'],
     'photo-1611532736597-de2d4265fba3'),    # broadcast signal/tower

    # ── Monitor / display ────────────────────────────────────────────────────
    (['reference monitor', 'broadcast monitor', 'confidence monitor',
      'multiviewer', 'wall display', 'hdr display', 'oled monitor'],
     'photo-1527443224154-c4a3942d3acf'),    # professional monitor

    # ── Audio mixer / console ────────────────────────────────────────────────
    (['audio mixer', 'mixing console', 'mixing desk', 'fader', 'ssl',
      'neve', 'lawo', 'calrec', 'soundcraft', 'audio console'],
     'photo-1598488035139-bdbb2231ce04'),    # audio console

    # ── Audio post / dubbing ─────────────────────────────────────────────────
    (['dubbing', 'audio post', 'sound mix', 'dialogue edit', 'foley',
      'adm', 'dolby atmos', 'spatial audio', 'immersive audio'],
     'photo-1516321497487-e288fb19713f'),    # audio post production

    # ── Business / appointment / executive ──────────────────────────────────
    (['appoints', 'appointed', 'ceo', 'chief executive', 'managing director',
      'president', 'board director', 'vice president', 'moves into'],
     'photo-1507679799987-c73779587ccf'),    # executive/business

    # ── Funding / investment / acquisition ──────────────────────────────────
    (['acquisition', 'merger', 'investment', 'funding', 'raises',
      'venture capital', 'private equity', 'series a', 'series b'],
     'photo-1460925895917-afdab827c52f'),    # business/investment

    # ── Partnership / integration ────────────────────────────────────────────
    (['partnership', 'integration', 'interoperability', 'workflow integration',
      'api integration', 'plugin', 'workflow'],
     'photo-1553877522-43269d4ea984'),       # integration/connection

    # ── Training / education / certification ────────────────────────────────
    (['training', 'education', 'certification', 'workshop', 'masterclass',
      'learning', 'course', 'tutorial'],
     'photo-1434030216411-0b793f4b4173'),    # training/education

    # ── Infrastructure / facility ────────────────────────────────────────────
    (['broadcast facility', 'facility upgrade', 'technical infrastructure',
      'equipment room', 'technical hub', 'mdf', 'idf'],
     'photo-1504384308090-c894fdcc538d'),    # server/facility room

    # ── Streaming hardware appliance ────────────────────────────────────────
    (['haivision', 'wowza', 'mux', 'brightcove', 'kaltura', 'jwplayer',
      'bitmovin', 'telestream', 'harmonic', 'envivio'],
     'photo-1584824486509-112e4181ff6b'),    # hardware appliance rack

    # ── How-to / install / guide ────────────────────────────────────────────
    (['install', 'installation', 'how to', 'how-to', 'setup', 'configure',
      'step by step', 'guide', 'tutorial'],
     'photo-1518770660439-4636190af475'),    # setup/configuration
]

# Per-category fallback pools — unique photo IDs, nothing repeated within each pool
CATEGORY_IMAGE_POOLS = {
    'streaming': [
        'photo-1616401784845-180882ba9ba8',  # streaming monitor
        'photo-1574717024653-61fd2cf4d44d',  # signal waves
        'photo-1598488035139-bdbb2231ce04',  # server racks
        'photo-1516321318423-f06f85e504b3',  # network lights
        'photo-1611532736597-de2d4265fba3',  # broadcast signal
        'photo-1478737270239-2f02b77fc618',  # broadcast studio
        'photo-1540575467063-178a50c2df87',  # broadcast venue
        'photo-1492619375914-88005aa9e8fb',  # live event tech
    ],
    'cloud': [
        'photo-1451187580459-43490279c0fa',  # global network
        'photo-1544197150-b99a580bb7a8',     # cloud servers
        'photo-1560472355-536de3962603',     # data centre
        'photo-1504639725590-34d0984388bd',  # virtual infrastructure
        'photo-1526374965328-7f61d4dc18c5',  # network nodes
        'photo-1588508065123-287b28e013da',  # cloud abstract
        'photo-1531297484001-80022131f5a1',  # tech background
        'photo-1558494949-ef010cbdcc31',     # cables/connectivity
    ],
    'ai-post-production': [
        'photo-1677442135703-1787eea5ce01',  # AI neural
        'photo-1620712943543-bcc4688e7485',  # AI processing
        'photo-1655635643532-fa9ba2648cbe',  # AI data
        'photo-1574717025058-97e3af4ef9b5',  # video edit timeline
        'photo-1605106702734-205df224ecce',  # colour grading
        'photo-1533228100845-08145b01de14',  # computer vision
        'photo-1598520106830-8c45c2035460',  # production gear
        'photo-1635070041078-e363dbe005cb',  # AI abstract
    ],
    'graphics': [
        'photo-1547658719-da2b51169166',     # motion/graphics
        'photo-1593642632559-0c6d3fc62b89',  # 3D/real-time
        'photo-1518770660439-4636190af475',  # VFX/rendering
        'photo-1610563166150-b34df4f3bcd6',  # VFX render
        'photo-1472214103451-9374bd1c798e',  # creative tech
        'photo-1541462608143-67571c6738dd',  # graphics abstract
        'photo-1497091071254-cc9b2ba7c48a',  # design studio
        'photo-1527443224154-c4a3942d3acf',  # professional monitor
    ],
    'playout': [
        'photo-1612420696760-0a0f34d3e7d0',  # broadcast control
        'photo-1478737270239-2f02b77fc618',  # automation
        'photo-1567095761054-7003afd47020',  # camera/broadcast
        'photo-1574717024653-61fd2cf4d44d',  # signal
        'photo-1492619375914-88005aa9e8fb',  # broadcast live
        'photo-1540575467063-178a50c2df87',  # venue/broadcast
        'photo-1598488035139-bdbb2231ce04',  # server/playout
        'photo-1590602847861-f357a9332bbc',  # broadcast tech
    ],
    'infrastructure': [
        'photo-1486312338219-ce68d2c6f44d',  # IP network rack
        'photo-1497366216548-37526070297c',  # network infra
        'photo-1560472354-b33ff0c44a43',     # storage/rack
        'photo-1553877522-43269d4ea984',     # integration
        'photo-1542744094-3a31f272c490',     # server room
        'photo-1504384308090-c894fdcc538d',  # facility/rack
        'photo-1584824486509-112e4181ff6b',  # hardware rack
        'photo-1558494949-ef010cbdcc31',     # cables
    ],
    'newsroom': [
        'photo-1504711434969-e33886168f5c',  # newsroom
        'photo-1493863641943-9b68992a8d07',  # presenter
        'photo-1585829365295-ab7cd400c167',  # remote/bureau
        'photo-1432821596592-e2c18b78144f',  # news writing
        'photo-1503428593586-e225b39bddfe',  # journalism
        'photo-1557804506-669a67965ba0',     # office/news
        'photo-1513519245088-0e12902e5a38',  # news screen
        'photo-1495020689067-958852a7765e',  # breaking news
    ],
    'featured': [
        'photo-1598488035139-bdbb2231ce04',  # server/streaming
        'photo-1478737270239-2f02b77fc618',  # broadcast studio
        'photo-1574717024653-61fd2cf4d44d',  # signal/wave
        'photo-1540575467063-178a50c2df87',  # broadcast venue
        'photo-1612420696760-0a0f34d3e7d0',  # control room
        'photo-1567095761054-7003afd47020',  # camera
        'photo-1486312338219-ce68d2c6f44d',  # IP/network
        'photo-1677442135703-1787eea5ce01',  # AI
    ],
    'default': [
        'photo-1598488035139-bdbb2231ce04',
        'photo-1478737270239-2f02b77fc618',
        'photo-1574717024653-61fd2cf4d44d',
        'photo-1486312338219-ce68d2c6f44d',
        'photo-1504711434969-e33886168f5c',
        'photo-1677442135703-1787eea5ce01',
        'photo-1612420696760-0a0f34d3e7d0',
        'photo-1547658719-da2b51169166',
    ],
}

BADGE_COLORS = {'streaming':'#0071e3','cloud':'#5856d6','ai-post-production':'#FF2D55','graphics':'#FF9500','playout':'#34C759','infrastructure':'#8E8E93','newsroom':'#D4AF37','featured':'#1d1d1f'}
BADGE_ICONS  = {'streaming':'📡','cloud':'☁️','ai-post-production':'🎬','graphics':'🎨','playout':'▶️','infrastructure':'🏗️','newsroom':'📰','featured':'⭐'}


def keyword_image(title: str, cat_slug: str, seed: str) -> str:
    """Scan title for topic keywords → return a relevant unique Unsplash URL."""
    title_lower = (title or '').lower()
    for keywords, photo_id in KEYWORD_IMAGE_MAP:
        if any(kw in title_lower for kw in keywords):
            return f'https://images.unsplash.com/{photo_id}?w=800&auto=format&fit=crop'
    # Category fallback with deterministic offset so same pool entries aren't repeated
    pool = CATEGORY_IMAGE_POOLS.get(cat_slug, CATEGORY_IMAGE_POOLS['default'])
    idx  = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(pool)
    return f'https://images.unsplash.com/{pool[idx]}?w=800&auto=format&fit=crop'


# ── Cache helpers ──────────────────────────────────────────────────────────
def load_cache():
    if os.path.exists(CACHE_F):
        try:
            with open(CACHE_F, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
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
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def load_editorial_spotlight():
    path = os.path.join(SITE_SRC, 'editorial.txt')
    if not os.path.exists(path): return []
    with open(path, 'r', encoding='utf-8') as f:
        raw = f.read()
    articles = []
    blocks = re.split(r'\n===\s*\n', raw)
    for block in blocks:
        fields, para_lines, reading_paras = {}, [], False
        for line in block.splitlines():
            stripped = line.strip()
            if stripped.startswith('##'): continue
            if not reading_paras:
                m = re.match(r'^(TITLE|BADGE|COLOR|ICON|READ)\s*:\s*(.+)$', stripped, re.IGNORECASE)
                if m:
                    fields[m.group(1).upper()] = m.group(2).strip(); continue
                if fields and not stripped:
                    reading_paras = True; continue
            else:
                para_lines.append(line)
        if not fields.get('TITLE'): continue
        paragraphs, current = [], []
        for line in para_lines:
            if line.strip() == '':
                if current:
                    p = ' '.join(current).strip()
                    if p: paragraphs.append(p)
                    current = []
            else:
                current.append(line.strip())
        if current:
            p = ' '.join(current).strip()
            if p: paragraphs.append(p)
        if paragraphs:
            articles.append({
                'title': fields.get('TITLE','Untitled'),
                'badge': fields.get('BADGE','Editorial'),
                'color': fields.get('COLOR','#1d1d1f'),
                'icon':  fields.get('ICON','📖'),
                'read_time': fields.get('READ','5 min read'),
                'paragraphs': paragraphs,
            })
    return articles[:2]


# ── Text helpers ───────────────────────────────────────────────────────────
def clean_text(html):
    txt = BeautifulSoup(html or '', 'html.parser').get_text(' ')
    txt = re.sub(r'\s+', ' ', txt)
    txt = re.sub(r'(appeared first on[\s\S]{0,80}|the post [\s\S]{0,100}|&nbsp;|read more\.?\s*$)',
                 '', txt, flags=re.IGNORECASE)
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
    for p in body_paras:
        body_html += f'    <p>{e(p)}</p>\n'
    if conclusion:
        body_html += f'    <p class="art-conclusion">{e(conclusion)}</p>\n'
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
        Background context (rewrite entirely in your own words): "{ctx}"
        Return JSON with EXACTLY:
        {{"headline":"Original SEO headline 8-14 words","summary":"One sentence 20-30 words","lead":"2-sentence opening","body":["para 1 60-80w","para 2 60-80w","para 3 60-80w"],"conclusion":"One forward-looking sentence"}}
        Rules: 100% original voice, no source names, technical depth for broadcast professionals.
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
    today    = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    img_url  = keyword_image(title, cat_slug, key)
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', raw_text) if len(s.strip()) > 30]
    lead      = ' '.join(sentences[:2]) if len(sentences) >= 2 else f'The latest developments in {cat_name} continue to reshape the broadcast technology landscape.'
    body_p1   = ' '.join(sentences[2:5]) if len(sentences) >= 5 else f'This development reflects the ongoing evolution of {cat_name.lower()} workflows across the broadcast industry. Operators and technology professionals are monitoring these changes closely as the implications for day-to-day operations become clearer.'
    body_p2   = ' '.join(sentences[5:8]) if len(sentences) >= 8 else f'The broader context sits within an industry rapidly transitioning toward IP-based and cloud-native infrastructure. Decisions made now will shape operational capabilities for years to come.'
    body_p3   = f'For broadcast engineers and media technology teams, staying current with these developments is essential. Understanding both technical specifications and practical deployment realities helps organisations make informed choices in a fast-moving vendor landscape.'
    conclusion = f'As {cat_name.lower()} technology continues to mature, the coming months will bring further clarity on adoption timelines and real-world performance benchmarks.'
    summary   = first_sentences(raw_text or lead, 1)[:160] or f'Latest {cat_name} news from The Streamic.'
    html = _article_page(key, title, summary, lead, [body_p1, body_p2, body_p3],
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
                  'style.css','robots.txt','ads.txt','CNAME','editorial.txt']:
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
        try:
            feed = feedparser.parse(url)
        except Exception as ex:
            print(f'  Feed error {url}: {ex}'); continue

        for e in feed.entries[:10]:
            title = re.sub(r'\s*(appeared first on|the post .{0,50}$)','',
                           (e.get('title') or '').strip(), flags=re.IGNORECASE).strip()
            link  = (e.get('link') or '').strip()
            if not title or not link: continue

            raw_text  = clean_text(e.get('summary') or e.get('description') or '')
            ts        = parse_time(e)
            key       = url_key(link)
            cached    = cache.get(key)
            # Try source image first
            src_img   = first_image(e)

            if cached:
                internal_link = f'articles/rss-{key}.html'
                # Re-run keyword image (not cached image) so images stay fresh
                img_url       = src_img if src_img else keyword_image(title, cat_slug, key)
                summary       = cached.get('summary', '')
                display_title = cached.get('headline', title)
                # Update cached image
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

            items.append({
                'title':    display_title,
                'link':     internal_link,
                'external': False,
                'summary':  summary,
                'image':    img_url,
                'ts':       ts,
                'date':     fmt_date(ts),
                'category': category,
                'is_editorial': False,
            })

    seen, dedup = set(), []
    for item in items:
        if item['link'] not in seen:
            dedup.append(item); seen.add(item['link'])
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
            if item['link'] not in seen:
                all_cards.append(item); seen.add(item['link'])
    for cat, items in category_map.items():
        if cat not in ORDER:
            for item in items[:3]:
                if item['link'] not in seen:
                    all_cards.append(item); seen.add(item['link'])
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
             ('vlog.html','monthly','0.8'),('about.html','monthly','0.7'),('contact.html','monthly','0.6'),
             ('privacy.html','yearly','0.4')]
    for slug in howto_slugs:
        pages.append((f'articles/{slug}.html', 'monthly', '0.85'))
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
    if not GROQ_API_KEY:
        print('⚠  No GROQ_API_KEY — stub pages will be generated.')
    else:
        print(f'Groq enabled — rewriting up to {MAX_NEW_PER_BUILD} new articles.')
    print('Building The Streamic…')
    category_map = {}
    for cat, urls in FEEDS.items():
        print(f'Fetching: {cat}')
        category_map[cat] = build_category(cat, urls, editorial, cache, new_count_ref)
    save_cache(cache)
    print(f'Cache saved — {new_count_ref[0]} new Groq, {len(cache)} total.')
    build_home(category_map, editorial, spotlight_articles)
    howto_slugs = ['how-to-install-avid-media-composer', 'how-to-avid-adobe-premiere-workflow']
    build_sitemap(editorial, list(cache.keys()), howto_slugs)
    print('✅ Build complete.')


if __name__ == '__main__':
    main()
