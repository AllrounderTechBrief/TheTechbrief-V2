"""
content_strategy.py — The Tech Brief V3
Website-level AdSense readiness: content plan, internal linking, site structure.
Generates a 25–40 article plan with proper intent mix and internal link graph.
"""

from typing import Optional

# ── 25–40 High-CPC Article Plan per Mix ────────────────────────────────────
# Distribution: Guides 40% | Explainers 30% | Comparisons 20% | News 10%

CONTENT_PLAN: list[dict] = [
    # ── AI / ML (8 articles) ────────────────────────────────────────────
    {"topic": "How to Deploy LLMs in Enterprise: Architecture, Cost, and Governance",
     "category": "ai_ml", "intent": "guide", "priority": 1},
    {"topic": "RAG vs Fine-Tuning: Which Approach Is Right for Your Use Case",
     "category": "ai_ml", "intent": "comparison", "priority": 1},
    {"topic": "What Is Agentic AI and How Do AI Agents Actually Work",
     "category": "ai_ml", "intent": "explainer", "priority": 1},
    {"topic": "AI Hallucination: Why It Happens and How to Reduce It in Production",
     "category": "ai_ml", "intent": "guide", "priority": 2},
    {"topic": "OpenAI vs Anthropic vs Google: Enterprise AI Platform Comparison 2025",
     "category": "ai_ml", "intent": "comparison", "priority": 2},
    {"topic": "Prompt Engineering Best Practices for Production LLM Applications",
     "category": "ai_ml", "intent": "guide", "priority": 2},
    {"topic": "Vector Databases Explained: Pinecone, Weaviate, and Chroma Compared",
     "category": "ai_ml", "intent": "comparison", "priority": 3},
    {"topic": "The State of AI Regulation in 2025: What the EU AI Act Means for Businesses",
     "category": "ai_ml", "intent": "news_analysis", "priority": 2},

    # ── Cybersecurity (7 articles) ──────────────────────────────────────
    {"topic": "Zero Trust Security Architecture: Implementation Guide for 2025",
     "category": "cybersecurity", "intent": "guide", "priority": 1},
    {"topic": "Ransomware Attack Anatomy: How Modern Attacks Work and How to Stop Them",
     "category": "cybersecurity", "intent": "explainer", "priority": 1},
    {"topic": "SIEM vs XDR: Which Security Platform Does Your Organisation Need",
     "category": "cybersecurity", "intent": "comparison", "priority": 2},
    {"topic": "Supply Chain Attacks: The Growing Threat to Software Security",
     "category": "cybersecurity", "intent": "explainer", "priority": 1},
    {"topic": "How to Conduct a Cybersecurity Risk Assessment: Step-by-Step",
     "category": "cybersecurity", "intent": "guide", "priority": 2},
    {"topic": "Phishing Attack Techniques in 2025: What Has Changed and What to Do",
     "category": "cybersecurity", "intent": "news_analysis", "priority": 2},
    {"topic": "Identity and Access Management: Why IAM Is Now a Board-Level Risk",
     "category": "cybersecurity", "intent": "explainer", "priority": 3},

    # ── Enterprise Tech (6 articles) ────────────────────────────────────
    {"topic": "Cloud Cost Optimisation: How to Reduce AWS and Azure Bills by 30%",
     "category": "enterprise_tech", "intent": "guide", "priority": 1},
    {"topic": "Kubernetes for Enterprise: Architecture, Cost, and Management Guide",
     "category": "enterprise_tech", "intent": "guide", "priority": 1},
    {"topic": "AWS vs Azure vs GCP: Enterprise Cloud Platform Comparison 2025",
     "category": "enterprise_tech", "intent": "comparison", "priority": 1},
    {"topic": "What Is Digital Transformation and Why 70% of Initiatives Fail",
     "category": "enterprise_tech", "intent": "explainer", "priority": 2},
    {"topic": "How to Build a Business Case for IT Investment",
     "category": "enterprise_tech", "intent": "guide", "priority": 2},
    {"topic": "Microservices vs Monolith: When Each Architecture Makes Sense",
     "category": "enterprise_tech", "intent": "comparison", "priority": 3},

    # ── EVs & Automotive (5 articles) ───────────────────────────────────
    {"topic": "Best Electric Cars of 2025: Range, Charging, and Value Compared",
     "category": "evs_automotive", "intent": "comparison", "priority": 1},
    {"topic": "Home EV Charging Setup: Complete Guide from Installation to Cost",
     "category": "evs_automotive", "intent": "guide", "priority": 1},
    {"topic": "Tesla vs Rivian vs Lucid: Which EV Brand Leads in 2025",
     "category": "evs_automotive", "intent": "comparison", "priority": 2},
    {"topic": "How Vehicle-to-Grid Technology Works and Why It Changes the EV Case",
     "category": "evs_automotive", "intent": "explainer", "priority": 2},
    {"topic": "EV Battery Degradation: What the Data Shows After 100,000 Miles",
     "category": "evs_automotive", "intent": "news_analysis", "priority": 2},

    # ── Mobile & Consumer (5 articles) ──────────────────────────────────
    {"topic": "Best Smartphones of 2025: iPhone vs Android Buying Guide",
     "category": "mobile_gadgets", "intent": "comparison", "priority": 1},
    {"topic": "How to Choose a Laptop for 2025: MacBook vs ThinkPad vs Dell XPS",
     "category": "consumer_tech", "intent": "guide", "priority": 1},
    {"topic": "What Is Wi-Fi 7 and Do You Actually Need It",
     "category": "consumer_tech", "intent": "explainer", "priority": 2},
    {"topic": "Best Noise-Cancelling Headphones 2025: Sony vs Apple vs Bose",
     "category": "consumer_tech", "intent": "comparison", "priority": 2},
    {"topic": "Apple vs Samsung in 2025: Which Ecosystem Makes More Sense",
     "category": "mobile_gadgets", "intent": "comparison", "priority": 2},

    # ── Startups & Business (4 articles) ────────────────────────────────
    {"topic": "How to Validate a B2B SaaS Business Model Before Building",
     "category": "startups_business", "intent": "guide", "priority": 1},
    {"topic": "Venture Capital in 2025: What Investors Are Looking For",
     "category": "startups_business", "intent": "explainer", "priority": 2},
    {"topic": "SaaS Metrics That Matter: ARR, NRR, CAC and Payback Period Explained",
     "category": "startups_business", "intent": "explainer", "priority": 2},
    {"topic": "AI Startups in 2025: The Funding Landscape and Where to Invest",
     "category": "startups_business", "intent": "news_analysis", "priority": 3},
]


