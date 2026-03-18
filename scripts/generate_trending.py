#!/usr/bin/env python3
"""
generate_trending.py — The Streamic
────────────────────────────────────────────────────────────────────
Runs daily (via GitHub Actions at 05:30 UTC, after generate_articles.py).
Fetches the top 6 RSS stories from across all categories, then uses
Groq Llama 3 to write a full 400–500 word editorial article for each.
Saves everything to site/assets/data/trending.json.

STRICT RULES:
- Never copy or paraphrase text from RSS feeds.
- Use RSS topics ONLY as subject context — write entirely original prose.
- Never mention source publications by name.
- AdSense-safe, original, broadcast-industry editorial voice throughout.
────────────────────────────────────────────────────────────────────
"""

import os, sys, json, re, time, random, hashlib, requests
import feedparser
from datetime import datetime, timezone
from pathlib import Path

ROOT       = Path(__file__).resolve().parent.parent
OUT_JSON   = ROOT / "site" / "assets" / "data" / "trending.json"
CACHE_FILE = ROOT / "data" / "trending_cache.json"

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
MODEL        = "llama3-70b-8192"
SITE_URL     = "https://www.thestreamic.in"

# Top RSS feeds per category — diverse mix for trending
TRENDING_FEEDS = [
    {"cat": "Streaming",          "slug": "streaming",          "url": "https://www.streamingmediablog.com/feed"},
    {"cat": "Streaming",          "slug": "streaming",          "url": "https://mux.com/blog/feed/"},
    {"cat": "Cloud Production",   "slug": "cloud",              "url": "https://aws.amazon.com/blogs/media/feed/"},
    {"cat": "Cloud Production",   "slug": "cloud",              "url": "https://blog.frame.io/feed/"},
    {"cat": "AI & Post-Production","slug": "ai-post-production","url": "https://www.provideocoalition.com/feed/"},
    {"cat": "AI & Post-Production","slug": "ai-post-production","url": "https://postperspective.com/feed/"},
    {"cat": "Graphics",           "slug": "graphics",           "url": "https://motionographer.com/feed/"},
    {"cat": "Playout",            "slug": "playout",            "url": "https://www.tvtechnology.com/news/rss.xml"},
    {"cat": "Infrastructure",     "slug": "infrastructure",     "url": "https://www.tvbeurope.com/feed/"},
    {"cat": "Newsroom",           "slug": "newsroom",           "url": "https://www.newscaststudio.com/feed/"},
]

IMAGE_POOLS = {
    "streaming":          ["photo-1598488035139-bdbb2231ce04","photo-1516321497487-e288fb19713f","photo-1574717024653-61fd2cf4d44d","photo-1567095761054-7003afd47020","photo-1540575467063-178a50c2df87"],
    "cloud":              ["photo-1451187580459-43490279c0fa","photo-1544197150-b99a580bb7a8","photo-1560472355-536de3962603","photo-1504639725590-34d0984388bd","photo-1558494949-ef010cbdcc31"],
    "ai-post-production": ["photo-1677442135703-1787eea5ce01","photo-1620712943543-bcc4688e7485","photo-1655635643532-fa9ba2648cbe","photo-1533228100845-08145b01de14","photo-1635070041078-e363dbe005cb"],
    "graphics":           ["photo-1593642632559-0c6d3fc62b89","photo-1518770660439-4636190af475","photo-1547658719-da2b51169166","photo-1541462608143-67571c6738dd","photo-1568952433726-3896e3881c65"],
    "playout":            ["photo-1612420696760-0a0f34d3e7d0","photo-1478737270239-2f02b77fc618","photo-1598488035139-bdbb2231ce04","photo-1574717024653-61fd2cf4d44d","photo-1492619375914-88005aa9e8fb"],
    "infrastructure":     ["photo-1486312338219-ce68d2c6f44d","photo-1497366216548-37526070297c","photo-1560472354-b33ff0c44a43","photo-1553877522-43269d4ea984","photo-1504384308090-c894fdcc538d"],
    "newsroom":           ["photo-1504711434969-e33886168f5c","photo-1493863641943-9b68992a8d07","photo-1585829365295-ab7cd400c167","photo-1432821596592-e2c18b78144f","photo-1503428593586-e225b39bddfe"],
    "featured":           ["photo-1598488035139-bdbb2231ce04","photo-1478737270239-2f02b77fc618","photo-1567095761054-7003afd47020","photo-1486312338219-ce68d2c6f44d","photo-1451187580459-43490279c0fa"],
}

