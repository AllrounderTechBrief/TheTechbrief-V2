#!/usr/bin/env python3
"""
generate_articles.py — The Streamic
Daily AI-authored original article generator using Groq Llama 3.

• Generates 1 long-form original article per category (8 articles/day)
• Each article: 700–900 words, editorial structure with H2 subheadings
• Saves full styled HTML → site/articles/YYYY-MM-DD-{catslug}.html
• Syncs metadata → data/generated_articles.json (homepage + category injection)
• Auto-updates site/assets/data/trending.txt with latest headlines
• Skips categories that already have today's article (idempotent — safe to re-run)

STRICT RULES FOR CONTENT:
- Never copy or paraphrase text from RSS feeds or external websites.
- Use RSS feeds ONLY to identify the topic, not the wording.
- Every article must be 700–900 words minimum.
- Write in a human, editorial, broadcast-industry tone.
- Add background, context, implications, and industry impact.
- Never mention the original source publication.
- Output clean original prose only.

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
ROOT          = Path(__file__).resolve().parent.parent
SITE_DIR      = ROOT / "site" / "articles"
DATA_DIR      = ROOT / "data"
TRENDING_TXT  = ROOT / "site" / "assets" / "data" / "trending.txt"
ARTICLES_JSON = DATA_DIR / "generated_articles.json"

# ─── Config ───────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
MODEL        = "llama3-70b-8192"
SITE_URL     = "https://www.thestreamic.in"
GA_TAG       = "G-0VSHDN3ZR6"
ADSENSE_ID   = "ca-pub-8033069131874524"
AUTHOR       = "The Streamic Editorial Team"
MAX_STORED   = 60

# ─── Category definitions ─────────────────────────────────────────────────────
CATEGORIES = [
    {
        "name": "Streaming",
        "slug": "streaming",
        "page": "streaming.html",
        "badge_color": "#0071e3",
        "icon": "📡",
        "feeds": [
            "https://www.streamingmediablog.com/feed",
            "https://www.streaminglearningcenter.com/rss.xml",
            "https://mux.com/blog/feed/",
            "https://www.haivision.com/blog/feed/",
            "https://bitmovin.com/blog/feed/",
        ],
        "topics_fallback": [
            "The evolution of adaptive bitrate streaming in 2025",
            "Why low-latency live streaming is still a hard problem",
            "HEVC vs AV1: the codec battle reshaping streaming infrastructure",
            "CDN architecture for global live events at scale",
            "The rise of CMAF and its impact on multi-DRM workflows",
        ],
    },
    {
        "name": "Cloud Production",
        "slug": "cloud",
        "page": "cloud.html",
        "badge_color": "#5856d6",
        "icon": "☁️",
        "feeds": [
            "https://aws.amazon.com/blogs/media/feed/",
            "https://blog.frame.io/feed/",
            "https://blog.cloudflare.com/rss/",
            "https://mux.com/blog/feed/",
            "https://www.tvbeurope.com/feed/",
        ],
        "topics_fallback": [
            "How IP-based production is replacing satellite and fibre contribution",
            "Cloud-native playout: vendors and broadcasters assess the transition",
            "The economics of cloud versus on-premises broadcast infrastructure",
            "Remote production workflows after the pandemic acceleration",
            "Multi-cloud redundancy strategies for live broadcast operations",
        ],
    },
    {
        "name": "AI & Post-Production",
        "slug": "ai-post-production",
        "page": "ai-post-production.html",
        "badge_color": "#FF2D55",
        "icon": "🎬",
        "feeds": [
            "https://www.provideocoalition.com/feed/",
            "https://www.newsshooter.com/feed/",
            "https://postperspective.com/feed/",
            "https://www.studiodaily.com/feed/",
            "https://blog.frame.io/feed/",
        ],
        "topics_fallback": [
            "How AI is automating rough cuts in broadcast news editing",
            "The ethics of AI-generated content in broadcast journalism",
            "LLM-powered metadata tagging and media asset management",
            "Real-time AI dubbing and localisation for streaming platforms",
            "Generative AI tools entering the professional post-production suite",
        ],
    },
    {
        "name": "Graphics",
        "slug": "graphics",
        "page": "graphics.html",
        "badge_color": "#FF9500",
        "icon": "🎨",
        "feeds": [
            "https://motionographer.com/feed/",
            "https://www.cgchannel.com/feed/",
            "https://realtimevfx.com/latest.rss",
            "https://www.newscaststudio.com/feed/",
            "https://www.tvtechnology.com/news/rss.xml",
        ],
        "topics_fallback": [
            "Unreal Engine in live broadcast: a practical assessment",
            "The shift to IP-based graphics distribution in newsrooms",
            "Real-time data visualisation for election night coverage",
            "Virtual studios and extended reality in broadcast sports",
            "The role of WebGL in next-generation broadcast graphics",
        ],
    },
    {
        "name": "Playout",
        "slug": "playout",
        "page": "playout.html",
        "badge_color": "#34C759",
        "icon": "▶️",
        "feeds": [
            "https://www.harmonicinc.com/insights/blog/rss.xml",
            "https://www.pebble.tv/feed/",
            "https://www.tvtechnology.com/news/rss.xml",
            "https://www.tvbeurope.com/feed/",
            "https://www.newscaststudio.com/feed/",
        ],
        "topics_fallback": [
            "Channel-in-a-box evolution: what broadcasters are actually deploying",
            "Software-defined playout and the virtualisation of master control",
            "How OTT has changed the economics of traditional playout",
            "Redundancy and failover architectures in modern playout systems",
            "The business case for cloud playout in regional broadcasting",
        ],
    },
    {
        "name": "Infrastructure",
        "slug": "infrastructure",
        "page": "infrastructure.html",
        "badge_color": "#8E8E93",
        "icon": "🏗️",
        "feeds": [
            "https://cloudinary.com/blog/feed",
            "https://blog.cloudflare.com/rss/",
            "https://aws.amazon.com/blogs/media/feed/",
            "https://www.tvtechnology.com/news/rss.xml",
            "https://www.tvbeurope.com/feed/",
        ],
        "topics_fallback": [
            "SMPTE ST 2110 adoption: where the industry actually stands",
            "MAM systems in the age of AI-assisted metadata and search",
            "NVMe storage and the future of high-resolution media workflows",
            "Software-defined networking in broadcast facility design",
            "The security challenges of IP-based broadcast infrastructure",
        ],
    },
    {
        "name": "Newsroom",
        "slug": "newsroom",
        "page": "newsroom.html",
        "badge_color": "#D4AF37",
        "icon": "📰",
        "feeds": [
            "https://www.newscaststudio.com/feed/",
            "https://www.tvtechnology.com/news/rss.xml",
            "https://www.broadcastbeat.com/feed/",
            "https://www.svgeurope.org/feed/",
            "https://www.tvbeurope.com/feed/",
        ],
        "topics_fallback": [
            "How AI writing assistants are entering broadcast newsrooms",
            "The remote newsroom: permanent change or pandemic relic?",
            "Social media verification tools for broadcast journalists",
            "Newsroom computer systems: the vendor landscape in 2025",
            "Automation in news production: where it helps and where it fails",
        ],
    },
    {
        "name": "Featured",
        "slug": "featured",
        "page": "featured.html",
        "badge_color": "#1d1d1f",
        "icon": "⭐",
        "feeds": [
            "https://www.newscaststudio.com/feed/",
            "https://www.tvbeurope.com/feed/",
            "https://www.tvtechnology.com/news/rss.xml",
            "https://www.broadcastbeat.com/feed/",
        ],
        "topics_fallback": [
            "The broadcast technology story of the week",
            "Major shifts in media infrastructure and production workflows",
            "How streaming economics are reshaping broadcast strategy",
            "The convergence of IT and broadcast: a five-year assessment",
            "What the next generation of broadcast engineers needs to know",
        ],
    },
]


# ─── Unsplash image pools ─────────────────────────────────────────────────────
CATEGORY_IMAGE_POOLS = {
    "streaming":          ["photo-1598488035139-bdbb2231ce04","photo-1516321497487-e288fb19713f","photo-1574717024653-61fd2cf4d44d","photo-1567095761054-7003afd47020","photo-1540575467063-178a50c2df87","photo-1611532736597-de2d4265fba3"],
    "cloud":              ["photo-1451187580459-43490279c0fa","photo-1544197150-b99a580bb7a8","photo-1560472355-536de3962603","photo-1504639725590-34d0984388bd","photo-1558494949-ef010cbdcc31","photo-1531297484001-80022131f5a1"],
    "ai-post-production": ["photo-1677442135703-1787eea5ce01","photo-1620712943543-bcc4688e7485","photo-1655635643532-fa9ba2648cbe","photo-1533228100845-08145b01de14","photo-1635070041078-e363dbe005cb","photo-1501526029524-a8ea952b15be"],
    "graphics":           ["photo-1593642632559-0c6d3fc62b89","photo-1518770660439-4636190af475","photo-1547658719-da2b51169166","photo-1541462608143-67571c6738dd","photo-1568952433726-3896e3881c65","photo-1497091071254-cc9b2ba7c48a"],
    "playout":            ["photo-1612420696760-0a0f34d3e7d0","photo-1478737270239-2f02b77fc618","photo-1598488035139-bdbb2231ce04","photo-1574717024653-61fd2cf4d44d","photo-1492619375914-88005aa9e8fb","photo-1590602847861-f357a9332bbc"],
    "infrastructure":     ["photo-1486312338219-ce68d2c6f44d","photo-1497366216548-37526070297c","photo-1560472354-b33ff0c44a43","photo-1553877522-43269d4ea984","photo-1542744094-3a31f272c490","photo-1504384308090-c894fdcc538d"],
    "newsroom":           ["photo-1504711434969-e33886168f5c","photo-1493863641943-9b68992a8d07","photo-1585829365295-ab7cd400c167","photo-1432821596592-e2c18b78144f","photo-1503428593586-e225b39bddfe","photo-1495020689067-958852a7765e"],
    "featured":           ["photo-1598488035139-bdbb2231ce04","photo-1478737270239-2f02b77fc618","photo-1567095761054-7003afd47020","photo-1486312338219-ce68d2c6f44d","photo-1451187580459-43490279c0fa","photo-1677442135703-1787eea5ce01"],
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def slugify_title(text: str) -> str:
    t = text.lower().strip()
    t = re.sub(r"[^\w\s-]", "", t)
    t = re.sub(r"[\s_]+", "-", t)
    t = re.sub(r"-{2,}", "-", t)
    return re.sub(r"^-+|-+$", "", t)[:65]


def pick_image(cat_slug: str, seed: str) -> str:
    import hashlib
    pool = CATEGORY_IMAGE_POOLS.get(cat_slug, list(CATEGORY_IMAGE_POOLS["featured"]))
    idx  = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(pool)
    return f"https://images.unsplash.com/{pool[idx]}?w=900&auto=format&fit=crop&q=80"


def fetch_rss_topics(feeds: list, fallbacks: list) -> str:
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
    today    = today_str()
    articles = load_articles_json()
    return any(
        a["cat_slug"] == cat_slug and a["date"] == today
        for a in articles
    )


# ─── Groq call ────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = textwrap.dedent("""
    You are a senior broadcast technology journalist writing for The Streamic,
    an independent publication covering the professional broadcast and streaming
    technology industry.

    Your readers are broadcast engineers, media technology directors, post-production
    professionals, and streaming platform operators. Write at their level — technical
    depth matters. Assume familiarity with industry terms like SMPTE ST 2110, HEVC,
    CDN, MAM, playout automation, and cloud-native production.

    ABSOLUTE RULES — no exceptions:
    - NEVER copy, quote, or paraphrase text from any source.
    - NEVER mention other publications, websites, brands, or their article titles.
    - NEVER include affiliate links, promotional language, or sponsored content.
    - NEVER produce misleading, harmful, or controversial content.
    - Write entirely in your own words, as a knowledgeable industry expert.
    - Tone: authoritative, analytical, technically precise — like TVBEurope or SVG editorial.

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
    prompt = textwrap.dedent(f"""
        Write a 700–900 word in-depth broadcast technology article for the "{cat['name']}"
        section of The Streamic.

        Use these recent industry headlines ONLY as background context for the topic area.
        Do NOT reference, quote, or name any of these headlines in your article:
        {headlines}

        Choose a compelling, specific angle within the {cat['name']} topic space that a
        broadcast engineer or media technology professional would find genuinely valuable.

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
        - Include specific technical facts, standards, metrics, and real-world deployment context
        - No bullet points in paragraphs — flowing technical prose only
        - The article must stand alone as original editorial content for a broadcast professional audience
    """).strip()

    raw = call_groq(prompt)
    if not raw:
        return None

    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw.strip()).strip()

    try:
        data = json.loads(raw)
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