def get_content_plan(
    max_articles: int = 35,
    categories: Optional[list[str]] = None,
    intents: Optional[list[str]] = None,
    priority_max: int = 3,
) -> list[dict]:
    """
    Return filtered, prioritised content plan.
    """
    plan = [a for a in CONTENT_PLAN if a["priority"] <= priority_max]

    if categories:
        plan = [a for a in plan if a["category"] in categories]
    if intents:
        plan = [a for a in plan if a["intent"] in intents]

    # Sort by priority then category diversity
    plan.sort(key=lambda a: (a["priority"], a["category"]))
    return plan[:max_articles]


def get_internal_link_graph() -> dict[str, list[str]]:
    """
    Generate a topic → related_topics linking graph.
    Each topic should link to 3–5 semantically related articles.
    """
    graph: dict[str, list[str]] = {}

    for article in CONTENT_PLAN:
        topic = article["topic"]
        category = article["category"]
        related = []

        for other in CONTENT_PLAN:
            if other["topic"] == topic:
                continue
            # Same category = strong relation
            if other["category"] == category:
                related.append(other["topic"])
            # Cross-category affinities
            elif (category == "ai_ml" and other["category"] in ("enterprise_tech", "cybersecurity")) \
              or (category == "cybersecurity" and other["category"] in ("enterprise_tech", "ai_ml")) \
              or (category == "evs_automotive" and other["category"] in ("consumer_tech", "startups_business")):
                related.append(other["topic"])

        graph[topic] = related[:5]  # Max 5 internal links per article

    return graph