BADGE_MAP = {
    "streaming":          {"badge": "Streaming",    "color": "#0071e3"},
    "cloud":              {"badge": "Cloud",        "color": "#5856d6"},
    "ai-post-production": {"badge": "AI & Post",    "color": "#FF2D55"},
    "graphics":           {"badge": "Graphics",     "color": "#FF9500"},
    "playout":            {"badge": "Playout",      "color": "#34C759"},
    "infrastructure":     {"badge": "Infra",        "color": "#8E8E93"},
    "newsroom":           {"badge": "Newsroom",     "color": "#D4AF37"},
    "featured":           {"badge": "Featured",     "color": "#1d1d1f"},
}


def pick_image(slug: str, seed: str) -> str:
    pool = IMAGE_POOLS.get(slug, IMAGE_POOLS["featured"])
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
    stories = []
    for feed_cfg in TRENDING_FEEDS:
        try:
            feed = feedparser.parse(feed_cfg["url"])
            for entry in feed.entries[:3]:
                title = (entry.get("title") or "").strip()
                link  = (entry.get("link") or "").strip()
                if not title or not link or len(title) < 20:
                    continue
                ts    = entry.get("published_parsed") or entry.get("updated_parsed")
                ts_val = time.mktime(ts) if ts else 0
                stories.append({
                    "title":    title,
                    "link":     link,
                    "cat":      feed_cfg["cat"],
                    "slug":     feed_cfg["slug"],
                    "ts":       ts_val,
                    "feed_url": feed_cfg["url"],
                })
        except Exception as ex:
            print(f"  Feed error {feed_cfg['url']}: {ex}")

    stories.sort(key=lambda x: x["ts"], reverse=True)
    seen   = set()
    deduped = []
    for s in stories:
        key = s["title"][:40].lower()
        if key not in seen:
            deduped.append(s)
            seen.add(key)
    return deduped[:n]


def call_groq_trending(title: str, category: str) -> dict | None:
    if not GROQ_API_KEY:
        return None

    system = (
        "You are a senior broadcast technology journalist at The Streamic, an independent "
        "publication covering professional broadcast and streaming technology. "
        "Your readers are broadcast engineers, production managers, and media technology "
        "professionals. Write at their level with technical authority. "
        "You write 100% original editorial content. "
        "You NEVER copy, quote, or reference any external source, publication, or website. "
        "Return ONLY valid JSON — no markdown fences, no preamble."
    )

    user = f"""Write a full 400–500 word original broadcast technology article for The Streamic's trending section.

Topic context (use as subject inspiration ONLY — do NOT copy or reference this headline):
"{title}"
Category: {category}

Return a JSON object with EXACTLY this structure:
{{
  "headline": "A sharp, specific broadcast-industry headline (8-12 words) — NOT a copy of the input",
  "intro": "A powerful 2-sentence opening that immediately hooks the broadcast professional reader",
  "paragraphs": [
    "First body paragraph (80-100 words) — what is happening technically and why it matters to broadcast ops",
    "Second body paragraph (80-100 words) — industry context, who is deploying this, what it replaces",
    "Third body paragraph (80-100 words) — implications for operations teams, vendors, or workflows",
    "Fourth body paragraph (80-100 words) — broader technology trend this reflects in broadcast/streaming"
  ],
  "conclusion": "A 2-sentence forward-looking conclusion for a broadcast engineer audience",
  "key_insight": "One sharp sentence (max 20 words) — the single most important technical takeaway"
}}

Rules:
- Every word must be 100% original — written by you, not lifted from any source
- No source attributions, no brand-name references unless they are generic industry terms
- Technical depth matters: reference protocols, standards, or architectures where appropriate
- Confident, analytical, industry-expert tone
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
            raw  = resp.json()["choices"][0]["message"]["content"].strip()
            raw  = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
            raw  = re.sub(r"\s*```$", "", raw.strip()).strip()
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

    today = today_str()
    cache = load_cache()

    print("\n" + "═"*55)
    print("  The Streamic — Trending Article Generator")
    print(f"  Date: {today}")
    print("═"*55)

    print("\nFetching top RSS stories across all categories…")
    stories = fetch_top_stories(12)
    print(f"  Found {len(stories)} candidate stories")

    selected  = []
    used_cats = set()
    for story in stories:
        if story["slug"] not in used_cats and len(selected) < 6:
            selected.append(story)
            used_cats.add(story["slug"])
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

        if cached and cached.get("date") == today:
            print(f"  ✓ Using today's cache")
            output.append(cached)
            continue

        print(f"  ✍  Calling Groq Llama 3…")
        article = call_groq_trending(story["title"], story["cat"])

        if not article:
            print(f"  ✗ Generation failed — skipping")
            continue

        badge   = BADGE_MAP.get(story["slug"], {"badge": "Broadcast", "color": "#0071e3"})
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
