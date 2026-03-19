#!/usr/bin/env python3
"""
generate_articles.py — The Tech Brief
Daily AI-authored original article generator using Groq Llama 3.

• Generates 1 long-form original article per category (9 articles/day)
• Each article: 700–900 words, editorial structure with H2 subheadings
• Saves full styled HTML → site/articles/YYYY-MM-DD-{catslug}.html
• Syncs metadata → data/generated_articles.json (homepage + category injection)
• Auto-updates site/assets/data/trending.txt with latest headlines
• Skips categories that already have today's article (idempotent — safe to re-run)

Usage:
    GROQ_API_KEY=your_key python scripts/generate_articles.py

GitHub Actions: secret is injected automatically via ${{ secrets.GROQ_API_KEY }}
"""

import os
import re
import sys
import json
import time
import random
import textwrap
import feedparser
import requests
from datetime import datetime, timezone
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────
ROOT         = Path(__file__).resolve().parent.parent
SITE_DIR     = ROOT / "site" / "articles"
DATA_DIR     = ROOT / "data"
TRENDING_TXT = ROOT / "site" / "assets" / "data" / "trending.txt"
ARTICLES_JSON = DATA_DIR / "generated_articles.json"

# ─── Config ───────────────────────────────────────────────────────────────────
GROQ_API_KEY  = os.environ.get("GROQ_API_KEY", "")
GROQ_URL      = "https://api.groq.com/openai/v1/chat/completions"
# 70B: best quality, still fast on Groq
model = "llama-3.3-70b-versatile"
# or, for cheaper/faster runs:
# model = "llama-3.1-8b-instant"
SITE_URL      = "https://www.thetechbrief.net"
GA_TAG        = "G-YCJEGDPW7G"
AUTHOR        = "The Tech Brief Editorial Team"
MAX_STORED    = 60  # Maximum articles to keep in generated_articles.json

