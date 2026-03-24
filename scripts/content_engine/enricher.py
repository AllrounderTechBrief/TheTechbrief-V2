"""
enricher.py — The Tech Brief V3
Content Enrichment Layer: adds author block, dates, meta, internal links,
SEO anchors, schema markup, and slug generation.
"""

import re
import json
import hashlib
from datetime import datetime, timezone
from bs4 import BeautifulSoup

SITE_URL = "https://www.thetechbrief.net"

# ── Category to page mapping ────────────────────────────────────────────────
CAT_PAGE_MAP = {
    "cybersecurity":    ("cybersecurity-updates.html", "🔐", "#DC2626"),
    "enterprise_tech":  ("enterprise-tech.html",       "🏢", "#1A56DB"),
    "consumer_tech":    ("consumer-tech.html",         "🛒", "#0891B2"),
    "evs_automotive":   ("evs-automotive.html",        "🚗", "#059669"),
    "ai_ml":            ("ai-news.html",               "🤖", "#7C3AED"),
    "space_science":    ("ai-news.html",               "🔭", "#2563EB"),
    "mobile_gadgets":   ("mobile-gadgets.html",        "📱", "#0891B2"),
    "gaming":           ("gaming.html",                "🎮", "#7C3AED"),
    "startups_business":("startups-business.html",     "💼", "#D97706"),
    "broadcast_tech":   ("broadcast-tech.html",        "📡", "#BE185D"),
}

# ── Reading speed (words per minute) ───────────────────────────────────────
WPM = 230


def _make_slug(title: str) -> str:
    """Convert title to clean URL slug."""
    slug = re.sub(r'[^\w\s-]', '', title.lower())
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug[:70]


def _extract_title(html: str, topic: str) -> str:
    """Extract H1 title from HTML, fallback to topic."""
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    return h1.get_text(strip=True) if h1 else topic


def _extract_meta_description(html: str, topic: str, word_count: int) -> str:
    """Extract or generate meta description."""
    soup = BeautifulSoup(html, "html.parser")

    # Check for existing meta tag
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content") and len(meta["content"]) > 100:
        return meta["content"]

    # Extract from HTML comment
    comment_match = re.search(r'<!--\s*META:\s*(.+?)\s*-->', html)
    if comment_match:
        return comment_match.group(1)[:155]

    # Generate from first paragraph
    first_p = soup.find("p")
    if first_p:
        text = first_p.get_text(strip=True)
        if len(text) > 120:
            return text[:152] + "…"

    return f"Expert analysis of {topic} — covering key technologies, practical applications, and strategic insights for technology professionals."[:155]


def _extract_primary_keyword(html: str, topic: str) -> str:
    """Extract the most likely primary keyword."""
    # Clean topic to keyword
    stop_words = {"the", "a", "an", "of", "in", "on", "at", "to", "for",
                  "with", "by", "from", "is", "are", "was", "were", "how",
                  "what", "why", "when", "where", "which"}
    words = [w.lower() for w in topic.split() if w.lower() not in stop_words]
    return " ".join(words[:4]) if words else topic.lower()


def _extract_secondary_keywords(html: str, topic: str, category: str) -> list[str]:
    """Extract 3-5 secondary keyword phrases from headings."""
    soup = BeautifulSoup(html, "html.parser")
    headings = [h.get_text(strip=True) for h in soup.find_all(["h2", "h3"])]

    keywords = []
    for heading in headings[:8]:
        # Clean heading to keyword phrase
        clean = re.sub(r'[^\w\s]', '', heading.lower()).strip()
        if 15 < len(clean) < 60:
            keywords.append(clean)

    return keywords[:5]


def _extract_word_count(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    return len(re.findall(r'\b\w+\b', text))


def _build_author_block(category: str, pub_date: str) -> str:
    """Build a consistent, AdSense-friendly author block."""
    cat_page, cat_icon, cat_color = CAT_PAGE_MAP.get(category, ("index.html", "📰", "#1A56DB"))
    try:
        dt = datetime.strptime(pub_date, "%Y-%m-%d")
        formatted_date = dt.strftime("%B %d, %Y")
    except Exception:
        formatted_date = pub_date

    return f"""
<div class="article-author-block" style="display:flex;align-items:center;gap:14px;padding:16px 20px;background:#F6F6FA;border-radius:8px;margin:20px 0 28px;border:1px solid #E0E0EC;">
  <div style="width:44px;height:44px;background:{cat_color};border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;">{cat_icon}</div>
  <div>
    <div style="font-weight:700;color:#0A0A10;font-size:14px;">The Tech Brief Editorial Team</div>
    <div style="font-size:12px;color:#72728A;margin-top:2px;">
      Published <time datetime="{pub_date}">{formatted_date}</time> &middot;
      Updated <time datetime="{pub_date}">{formatted_date}</time> &middot;
      <a href="{cat_page}" style="color:#1A56DB;">{category.replace('_',' ').title()}</a>
    </div>
  </div>
</div>"""


def _build_schema_markup(
    title: str,
    description: str,
    pub_date: str,
    slug: str,
    category: str,
    word_count: int,
) -> str:
    """Generate Article schema.org markup."""
    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "datePublished": pub_date,
        "dateModified": pub_date,
        "wordCount": word_count,
        "author": {
            "@type": "Organization",
            "name": "The Tech Brief Editorial Team",
            "url": SITE_URL + "/about.html",
        },
        "publisher": {
            "@type": "Organization",
            "name": "The Tech Brief",
            "url": SITE_URL,
            "logo": {
                "@type": "ImageObject",
                "url": SITE_URL + "/assets/favicon.svg",
            },
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": f"{SITE_URL}/articles/{slug}.html",
        },
        "articleSection": category.replace("_", " ").title(),
        "inLanguage": "en-GB",
    }
    return f'<script type="application/ld+json">\n{json.dumps(schema, indent=2)}\n</script>'


