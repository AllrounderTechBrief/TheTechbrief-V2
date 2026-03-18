#!/usr/bin/env python3
"""
generate_trending.py — The Tech Brief
────────────────────────────────────────────────────────────────────
Runs daily (via GitHub Actions at 05:30 UTC, after generate_articles.py).
Fetches the top 6 RSS stories from across all categories, then uses
Groq Llama 3 to write a full 400–500 word editorial article for each.
Saves everything to site/assets/data/trending.json.
The trending-loader.js reads this file and renders full expandable articles.
────────────────────────────────────────────────────────────────────
"""

import os, sys, json, re, time, random, hashlib, requests
import feedparser
from datetime import datetime, timezone
from pathlib import Path

ROOT         = Path(__file__).resolve().parent.parent
OUT_JSON     = ROOT / "site" / "assets" / "data" / "trending.json"
CACHE_FILE   = ROOT / "data" / "trending_cache.json"

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
MODEL        = "llama3-70b-8192"
SITE_URL     = "https://www.thetechbrief.net"

# Top RSS feeds per category — diverse mix for trending
TRENDING_FEEDS = [
    {"cat": "AI News",              "slug": "ai-news",              "url": "https://techcrunch.com/tag/ai/feed/"},
    {"cat": "AI News",              "slug": "ai-news",              "url": "https://venturebeat.com/category/ai/feed/"},
    {"cat": "Mobile & Gadgets",     "slug": "mobile-gadgets",       "url": "https://www.theverge.com/rss/gadgets/index.xml"},
    {"cat": "Cybersecurity",        "slug": "cybersecurity-updates","url": "https://www.darkreading.com/rss.xml"},
    {"cat": "Enterprise Tech",      "slug": "enterprise-tech",      "url": "https://www.zdnet.com/topic/enterprise/rss.xml"},
    {"cat": "EVs & Automotive",     "slug": "evs-automotive",       "url": "https://electrek.co/feed/"},
    {"cat": "Startups & Business",  "slug": "startups-business",    "url": "https://techcrunch.com/feed/"},
    {"cat": "Gaming",               "slug": "gaming",               "url": "https://kotaku.com/rss"},
    {"cat": "Consumer Tech",        "slug": "consumer-tech",        "url": "https://www.cnet.com/rss/all/"},
    {"cat": "Broadcast Tech",       "slug": "broadcast-tech",       "url": "https://www.newscaststudio.com/feed/"},
]

# Unsplash image pools per category (copyright-free)
IMAGE_POOLS = {
    "ai-news":               ["photo-1677442135703-1787eea5ce01","photo-1620712943543-bcc4688e7485","photo-1655635643532-fa9ba2648cbe","photo-1635070041078-e363dbe005cb","photo-1558494949-ef010cbdcc31"],
    "cybersecurity-updates": ["photo-1550751827-4bd374c3f58b","photo-1563986768609-322da13575f3","photo-1614064641938-3bbee52942c7","photo-1510511233900-1982d92bd835","photo-1504384308090-c894fdcc538d"],
    "mobile-gadgets":        ["photo-1511707171634-5f897ff02aa9","photo-1592750475338-74b7b21085ab","photo-1585060544812-6b45742d762f","photo-1542751371-adc38448a05e","photo-1567581935884-3349723552ca"],
    "evs-automotive":        ["photo-1593941707882-a5bba14938c7","photo-1558618666-fcd25c85cd64","photo-1616455579100-2ceaa4eb2d37","photo-1580274455191-1c62238fa1f4","photo-1617469767053-d3b523a0b982"],
    "startups-business":     ["photo-1559136555-9303baea8ebd","photo-1450101499163-c8848c66ca85","photo-1460925895917-afdab827c52f","photo-1553484771-371a605b060b","photo-1579532537598-459ecdaf39cc"],
    "enterprise-tech":       ["photo-1486312338219-ce68d2c6f44d","photo-1497366216548-37526070297c","photo-1568952433726-3896e3881c65","photo-1542744094-3a31f272c490","photo-1454165804606-c3d57bc86b40"],
    "gaming":                ["photo-1538481199705-c710c4e965fc","photo-1493711662062-fa541adb3fc8","photo-1552820728-8b83bb6b773f","photo-1601887389937-0b02f7683064","photo-1574375927938-d5a98e8ffe85"],
    "consumer-tech":         ["photo-1498049794561-7780e7231661","photo-1517694712202-14dd9538aa97","photo-1593642632559-0c6d3fc62b89","photo-1519389950473-47ba0277781c","photo-1550009158-9ebf69173e03"],
    "broadcast-tech":        ["photo-1478737270239-2f02b77fc618","photo-1567095761054-7003afd47020","photo-1598488035139-bdbb2231ce04","photo-1574717024653-61fd2cf4d44d","photo-1516321497487-e288fb19713f"],
}