# ─── Category definitions ─────────────────────────────────────────────────────
CATEGORIES = [
    {
        "name": "AI News",
        "slug": "ai-news",
        "page": "ai-news.html",
        "badge_color": "#7C3AED",
        "icon": "🤖",
        "feeds": [
            "https://techcrunch.com/tag/ai/feed/",
            "https://venturebeat.com/category/ai/feed/",
            "https://www.theverge.com/rss/artificial-intelligence/index.xml",
        ],
        "topics_fallback": [
            "The evolution of large language models in enterprise software",
            "How AI coding assistants are changing software development",
            "Autonomous AI agents and their impact on business workflows",
            "The AI chip war: NVIDIA, AMD, and custom silicon",
            "Open-source vs closed AI models: the 2025 landscape",
        ],
    },
    {
        "name": "Cybersecurity Updates",
        "slug": "cybersecurity-updates",
        "page": "cybersecurity-updates.html",
        "badge_color": "#DC2626",
        "icon": "🔐",
        "feeds": [
            "https://www.csoonline.com/index.rss",
            "https://www.darkreading.com/rss.xml",
            "https://feeds.feedburner.com/TheHackersNews",
        ],
        "topics_fallback": [
            "Why phishing attacks are harder to detect than ever",
            "Zero-trust architecture: what enterprises are actually doing",
            "The rise of AI-powered cyberattacks",
            "Cloud misconfigurations: the most common breach vector",
            "Ransomware payments and the policy debate around them",
        ],
    },
    {
        "name": "Mobile & Gadgets",
        "slug": "mobile-gadgets",
        "page": "mobile-gadgets.html",
        "badge_color": "#0891B2",
        "icon": "📱",
        "feeds": [
            "https://www.theverge.com/rss/gadgets/index.xml",
            "https://www.engadget.com/rss.xml",
            "https://www.androidauthority.com/feed/",
        ],
        "topics_fallback": [
            "On-device AI features that are actually useful in 2025",
            "The battle for foldable phone dominance",
            "Why flagship smartphone cameras have hit a plateau",
            "Wearables beyond the wrist: AR glasses go mainstream",
            "The death of the headphone jack and what replaced it",
        ],
    },
    {
        "name": "EVs & Automotive",
        "slug": "evs-automotive",
        "page": "evs-automotive.html",
        "badge_color": "#059669",
        "icon": "🚗",
        "feeds": [
            "https://electrek.co/feed/",
            "https://insideevs.com/feed/",
            "https://techcrunch.com/category/transportation/feed/",
        ],
        "topics_fallback": [
            "Solid-state batteries: where the technology actually stands",
            "The charging infrastructure gap slowing EV adoption",
            "Software-defined vehicles and the OTA update revolution",
            "How autonomous driving technology is reshaping car insurance",
            "EV affordability: the race to the sub-$30,000 electric car",
        ],
    },
    {
        "name": "Startups & Business",
        "slug": "startups-business",
        "page": "startups-business.html",
        "badge_color": "#D97706",
        "icon": "💼",
        "feeds": [
            "https://techcrunch.com/feed/",
            "https://venturebeat.com/feed/",
            "https://news.crunchbase.com/feed/",
        ],
        "topics_fallback": [
            "How AI startups are navigating a more selective funding environment",
            "The second wave of B2B SaaS consolidation",
            "Why founder-led sales is making a comeback in enterprise tech",
            "Tech IPO market outlook and what investors are watching",
            "The rise of vertical AI: industry-specific models and startups",
        ],
    },
    {
        "name": "Enterprise Tech",
        "slug": "enterprise-tech",
        "page": "enterprise-tech.html",
        "badge_color": "#2563EB",
        "icon": "🏢",
        "feeds": [
            "https://www.zdnet.com/topic/enterprise/rss.xml",
            "https://www.infoworld.com/category/enterprise-it/index.rss",
            "https://siliconangle.com/feed/",
        ],
        "topics_fallback": [
            "Cloud cost optimization: what enterprises are actually doing",
            "The hybrid cloud reality for large enterprises in 2025",
            "How CIOs are managing AI governance and risk",
            "Kubernetes at scale: lessons from five years of production use",
            "The rise of the AI-native data warehouse",
        ],
    },
    {
        "name": "Gaming",
        "slug": "gaming",
        "page": "gaming.html",
        "badge_color": "#7C3AED",
        "icon": "🎮",
        "feeds": [
            "https://kotaku.com/rss",
            "https://www.eurogamer.net/?format=rss",
            "https://www.polygon.com/rss/index.xml",
        ],
        "topics_fallback": [
            "The business model evolution of live-service games",
            "How generative AI is changing game development pipelines",
            "The handheld gaming PC renaissance and what it signals",
            "Subscription gaming fatigue and what publishers are doing about it",
            "The return of single-player narrative games",
        ],
    },
    {
        "name": "Consumer Tech",
        "slug": "consumer-tech",
        "page": "consumer-tech.html",
        "badge_color": "#0891B2",
        "icon": "🛒",
        "feeds": [
            "https://www.cnet.com/rss/all/",
            "https://www.techradar.com/rss",
            "https://www.tomsguide.com/feeds/all",
        ],
        "topics_fallback": [
            "The smart home interoperability problem is finally being solved",
            "Why laptop battery life has dramatically improved",
            "Noise-cancelling headphones: the science and the marketing",
            "The new generation of ultra-portable monitors",
            "Budget flagship phones: the spec-gap is almost gone",
        ],
    },
    {
        "name": "Broadcast Tech",
        "slug": "broadcast-tech",
        "page": "broadcast-tech.html",
        "badge_color": "#BE185D",
        "icon": "📡",
        "feeds": [
            "https://www.tvbeurope.com/feed",
            "https://www.newscaststudio.com/feed/",
            "https://aws.amazon.com/blogs/media/category/media-entertainment/feed/",
        ],
        "topics_fallback": [
            "IP migration in broadcast: the transition timeline realities",
            "How streaming platforms are changing live sports production",
            "AI-assisted editing and its impact on post-production workflows",
            "The role of cloud rendering in modern broadcast operations",
            "ATSC 3.0 rollout and what it means for broadcasters",
        ],
    },
]