def _inject_internal_link_placeholders(html: str, category: str, topic: str) -> tuple[str, list[str]]:
    """
    Find opportunities for internal links and inject HTML comments.
    Also returns a list of suggested internal link topics.
    """
    CAT_RELATED_TOPICS = {
        "cybersecurity": [
            "cybersecurity-updates.html", "enterprise-tech.html", "ai-news.html"
        ],
        "enterprise_tech": [
            "enterprise-tech.html", "ai-news.html", "cybersecurity-updates.html"
        ],
        "ai_ml": [
            "ai-news.html", "enterprise-tech.html", "startups-business.html"
        ],
        "evs_automotive": [
            "evs-automotive.html", "consumer-tech.html", "startups-business.html"
        ],
        "consumer_tech": [
            "consumer-tech.html", "mobile-gadgets.html", "gaming.html"
        ],
        "mobile_gadgets": [
            "mobile-gadgets.html", "consumer-tech.html", "ai-news.html"
        ],
        "gaming": [
            "gaming.html", "consumer-tech.html", "enterprise-tech.html"
        ],
        "startups_business": [
            "startups-business.html", "enterprise-tech.html", "ai-news.html"
        ],
        "broadcast_tech": [
            "broadcast-tech.html", "enterprise-tech.html", "ai-news.html"
        ],
    }

    related_pages = CAT_RELATED_TOPICS.get(category, ["index.html"])
    suggestions = [f"{SITE_URL}/{p}" for p in related_pages]

    # Inject placeholder comments at H2 boundaries
    soup = BeautifulSoup(html, "html.parser")
    h2s = soup.find_all("h2")
    link_idx = 0

    for i, h2 in enumerate(h2s[1:4], 1):  # Max 3 internal links
        if link_idx < len(related_pages):
            comment_tag = BeautifulSoup(
                f'<!-- INTERNAL_LINK: {related_pages[link_idx]} -->',
                'html.parser'
            )
            h2.insert_before(NavigableString(
                f'\n<!-- INTERNAL_LINK: {related_pages[link_idx]} -->\n'
            ))
            link_idx += 1

    return str(soup), suggestions


def _add_meta_tags_to_html(html: str, title: str, description: str, slug: str) -> str:
    """Inject meta description if not present."""
    if 'name="description"' in html:
        return html

    meta_tag = f'<meta name="description" content="{description}">'
    canonical_tag = f'<link rel="canonical" href="{SITE_URL}/articles/{slug}.html">'

    if "<head>" in html:
        return html.replace("<head>", f"<head>\n  {meta_tag}\n  {canonical_tag}")
    return html


def enrich_article(
    content: str,
    topic: str,
    category: str,
    intent: str,
    pub_date: str,
    score: dict,
) -> dict:
    """
    Main entry point. Enrich article with all required metadata and elements.
    Returns a rich dict with html, title, slug, meta, keywords, author block, etc.
    """
    word_count   = _extract_word_count(content)
    reading_time = max(1, round(word_count / WPM))
    title        = _extract_title(content, topic)
    slug         = _make_slug(title)
    meta_desc    = _extract_meta_description(content, topic, word_count)
    primary_kw   = _extract_primary_keyword(content, topic)
    secondary_kw = _extract_secondary_keywords(content, topic, category)
    author_block = _build_author_block(category, pub_date)
    schema       = _build_schema_markup(title, meta_desc, pub_date, slug, category, word_count)

    # Inject internal link placeholders
    enriched_html, internal_links = _inject_internal_link_placeholders(content, category, topic)

    # Add meta tags
    enriched_html = _add_meta_tags_to_html(enriched_html, title, meta_desc, slug)

    # Inject author block after H1
    soup = BeautifulSoup(enriched_html, "html.parser")
    h1 = soup.find("h1")
    if h1:
        author_soup = BeautifulSoup(author_block, "html.parser")
        h1.insert_after(author_soup)
        enriched_html = str(soup)

    # Prepend schema
    enriched_html = schema + "\n" + enriched_html

    return {
        "html":               enriched_html,
        "title":              title,
        "slug":               slug,
        "meta_description":   meta_desc,
        "primary_keyword":    primary_kw,
        "secondary_keywords": secondary_kw,
        "word_count":         word_count,
        "reading_time":       f"{reading_time} min read",
        "author_block":       author_block,
        "internal_links":     internal_links,
        "pub_date":           pub_date,
        "category_page":      CAT_PAGE_MAP.get(category, ("index.html",))[0],
        "schema_markup":      schema,
    }


# Import needed for NavigableString
from bs4 import NavigableString