def get_intent_distribution_report(plan: Optional[list[dict]] = None) -> dict:
    """Return intent distribution for the content plan."""
    if plan is None:
        plan = CONTENT_PLAN
    from collections import Counter
    intents = Counter(a["intent"] for a in plan)
    cats = Counter(a["category"] for a in plan)
    total = len(plan)
    return {
        "total_articles": total,
        "intent_distribution": {
            k: {"count": v, "pct": round(v/total*100, 1)}
            for k, v in intents.most_common()
        },
        "category_distribution": {
            k: {"count": v, "pct": round(v/total*100, 1)}
            for k, v in cats.most_common()
        },
        "adsense_mix_target": {
            "guides": "40%",
            "explainers": "30%",
            "comparisons": "20%",
            "news_analysis": "10%",
        },
        "meets_adsense_mix": (
            intents.get("guide", 0) / total >= 0.35
            and intents.get("explainer", 0) / total >= 0.25
        ),
    }


def get_site_structure_recommendations() -> dict:
    """
    Return full website structure recommendations for AdSense approval readiness.
    """
    return {
        "homepage": {
            "hero_section": "Intelligence positioning — 'Technology Analysis for Professionals'",
            "featured_section": "3 latest high-priority articles, auto-populated",
            "category_grid": "9 category tiles with article counts",
            "trending_section": "6 trending articles from RSS + Groq rewrites",
            "trust_signals": [
                "Article count badge",
                "Daily update indicator",
                "'Written by our editorial team' statement",
                "Privacy policy + cookie consent",
            ],
        },
        "article_pages": {
            "required_elements": [
                "Author name + date (top of article)",
                "Category badge with link",
                "Reading time indicator",
                "H1 → H2 → H3 heading hierarchy",
                "FAQ section (minimum 5 questions)",
                "Related articles section (3–5 links)",
                "Schema.org Article markup",
                "Canonical URL tag",
            ],
            "adsense_ad_slots": [
                "After introduction (before first H2)",
                "Mid-article (between H2 sections)",
                "After conclusion",
                "Sidebar (desktop only)",
            ],
        },
        "required_pages": {
            "about": {
                "required_content": [
                    "Editorial mission statement",
                    "Description of editorial process",
                    "Author/team description",
                    "Contact information",
                    "When the site was founded",
                ],
                "why": "AdSense reviewers check About pages for site legitimacy",
            },
            "contact": {
                "required_content": ["Contact form (Formspree)", "Email address", "Response time promise"],
                "why": "Required by Google Publisher Policies",
            },
            "privacy_policy": {
                "required_content": [
                    "Cookie usage disclosure",
                    "Google Analytics disclosure",
                    "Google AdSense disclosure",
                    "Data retention",
                    "User rights (GDPR/CCPA)",
                ],
                "why": "Mandatory for AdSense and GDPR compliance",
            },
            "editorial_policy": {
                "required_content": [
                    "How content is researched and written",
                    "Fact-checking process",
                    "Correction policy",
                    "Independence statement",
                    "Conflict of interest policy",
                ],
                "why": "Strong E-E-A-T signal — Google explicitly looks for this",
            },
            "disclaimer": {
                "required_content": [
                    "Affiliate link disclosure",
                    "Accuracy disclaimer",
                    "Professional advice disclaimer",
                ],
                "why": "Required by Google Publisher Policies for technology review sites",
            },
        },
        "seo_structure": {
            "url_pattern": "/articles/{slug}.html",
            "category_pages": "/{category-slug}.html",
            "sitemap": "auto-generated, submitted to Google Search Console",
            "robots_txt": "Allow: / with sitemap reference",
            "canonical_urls": "Every page has canonical tag",
            "hreflang": "Not required for single-language site",
        },
        "adsense_readiness_checklist": [
            "✓ Minimum 15–20 original, high-quality articles published",
            "✓ About page with editorial team description",
            "✓ Privacy Policy with AdSense and cookie disclosures",
            "✓ Contact page with working form",
            "✓ Editorial Policy page",
            "✓ No copied or scraped content",
            "✓ All articles 1200+ words",
            "✓ Consistent navigation and site structure",
            "✓ Mobile-responsive design",
            "✓ Fast page load (no unoptimised images)",
            "✓ HTTPS (automatic with GitHub Pages + custom domain)",
            "✓ Custom domain (not .github.io subdomain)",
            "✓ Google Search Console verified and site indexed",
            "✓ No broken internal links",
            "✓ No ad placeholders before AdSense approval",
        ],
    }