# ─── Unsplash image pools (one per category for AdSense-safe visuals) ─────────
CATEGORY_IMAGE_POOLS = {
    "ai-news":               ["photo-1677442135703-1787eea5ce01","photo-1620712943543-bcc4688e7485","photo-1655635643532-fa9ba2648cbe","photo-1533228100845-08145b01de14","photo-1558494949-ef010cbdcc31","photo-1635070041078-e363dbe005cb"],
    "cybersecurity-updates": ["photo-1550751827-4bd374c3f58b","photo-1563986768609-322da13575f3","photo-1614064641938-3bbee52942c7","photo-1510511233900-1982d92bd835","photo-1555949963-aa79dcee981c","photo-1504384308090-c894fdcc538d"],
    "mobile-gadgets":        ["photo-1511707171634-5f897ff02aa9","photo-1592750475338-74b7b21085ab","photo-1585060544812-6b45742d762f","photo-1523206489230-c012c64b2b48","photo-1567581935884-3349723552ca","photo-1542751371-adc38448a05e"],
    "evs-automotive":        ["photo-1593941707882-a5bba14938c7","photo-1558618666-fcd25c85cd64","photo-1616455579100-2ceaa4eb2d37","photo-1549317661-bd32c8ce0db2","photo-1580274455191-1c62238fa1f4","photo-1617469767053-d3b523a0b982"],
    "startups-business":     ["photo-1559136555-9303baea8ebd","photo-1507003211169-0a1dd7228f2d","photo-1450101499163-c8848c66ca85","photo-1460925895917-afdab827c52f","photo-1553484771-371a605b060b","photo-1579532537598-459ecdaf39cc"],
    "enterprise-tech":       ["photo-1486312338219-ce68d2c6f44d","photo-1497366216548-37526070297c","photo-1568952433726-3896e3881c65","photo-1542744094-3a31f272c490","photo-1521737711867-e3b97375f902","photo-1454165804606-c3d57bc86b40"],
    "gaming":                ["photo-1538481199705-c710c4e965fc","photo-1493711662062-fa541adb3fc8","photo-1552820728-8b83bb6b773f","photo-1601887389937-0b02f7683064","photo-1612287230202-1ff1d85d1bdf","photo-1574375927938-d5a98e8ffe85"],
    "consumer-tech":         ["photo-1498049794561-7780e7231661","photo-1517694712202-14dd9538aa97","photo-1593642632559-0c6d3fc62b89","photo-1519389950473-47ba0277781c","photo-1496181133206-80ce9b88a853","photo-1550009158-9ebf69173e03"],
    "broadcast-tech":        ["photo-1478737270239-2f02b77fc618","photo-1612420696760-0a0f34d3e7d0","photo-1567095761054-7003afd47020","photo-1598488035139-bdbb2231ce04","photo-1516321497487-e288fb19713f","photo-1574717024653-61fd2cf4d44d"],
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def slugify(text: str) -> str:
    t = text.lower().strip()
    t = re.sub(r"[^\w\s-]", "", t)
    t = re.sub(r"[\s_]+", "-", t)
    t = re.sub(r"-{2,}", "-", t)
    return re.sub(r"^-+|-+$", "", t)[:65]


def pick_image(cat_slug: str, seed: str) -> str:
    import hashlib
    pool = CATEGORY_IMAGE_POOLS.get(cat_slug, list(CATEGORY_IMAGE_POOLS["ai-news"]))
    idx  = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(pool)
    return f"https://images.unsplash.com/{pool[idx]}?w=900&auto=format&fit=crop&q=80"


def fetch_rss_topics(feeds: list, fallbacks: list) -> str:
    """Return a comma-separated headline list for Groq topic context."""
    headlines = []
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:4]:
                t = (e.get("title") or "").strip()
                if t and len(t) > 20:
                    headlines.append(t)
        except Exception:
            pass
        if len(headlines) >= 8:
            break
    if not headlines:
        headlines = fallbacks[:5]
    random.shuffle(headlines)
    return " | ".join(headlines[:6])