BADGE_MAP = {
    "ai-news":               {"badge": "AI Alert",   "color": "#7C3AED"},
    "cybersecurity-updates": {"badge": "Security",   "color": "#DC2626"},
    "mobile-gadgets":        {"badge": "Gadgets",    "color": "#0891B2"},
    "evs-automotive":        {"badge": "EVs",        "color": "#059669"},
    "startups-business":     {"badge": "Business",   "color": "#D97706"},
    "enterprise-tech":       {"badge": "Enterprise", "color": "#2563EB"},
    "gaming":                {"badge": "Gaming",     "color": "#7C3AED"},
    "consumer-tech":         {"badge": "Consumer",   "color": "#0891B2"},
    "broadcast-tech":        {"badge": "Broadcast",  "color": "#BE185D"},
}


def pick_image(slug: str, seed: str) -> str:
    pool = IMAGE_POOLS.get(slug, IMAGE_POOLS["ai-news"])
    idx  = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(pool)
    return f"https://images.unsplash.com/{pool[idx]}?w=900&auto=format&fit=crop&q=80"


def today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_cache(cache: dict):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def fetch_top_stories(n: int = 12) -> list:
    """Fetch top headlines from all feeds, pick best n by recency."""
    stories = []
    for feed_cfg in TRENDING_FEEDS:
        try:
            feed = feedparser.parse(feed_cfg["url"])
            for entry in feed.entries[:3]:
                title = (entry.get("title") or "").strip()
                link  = (entry.get("link") or "").strip()
                if not title or not link or len(title) < 20:
                    continue
                ts = entry.get("published_parsed") or entry.get("updated_parsed")
                ts_val = time.mktime(ts) if ts else 0
                stories.append({
                    "title":   title,
                    "link":    link,
                    "cat":     feed_cfg["cat"],
                    "slug":    feed_cfg["slug"],
                    "ts":      ts_val,
                    "feed_url": feed_cfg["url"],
                })
        except Exception as ex:
            print(f"  Feed error {feed_cfg['url']}: {ex}")

    # Sort by recency, deduplicate by title similarity
    stories.sort(key=lambda x: x["ts"], reverse=True)
    seen = set()
    deduped = []
    for s in stories:
        key = s["title"][:40].lower()
        if key not in seen:
            deduped.append(s)
            seen.add(key)
    return deduped[:n]