# ─── HTML generation ──────────────────────────────────────────────────────────

def build_article_html(cat: dict, data: dict, date_str: str, slug: str) -> str:
    title       = data["title"].replace('"', '&quot;').replace("<", "&lt;")
    description = data["description"].replace('"', '&quot;').replace("<", "&lt;")
    lead_html   = f'<p class="article-lead">{data["lead"]}</p>'
    image_url   = pick_image(cat["slug"], slug)
    canon_url   = f"{SITE_URL}/articles/{slug}.html"
    year        = datetime.now(timezone.utc).year
    pub_date    = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y")
    read_min    = int(data.get("read_minutes", 6))
    badge_color = cat.get("badge_color", "#0071e3")

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
            "name": "The Streamic",
            "url": SITE_URL
        },
        "mainEntityOfPage": canon_url,
        "articleSection": cat["name"]
    }, indent=2)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
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
  <!-- Google AdSense -->
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_ID}" crossorigin="anonymous"></script>

  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} | The Streamic</title>
  <meta name="description" content="{description}">
  <meta name="robots" content="index, follow">
  <meta name="author" content="{AUTHOR}">
  <link rel="canonical" href="{canon_url}">

  <meta property="og:type"        content="article">
  <meta property="og:site_name"   content="The Streamic">
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

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Montserrat:wght@300;400;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../style.css">

  <style>
    .article-wrap {{
      max-width: 760px;
      margin: 0 auto;
      padding: 40px 24px 80px;
    }}
    .article-hero-img {{
      width: 100%; max-height: 420px; object-fit: cover;
      border-radius: 12px; margin-bottom: 36px;
      display: block;
    }}
    .article-breadcrumb {{
      font-size: 13px;
      color: #86868b;
      margin-bottom: 16px;
    }}
    .article-breadcrumb a {{
      color: #86868b;
      text-decoration: none;
    }}
    .article-breadcrumb a:hover {{ color: #000; }}
    .article-category-badge {{
      display: inline-block;
      background: {badge_color};
      color: #fff;
      padding: 4px 14px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      margin-bottom: 18px;
      text-decoration: none;
    }}
    .article-title {{
      font-family: Montserrat, sans-serif;
      font-size: clamp(26px, 4vw, 42px);
      font-weight: 700;
      line-height: 1.18;
      margin-bottom: 14px;
      color: #1d1d1f;
    }}
    .article-meta {{
      display: flex;
      gap: 20px;
      align-items: center;
      margin-bottom: 32px;
      padding-bottom: 20px;
      border-bottom: 1px solid #d2d2d7;
      flex-wrap: wrap;
      font-size: 13px;
      color: #86868b;
    }}
    .article-meta strong {{ color: #1d1d1f; }}
    .article-meta a {{
      margin-left: auto;
      font-size: 13px;
      color: #0071e3;
      font-weight: 600;
      text-decoration: none;
    }}
    .article-lead {{
      font-size: 18px;
      line-height: 1.75;
      color: #424245;
      font-weight: 400;
      margin-bottom: 28px;
    }}
    .article-body h2 {{
      font-family: Montserrat, sans-serif;
      font-size: clamp(20px, 2.5vw, 26px);
      font-weight: 700;
      color: #1d1d1f;
      margin: 36px 0 14px;
      line-height: 1.25;
    }}
    .article-body p {{
      font-size: 16.5px;
      line-height: 1.78;
      color: #1d1d1f;
      margin-bottom: 20px;
    }}
    .article-conclusion {{
      background: #f5f5f7;
      border-left: 4px solid {badge_color};
      padding: 18px 22px;
      border-radius: 0 8px 8px 0;
      font-size: 16.5px;
      line-height: 1.75;
      color: #424245;
      font-style: italic;
      margin-top: 32px;
    }}
    .article-editorial-note {{
      margin-top: 40px;
      padding: 16px 20px;
      background: #f5f5f7;
      border-radius: 8px;
      font-size: 13px;
      color: #86868b;
    }}
    .article-editorial-note strong {{ color: #1d1d1f; }}
    .related-section {{
      border-top: 1px solid #d2d2d7;
      margin-top: 48px;
      padding-top: 28px;
    }}
    .related-section h3 {{
      font-family: Montserrat, sans-serif;
      font-size: 20px;
      font-weight: 700;
      margin-bottom: 16px;
    }}
    .related-links a {{
      display: block;
      padding: 10px 0;
      border-bottom: 1px solid #f5f5f7;
      color: #0071e3;
      font-size: 15px;
      font-weight: 500;
      text-decoration: none;
    }}
    .related-links a:hover {{ color: #0077ed; }}
  </style>
</head>
<body>
  <nav class="site-nav">
    <div class="nav-inner">
      <a href="../featured.html" class="nav-logo-container">
        <img src="../assets/logo.png" alt="The Streamic" class="nav-logo-image" onload="this.closest('.nav-logo-container').classList.add('logo-loaded')">
        <span class="nav-logo">THE STREAMIC</span>
      </a>
      <button class="nav-toggle" aria-label="Toggle menu">☰</button>
      <ul class="nav-links">
        <li><a href="../featured.html">FEATURED</a></li>
        <li><a href="../infrastructure.html">INFRASTRUCTURE</a></li>
        <li><a href="../graphics.html">GRAPHICS</a></li>
        <li><a href="../cloud.html">CLOUD PRODUCTION</a></li>
        <li><a href="../streaming.html">STREAMING</a></li>
        <li><a href="../ai-post-production.html">AI &amp; POST-PRODUCTION</a></li>
        <li><a href="../playout.html">PLAYOUT</a></li>
        <li><a href="../newsroom.html">NEWSROOM</a></li>
      </ul>
      <div class="header-subscribe">
        <a href="../vlog.html" class="editors-desk-link">Editor's Desk</a>
      </div>
    </div>
  </nav>

  <main>
    <div class="article-wrap">

      <div class="article-breadcrumb">
        <a href="../featured.html">Home</a>
        &rsaquo;
        <a href="../{cat['page']}" style="color:{badge_color}; font-weight:600;">{cat['name']}</a>
      </div>

      <a href="../{cat['page']}" class="article-category-badge">{cat['icon']} {cat['name']}</a>

      <h1 class="article-title">{data["title"]}</h1>

      <div class="article-meta">
        <span>By <strong>{AUTHOR}</strong></span>
        <span><time datetime="{date_str}">{pub_date}</time></span>
        <span>{read_min} min read</span>
        <a href="../{cat['page']}">More {cat['name']} &rarr;</a>
      </div>

      <img class="article-hero-img"
           src="{image_url}"
           alt="Editorial illustration for: {data['title']}"
           width="760" height="420" loading="eager">

      <div class="article-body">
{article_body}
      </div>

      <div class="article-editorial-note">
        <strong>Editorial Note:</strong> This article was produced by The Streamic editorial team
        as original analysis and commentary on broadcast and streaming technology. It does not
        reproduce content from any third-party publication.
        <a href="../about.html" style="color:#0071e3; margin-left:6px;">About The Streamic &rarr;</a>
      </div>

      <div class="related-section">
        <h3>Continue Reading</h3>
        <div class="related-links">
          <a href="../{cat['page']}">{cat['icon']} All {cat['name']} Coverage</a>
          <a href="../featured.html">⭐ Featured Stories</a>
          <a href="../vlog.html">🎙️ Editor's Desk</a>
        </div>
      </div>

    </div>
  </main>

  <footer style="background:#1d1d1f; color:#86868b; padding:40px 24px; text-align:center; font-size:13px; margin-top:60px;">
    <div style="max-width:1200px; margin:0 auto;">
      <p style="margin-bottom:12px;">
        <a href="../featured.html" style="color:#fff; font-weight:700; text-decoration:none; font-size:16px;">THE STREAMIC</a>
      </p>
      <p style="margin-bottom:16px;">Independent broadcast and streaming technology publication. Updated daily.</p>
      <p>
        <a href="../featured.html" style="color:#86868b; margin:0 10px;">Home</a>
        <a href="../streaming.html" style="color:#86868b; margin:0 10px;">Streaming</a>
        <a href="../cloud.html" style="color:#86868b; margin:0 10px;">Cloud</a>
        <a href="../ai-post-production.html" style="color:#86868b; margin:0 10px;">AI &amp; Post</a>
        <a href="../graphics.html" style="color:#86868b; margin:0 10px;">Graphics</a>
        <a href="../playout.html" style="color:#86868b; margin:0 10px;">Playout</a>
        <a href="../about.html" style="color:#86868b; margin:0 10px;">About</a>
        <a href="../contact.html" style="color:#86868b; margin:0 10px;">Contact</a>
        <a href="../privacy.html" style="color:#86868b; margin:0 10px;">Privacy</a>
        <a href="../terms.html" style="color:#86868b; margin:0 10px;">Terms</a>
      </p>
      <p style="margin-top:20px;">&copy; {year} The Streamic &mdash; thestreamic.in. All rights reserved.</p>
    </div>
  </footer>

  <script>
    (function() {{
      var t = document.querySelector('.nav-toggle');
      var n = document.querySelector('.nav-links');
      if (!t || !n) return;
      t.addEventListener('click', function() {{
        n.style.display = n.style.display === 'flex' ? 'none' : 'flex';
      }});
    }})();
  </script>
</body>
</html>
"""


# ─── Trending.txt updater ──────────────────────────────────────────────────────

def update_trending_txt(articles: list):
    recent = sorted(articles, key=lambda a: a["date"], reverse=True)[:6]
    lines  = []
    icon_map = {
        "streaming": "📡", "cloud": "☁️", "ai-post-production": "🎬",
        "graphics": "🎨", "playout": "▶️", "infrastructure": "🏗️",
        "newsroom": "📰", "featured": "⭐",
    }
    for a in recent:
        icon    = icon_map.get(a["cat_slug"], "📡")
        summary = a.get("description", "")[:120]
        lines.append(f'{a["title"]}')
        lines.append(f'{summary}')
        lines.append(f'{icon} Original')
        lines.append(f'The Streamic')
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
    print(f"  The Streamic — Original Article Generator")
    print(f"  Date: {today}  |  Categories: {len(CATEGORIES)}")
    print("═" * 60)

    random.shuffle(CATEGORIES)

    for cat in CATEGORIES:
        print(f"\n▶  [{cat['name']}]")

        if already_generated_today(cat["slug"]):
            print(f"   ✓ Article already exists for today — skipping")
            continue

        print(f"   Fetching RSS headlines for context…")
        headlines = fetch_rss_topics(cat["feeds"], cat["topics_fallback"])
        print(f"   Topics context: {headlines[:80]}…")

        print(f"   Calling Groq Llama 3 (70B)…")
        data = generate_article_json(cat, headlines)
        if not data:
            print(f"   ✗ Generation failed — skipping")
            continue

        title_slug = slugify_title(data["title"])
        slug       = f"{today}-{cat['slug']}" if not title_slug else f"{today}-{title_slug}"
        html_path  = SITE_DIR / f"{slug}.html"

        html = build_article_html(cat, data, today, slug)
        html_path.write_text(html, encoding="utf-8")
        print(f"   📄 Saved: site/articles/{slug}.html")
        print(f"   Title: {data['title']}")

        record = {
            "slug":         slug,
            "title":        data["title"],
            "description":  data["description"],
            "date":         today,
            "cat_name":     cat["name"],
            "cat_slug":     cat["slug"],
            "cat_page":     cat["page"],
            "cat_icon":     cat["icon"],
            "image":        pick_image(cat["slug"], slug),
            "read_minutes": int(data.get("read_minutes", 6)),
            "url":          f"articles/{slug}.html",
        }
        articles.insert(0, record)
        generated += 1

    articles = articles[:MAX_STORED]
    save_articles_json(articles)
    print(f"\n  ✓ generated_articles.json updated ({len(articles)} total entries)")

    update_trending_txt(articles)

    print()
    print("═" * 60)
    print(f"  Done — {generated} new article(s) generated today")
    print("═" * 60)
    print()


if __name__ == "__main__":
    main()