def load_articles_json() -> list:
    if ARTICLES_JSON.exists():
        try:
            return json.loads(ARTICLES_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def save_articles_json(articles: list):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ARTICLES_JSON.write_text(
        json.dumps(articles, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def already_generated_today(cat_slug: str) -> bool:
    today = today_str()
    articles = load_articles_json()
    return any(
        a["cat_slug"] == cat_slug and a["date"] == today
        for a in articles
    )


# ─── Groq call ────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = textwrap.dedent("""
    You are a senior technology journalist writing for an independent publication called
    The Tech Brief. Your articles are original, authoritative, and deeply informative.

    Absolute rules:
    - NEVER copy, quote, or paraphrase text from any source.
    - NEVER mention other publications, websites, brands, or their article titles.
    - NEVER include affiliate links, promotional language, or sponsored content.
    - NEVER produce misleading, harmful, or controversial content.
    - Write entirely in your own words, as a knowledgeable industry expert.
    - Tone: confident, analytical, informative — like The Economist or MIT Technology Review.

    Respond ONLY with a valid JSON object. No markdown fences, no preamble, no postamble.
""").strip()


def call_groq(user_prompt: str, retries: int = 3) -> str | None:
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type":  "application/json",
                },
                json={
                    "model":       MODEL,
                    "messages":    [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user",   "content": user_prompt},
                    ],
                    "max_tokens":  1800,
                    "temperature": 0.72,
                    "top_p":       0.9,
                },
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code
            body = e.response.text[:300]
            print(f"    ✗ HTTP {code} (attempt {attempt}/{retries}): {body}")
            if code in (429, 503) and attempt < retries:
                wait = 15 * attempt
                print(f"    ⏳ Waiting {wait}s before retry…")
                time.sleep(wait)
        except requests.exceptions.Timeout:
            print(f"    ✗ Timeout (attempt {attempt}/{retries})")
            if attempt < retries:
                time.sleep(10)
        except Exception as exc:
            print(f"    ✗ Unexpected error: {exc}")
            break
    return None


def generate_article_json(cat: dict, headlines: str) -> dict | None:
    """Ask Groq to produce a structured article JSON."""
    prompt = textwrap.dedent(f"""
        Write a 700–900 word in-depth technology article for the "{cat['name']}" section of The Tech Brief.

        Use these recent tech headlines ONLY as background context for the topic area.
        Do NOT reference, quote, or name any of these headlines in your article:
        {headlines}

        Choose a compelling, specific angle within the {cat['name']} topic space that a tech-savvy reader would find genuinely valuable.

        Return a JSON object with EXACTLY this structure (no other keys):
        {{
          "title": "A compelling, specific SEO title (10-14 words, no generic phrasing)",
          "description": "A 25-30 word meta description that clearly describes the article value",
          "lead": "A strong 2-3 sentence opening paragraph (no heading, hooks the reader immediately)",
          "sections": [
            {{
              "h2": "Clear subheading (5-8 words)",
              "paragraphs": ["paragraph 1 text...", "paragraph 2 text..."]
            }}
          ],
          "conclusion": "2-3 sentence closing paragraph that offers a forward-looking insight",
          "read_minutes": 5
        }}

        Requirements:
        - Exactly 4-5 sections, each with 2-3 substantial paragraphs (3-5 sentences each)
        - Total word count: 700-900 words (excluding JSON keys)
        - Include specific facts, metrics, examples where credible — but do not attribute them to any source
        - No bullet points in paragraphs — flowing prose only
        - The article must stand alone as original editorial content
    """).strip()

    raw = call_groq(prompt)
    if not raw:
        return None

    # Strip markdown fences if model adds them
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw.strip()).strip()

    try:
        data = json.loads(raw)
        # Validate required keys
        required = {"title", "description", "lead", "sections", "conclusion", "read_minutes"}
        if not required.issubset(data.keys()):
            missing = required - set(data.keys())
            print(f"    ✗ JSON missing keys: {missing}")
            return None
        if not isinstance(data["sections"], list) or len(data["sections"]) < 3:
            print(f"    ✗ Not enough sections in response")
            return None
        return data
    except json.JSONDecodeError as e:
        print(f"    ✗ JSON parse error: {e}")
        print(f"    Raw (first 400 chars): {raw[:400]}")
        return None


# ─── HTML generation (matches site's exact design system) ─────────────────────

def build_article_html(cat: dict, data: dict, date_str: str, slug: str) -> str:
    title       = data["title"].replace('"', '&quot;').replace("<", "&lt;")
    description = data["description"].replace('"', '&quot;').replace("<", "&lt;")
    lead_html   = f'<p class="article-lead">{data["lead"]}</p>'
    image_url   = pick_image(cat["slug"], slug)
    canon_url   = f"{SITE_URL}/articles/{slug}.html"
    year        = datetime.now(timezone.utc).year
    pub_date    = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y")
    read_min    = int(data.get("read_minutes", 6))
    badge_color = cat.get("badge_color", "#2563EB")

    # Build article body HTML
    body_parts = [lead_html]
    for section in data.get("sections", []):
        h2 = str(section.get("h2", "")).replace("<", "&lt;")
        body_parts.append(f'\n    <h2>{h2}</h2>')
        for para in section.get("paragraphs", []):
            escaped = str(para).replace("<", "&lt;").replace(">", "&gt;")
            body_parts.append(f'    <p>{escaped}</p>')

    conclusion = str(data.get("conclusion", "")).replace("<", "&lt;").replace(">", "&gt;")
    if conclusion:
        body_parts.append(f'\n    <p class="article-conclusion">{conclusion}</p>')

    article_body = "\n".join(body_parts)

    # Schema.org JSON-LD
    schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": data["title"],
        "description": data["description"],
        "image": image_url,
        "datePublished": date_str,
        "dateModified":  date_str,
        "author": {
            "@type": "Organization",
            "name": AUTHOR
        },
        "publisher": {
            "@type": "Organization",
            "name": "The Tech Brief",
            "url": SITE_URL
        },
        "mainEntityOfPage": canon_url,
        "articleSection": cat["name"]
    }, indent=2)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <!-- Google Consent Mode v2 (default denied) -->
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('consent', 'default', {{
      'analytics_storage': 'denied',
      'ad_storage': 'denied',
      'ad_user_data': 'denied',
      'ad_personalization': 'denied',
      'wait_for_update': 500
    }});
  </script>
  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id={GA_TAG}"></script>
  <script>
    gtag('js', new Date());
    gtag('config', '{GA_TAG}');
  </script>

  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>{title} | The Tech Brief</title>
  <meta name="description" content="{description}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{canon_url}">

  <meta property="og:type"        content="article">
  <meta property="og:site_name"   content="The Tech Brief">
  <meta property="og:title"       content="{title}">
  <meta property="og:description" content="{description}">
  <meta property="og:url"         content="{canon_url}">
  <meta property="og:image"       content="{image_url}">
  <meta name="twitter:card"        content="summary_large_image">
  <meta name="twitter:title"       content="{title}">
  <meta name="twitter:description" content="{description}">
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
    /* Article-specific styles */
    .article-hero-img {{
      width: 100%; max-height: 420px; object-fit: cover;
      border-radius: var(--radius); margin-bottom: 36px;
      display: block;
    }}
    .article-lead {{
      font-size: 18px; line-height: 1.75;
      color: var(--ink-2); font-weight: 300;
      margin-bottom: 28px;
    }}
    .article-body h2 {{
      font-family: var(--font-serif);
      font-size: clamp(20px, 2.5vw, 26px);
      color: var(--ink); margin: 36px 0 14px;
      line-height: 1.25;
    }}
    .article-body p {{
      font-size: 16.5px; line-height: 1.78;
      color: var(--ink); margin-bottom: 20px;
    }}
    .article-conclusion {{
      background: var(--surface-2);
      border-left: 4px solid var(--accent);
      padding: 18px 22px; border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
      font-size: 16.5px; line-height: 1.75;
      color: var(--ink-2); font-style: italic;
      margin-top: 32px;
    }}
    .article-meta-bar {{
      display: flex; gap: 20px; align-items: center;
      margin-bottom: 32px; padding-bottom: 20px;
      border-bottom: 2px solid var(--border);
      flex-wrap: wrap;
    }}
    .article-meta-bar span {{
      font-size: 13px; color: var(--ink-3);
    }}
    .article-meta-bar strong {{ color: var(--ink); }}
    .related-section {{
      border-top: 2px solid var(--border);
      margin-top: 48px; padding-top: 28px;
    }}
    .related-section h3 {{
      font-family: var(--font-serif);
      font-size: 20px; margin-bottom: 16px;
    }}
    .related-links a {{
      display: block; padding: 10px 0;
      border-bottom: 1px solid var(--border-2);
      color: var(--accent); font-size: 15px;
      font-weight: 500;
    }}
    .related-links a:hover {{ color: var(--accent-h); }}
  </style>
</head>
<body>

<a class="skip-link" href="#main-content">Skip to main content</a>

<!-- ===== HEADER ===== -->
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

<!-- ===== MAIN ===== -->
<main id="main-content">
  <article class="page-wrap" style="max-width:740px;">

    <!-- Breadcrumb -->
    <div style="margin-bottom:12px; font-size:13px;">
      <a href="../index.html" style="color:var(--ink-3);">Home</a>
      <span style="color:var(--ink-3); margin:0 6px;">&rsaquo;</span>
      <a href="../{cat['page']}" style="color:var(--accent); font-weight:700;">{cat['name']}</a>
    </div>

    <!-- Category badge -->
    <a href="../{cat['page']}" style="display:inline-block; background:{badge_color}; color:#fff; padding:4px 14px; border-radius:999px; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.8px; margin-bottom:18px; text-decoration:none;">{cat['icon']} {cat['name']}</a>

    <!-- Headline -->
    <h1 style="font-family:var(--font-serif); font-size:clamp(26px,4vw,42px); line-height:1.18; margin-bottom:14px; color:var(--ink);">
      {data["title"]}
    </h1>

    <!-- Meta bar -->
    <div class="article-meta-bar">
      <span>By <strong>{AUTHOR}</strong></span>
      <span><time datetime="{date_str}">{pub_date}</time></span>
      <span>{read_min} min read</span>
      <span style="margin-left:auto;">
        <a href="../{cat['page']}" style="font-size:13px; color:var(--accent); font-weight:600;">More {cat['name']} &rarr;</a>
      </span>
    </div>

    <!-- Hero image -->
    <img class="article-hero-img"
         src="{image_url}"
         alt="Editorial illustration for: {data['title']}"
         width="740" height="400" loading="eager">

    <!-- Article body -->
    <div class="article-body">
{article_body}
    </div>

    <!-- Editorial trust notice -->
    <div style="margin-top:40px; padding:16px 20px; background:var(--surface-2); border-radius:var(--radius); font-size:13px; color:var(--ink-3);">
      <strong style="color:var(--ink);">Editorial Note:</strong> This article was produced by The Tech Brief editorial team as original analysis and commentary. It does not reproduce content from any third-party publication.
      <a href="../about.html#editorial-process" style="color:var(--accent); margin-left:6px;">About our process &rarr;</a>
    </div>

    <!-- Related section -->
    <div class="related-section">
      <h3>Continue Reading</h3>
      <div class="related-links">
        <a href="../{cat['page']}">{cat['icon']} All {cat['name']} Coverage</a>
        <a href="../how-to.html">📖 How-To Guides &amp; Tutorials</a>
        <a href="../index.html">🏠 Back to The Tech Brief Homepage</a>
      </div>
    </div>

  </article>
</main>

<!-- ===== FOOTER ===== -->
<footer class="site-footer" role="contentinfo">
  <div class="footer-inner">
    <div class="footer-about">
      <span class="brand-name">The Tech Brief</span>
      <p>An independent technology publication delivering concise, editorially reviewed coverage from across the technology industry. Updated every six hours, 24/7.</p>
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
      <a href="../how-to.html">How-To Guides</a>
    </div>
    <div class="footer-col">
      <h4>Site Info</h4>
      <a href="../about.html">About</a>
      <a href="../contact.html">Contact</a>
      <a href="../legal/privacy.html">Privacy Policy</a>
      <a href="../legal/terms.html">Terms of Use</a>
      <a href="../legal/disclaimer.html">Disclaimer</a>
      <a href="../legal/copyright.html">Copyright</a>
      <a href="../legal/affiliate.html">Affiliate Disclosure</a>
    </div>
  </div>
  <div class="footer-bottom">
    <span>&copy; {year} The Tech Brief &mdash; thetechbrief.net. All rights reserved.</span>
    <span>Independent technology journalism. Trademarks belong to their respective owners.</span>
  </div>
</footer>

<script>
  (function(){{
    var t=document.querySelector('.nav-toggle'),n=document.getElementById('site-nav');
    if(!t||!n)return;
    t.addEventListener('click',function(){{var o=n.classList.toggle('open');t.setAttribute('aria-expanded',o);}});
  }})();
</script>
<script src="../assets/cookie-consent.js"></script>
</body>
</html>
"""


# ─── Trending.txt updater ──────────────────────────────────────────────────────

def update_trending_txt(articles: list):
    """Rebuild trending.txt from the 6 most recent generated articles."""
    recent = sorted(articles, key=lambda a: a["date"], reverse=True)[:6]
    lines  = []
    for a in recent:
        label = a.get("cat_name", "Tech")
        icon_map = {
            "ai-news": "🤖", "cybersecurity-updates": "🔐",
            "mobile-gadgets": "📱", "evs-automotive": "🚗",
            "startups-business": "💼", "enterprise-tech": "🏢",
            "gaming": "🎮", "consumer-tech": "🛒", "broadcast-tech": "📡",
        }
        icon = icon_map.get(a["cat_slug"], "📰")
        summary = a.get("description", "")[:120]
        lines.append(f'{a["title"]}')
        lines.append(f'{summary}')
        lines.append(f'{icon} Original')
        lines.append(f'The Tech Brief')
        lines.append(f'articles/{a["slug"]}.html')
        lines.append("")

    TRENDING_TXT.parent.mkdir(parents=True, exist_ok=True)
    TRENDING_TXT.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ trending.txt updated ({len(recent)} entries)")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not GROQ_API_KEY:
        print("❌ GROQ_API_KEY is not set.")
        print("   Add it under: GitHub repo → Settings → Secrets → GROQ_API_KEY")
        sys.exit(1)

    SITE_DIR.mkdir(parents=True, exist_ok=True)

    today     = today_str()
    articles  = load_articles_json()
    generated = 0

    print()
    print("═" * 60)
    print(f"  The Tech Brief — Original Article Generator")
    print(f"  Date: {today}  |  Categories: {len(CATEGORIES)}")
    print("═" * 60)

    random.shuffle(CATEGORIES)

    for cat in CATEGORIES:
        print(f"\n▶  [{cat['name']}]")

        if already_generated_today(cat["slug"]):
            print(f"   ✓ Article already exists for today — skipping")
            continue

        # Fetch topic inspiration
        print(f"   Fetching RSS headlines for context…")
        headlines = fetch_rss_topics(cat["feeds"], cat["topics_fallback"])
        print(f"   Topics context: {headlines[:80]}…")

        # Generate via Groq
        print(f"   Calling Groq Llama 3 (70B)…")
        data = generate_article_json(cat, headlines)
        if not data:
            print(f"   ✗ Generation failed — skipping")
            continue

        # Build file slug and path
        title_slug = slugify(data["title"])
        slug       = f"{today}-{cat['slug']}" if not title_slug else f"{today}-{title_slug}"
        html_path  = SITE_DIR / f"{slug}.html"

        # Save HTML
        html = build_article_html(cat, data, today, slug)
        html_path.write_text(html, encoding="utf-8")
        print(f"   📄 Saved: site/articles/{slug}.html")
        print(f"   Title: {data['title']}")

        # Record metadata
        record = {
            "slug":        slug,
            "title":       data["title"],
            "description": data["description"],
            "date":        today,
            "cat_name":    cat["name"],
            "cat_slug":    cat["slug"],
            "cat_page":    cat["page"],
            "cat_icon":    cat["icon"],
            "image":       pick_image(cat["slug"], slug),
            "read_minutes": int(data.get("read_minutes", 6)),
            "url":         f"articles/{slug}.html",
        }
        articles.insert(0, record)
        generated += 1

    # Trim to max stored
    articles = articles[:MAX_STORED]

    # Persist JSON
    save_articles_json(articles)
    print(f"\n  ✓ generated_articles.json updated ({len(articles)} total entries)")

    # Update trending widget
    update_trending_txt(articles)

    print()
    print("═" * 60)
    print(f"  Done — {generated} new article(s) generated today")
    print("═" * 60)
    print()


if __name__ == "__main__":
    main()