def call_groq_trending(title: str, category: str) -> dict | None:
    """
    Generate a full 400–500 word trending article.
    Returns dict with keys: headline, intro, body_paragraphs (list), conclusion
    """
    if not GROQ_API_KEY:
        return None

    system = (
        "You are a senior technology journalist at The Tech Brief, an independent publication. "
        "You write 100% original editorial content. "
        "You NEVER copy, quote, or reference any external source, publication, or website. "
        "Return ONLY valid JSON — no markdown fences, no preamble."
    )

    user = f"""Write a full 400–500 word original technology article for The Tech Brief's trending section.

Topic context (use as subject inspiration ONLY — do NOT copy or reference this headline):
"{title}"
Category: {category}

Return a JSON object with EXACTLY this structure:
{{
  "headline": "A sharp, specific news headline (8-12 words) — NOT a copy of the input",
  "intro": "A powerful 2-sentence opening that immediately hooks the reader",
  "paragraphs": [
    "First body paragraph (80-100 words) — what is happening and why it matters",
    "Second body paragraph (80-100 words) — industry context, who is affected",
    "Third body paragraph (80-100 words) — implications for businesses or consumers",
    "Fourth body paragraph (80-100 words) — broader technology trend this reflects"
  ],
  "conclusion": "A 2-sentence forward-looking conclusion",
  "key_insight": "One sharp sentence (max 20 words) — the single most important takeaway"
}}

Rules:
- Every word must be 100% original — written by you, not lifted from any source
- No "according to", no brand-attributed quotes, no source names
- Confident, analytical, Economist-style tone
- Paragraph[0] should start with the most compelling fact or development
- Total body word count: 350-430 words across intro + 4 paragraphs + conclusion"""

    for attempt in range(1, 3):
        try:
            resp = requests.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user",   "content": user},
                    ],
                    "max_tokens": 1200,
                    "temperature": 0.72,
                },
                timeout=45,
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"\s*```$", "", raw.strip()).strip()
            data = json.loads(raw)
            required = {"headline", "intro", "paragraphs", "conclusion", "key_insight"}
            if not required.issubset(data.keys()):
                print(f"  ✗ Missing keys: {required - set(data.keys())}")
                return None
            if not isinstance(data["paragraphs"], list) or len(data["paragraphs"]) < 3:
                print(f"  ✗ Not enough paragraphs")
                return None
            return data
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429 and attempt == 1:
                print(f"  ⏳ Rate limit — waiting 25s…")
                time.sleep(25)
            else:
                print(f"  ✗ HTTP {e.response.status_code}")
                return None
        except json.JSONDecodeError as e:
            print(f"  ✗ JSON parse error: {e}")
            return None
        except Exception as ex:
            print(f"  ✗ Error: {ex}")
            return None
    return None


def generate_trending():
    if not GROQ_API_KEY:
        print("❌ GROQ_API_KEY not set — skipping trending generation")
        sys.exit(0)

    today   = today_str()
    cache   = load_cache()

    print("\n" + "═"*55)
    print("  The Tech Brief — Trending Article Generator")
    print(f"  Date: {today}")
    print("═"*55)

    # Fetch top stories
    print("\nFetching top RSS stories across all categories…")
    stories = fetch_top_stories(12)
    print(f"  Found {len(stories)} candidate stories")

    # Pick 6 — one per unique category where possible
    selected = []
    used_cats = set()
    for story in stories:
        if story["slug"] not in used_cats and len(selected) < 6:
            selected.append(story)
            used_cats.add(story["slug"])
    # Fill remaining slots if needed
    for story in stories:
        if len(selected) >= 6:
            break
        if story not in selected:
            selected.append(story)

    output = []
    for i, story in enumerate(selected):
        print(f"\n[{i+1}/6] {story['cat']}: {story['title'][:65]}…")

        cache_key = hashlib.md5(story["title"].encode()).hexdigest()[:16]
        cached    = cache.get(cache_key)

        # Use cache if it was generated today
        if cached and cached.get("date") == today:
            print(f"  ✓ Using today's cache")
            output.append(cached)
            continue

        print(f"  ✍  Calling Groq Llama 3…")
        article = call_groq_trending(story["title"], story["cat"])

        if not article:
            print(f"  ✗ Generation failed — skipping")
            continue

        badge   = BADGE_MAP.get(story["slug"], {"badge": "Tech", "color": "#2563EB"})
        img_url = pick_image(story["slug"], cache_key)

        record = {
            "headline":    article["headline"],
            "intro":       article["intro"],
            "paragraphs":  article["paragraphs"],
            "conclusion":  article["conclusion"],
            "key_insight": article["key_insight"],
            "category":    story["cat"],
            "cat_slug":    story["slug"],
            "cat_url":     f"{story['slug']}.html",
            "badge":       badge["badge"],
            "badge_color": badge["color"],
            "image":       img_url,
            "date":        today,
            "date_cached": datetime.now(timezone.utc).isoformat(),
        }

        cache[cache_key] = record
        output.append(record)
        print(f"  ✓ Generated: {article['headline'][:60]}…")

    # Save JSON
    if output:
        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUT_JSON.write_text(
            json.dumps({"updated": today, "stories": output}, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"\n✓ Saved {len(output)} trending articles → site/assets/data/trending.json")
        save_cache(cache)
    else:
        print("\n⚠ No articles generated — trending.json unchanged")

    print("\n" + "═"*55 + "\n")


if __name__ == "__main__":
    generate_trending()
