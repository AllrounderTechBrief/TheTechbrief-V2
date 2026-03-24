"""
prompt_builder.py — The Tech Brief V3
Prompt Intelligence Layer: dynamically constructs optimised prompts
per niche, intent, and score feedback.
"""

from typing import Optional
from .classifier import get_category_config, Category

# ── Intent definitions ──────────────────────────────────────────────────────
INTENT_CONFIGS = {
    "guide": {
        "structure_instruction": "Write a comprehensive step-by-step guide.",
        "min_words": 1400,
        "required_elements": ["numbered steps", "common mistakes", "prerequisites", "expected outcomes"],
        "seo_intent": "informational",
    },
    "explainer": {
        "structure_instruction": "Write a deep explainer that builds understanding progressively.",
        "min_words": 1200,
        "required_elements": ["plain-English summary", "analogies", "real examples", "wider significance"],
        "seo_intent": "informational",
    },
    "comparison": {
        "structure_instruction": "Write a balanced, data-driven comparison.",
        "min_words": 1300,
        "required_elements": ["comparison table", "use-case scenarios", "winner per category", "final verdict"],
        "seo_intent": "commercial investigation",
    },
    "news_analysis": {
        "structure_instruction": "Write a news analysis piece — facts first, then expert-level interpretation.",
        "min_words": 1000,
        "required_elements": ["what happened", "why it matters", "expert perspective", "what's next"],
        "seo_intent": "informational",
    },
    "review": {
        "structure_instruction": "Write an authoritative hands-on review.",
        "min_words": 1400,
        "required_elements": ["verdict upfront", "detailed section scores", "who should buy", "alternatives"],
        "seo_intent": "commercial investigation",
    },
}


def build_prompt(
    topic: str,
    category: Category,
    intent: str = "guide",
    score_feedback: Optional[dict] = None,
) -> tuple[str, str]:
    """
    Build system + user prompts for Groq.
    Returns (system_prompt, user_prompt).
    """
    cat_config    = get_category_config(category)
    intent_config = INTENT_CONFIGS.get(intent, INTENT_CONFIGS["guide"])
    min_words     = intent_config["min_words"]

    # ── System prompt ────────────────────────────────────────────────────
    system = f"""You are a senior technology journalist and industry analyst writing for The Tech Brief — a premium, AdSense-approved technology intelligence platform.

WRITING PERSONA:
- Tone: {cat_config['tone']}
- Expertise level: expert — you have years of hands-on experience in {category.replace('_', ' ')}
- Voice: authoritative yet accessible — you explain complex things clearly without dumbing them down
- Style: {cat_config['tone_instruction']}

QUALITY RULES — STRICTLY ENFORCE:
1. Minimum {min_words} words of genuine substance (not padding)
2. Every paragraph must deliver unique value — no filler
3. Use specific named technologies, tools, versions, and vendors where relevant
4. Include realistic data points, percentages, and benchmarks (estimate realistically if exact figures unavailable)
5. Vary sentence length and structure — short punchy sentences mixed with detailed ones
6. Never start two consecutive paragraphs the same way
7. Never use these AI-tell phrases: "In conclusion", "It's worth noting", "It is important to note", "In today's digital landscape", "In this article", "Delve into", "Leverage", "Unleash"
8. Output clean, valid HTML5 with semantic structure

WHAT TO AVOID:
{chr(10).join(f'- {a}' for a in cat_config['avoid'])}

OUTPUT FORMAT: Raw HTML (no markdown, no code blocks, no explanation)"""

    # ── Score feedback injection (retry path) ────────────────────────────
    feedback_block = ""
    if score_feedback:
        weak_areas = [
            k for k, v in score_feedback.items()
            if isinstance(v, dict) and v.get("score", 100) < 70
        ]
        if weak_areas:
            feedback_block = f"""
CRITICAL IMPROVEMENT AREAS (previous attempt failed these):
{chr(10).join(f'- Improve: {area.replace("_", " ")}' for area in weak_areas)}
Pay special attention to these — they caused the content to fail quality checks.
"""

    # ── Required sections ─────────────────────────────────────────────────
    required_sections = cat_config.get("required_sections", [
        "Introduction", "Main Explanation", "Key Insights",
        "Pros and Cons", "Real-World Use Cases", "Who Should Care",
        "Common Mistakes", "Conclusion", "FAQs"
    ])

    sections_html = "\n".join([
        f"  <section id='{s.lower().replace(' ', '-').replace('/', '-')}'>"
        f"<h2>{s}</h2> ... </section>"
        for s in required_sections
    ])

    # ── High-CPC keyword weaving ──────────────────────────────────────────
    keywords = cat_config.get("high_cpc_keywords", [])[:4]
    keyword_instruction = ""
    if keywords:
        keyword_instruction = f"""
KEYWORD STRATEGY:
Naturally integrate these high-value keywords (no stuffing — use contextually):
{chr(10).join(f'- {kw}' for kw in keywords)}
Primary keyword should appear in: H1 title, first paragraph, one H2 subheading, meta description."""

    # ── User prompt ───────────────────────────────────────────────────────
    user = f"""Write a complete, high-quality, 100% original technology article for The Tech Brief.

TOPIC: {topic}
CATEGORY: {category.replace('_', ' ').title()}
INTENT: {intent_config['structure_instruction']}

{feedback_block}

REQUIRED ARTICLE STRUCTURE (use these exact HTML sections):
{sections_html}

REQUIRED ELEMENTS FOR THIS INTENT:
{chr(10).join(f'- {e}' for e in intent_config['required_elements'])}

FOCUS AREAS FOR THIS CATEGORY:
{chr(10).join(f'- {f}' for f in cat_config['focus_areas'])}

{keyword_instruction}

SEO REQUIREMENTS:
- H1 title: compelling, keyword-forward, max 65 characters
- Meta description: 140-155 chars, includes primary keyword, has a value proposition
- URL slug: lowercase, hyphens, max 60 characters
- H2 subheadings: 4-8, keyword-rich but natural
- Internal link opportunities: note 3-5 related topics in HTML comments <!-- INTERNAL_LINK: topic -->

CONTENT REQUIREMENTS:
- Word count: minimum {min_words} words of genuine substance
- Include at least 5 FAQs in a proper <div class="faq-section"> with <details>/<summary> markup
- End with a strong, specific conclusion — not a vague summary
- First sentence of article must be a compelling hook (not a definition)
- All sections must have at least 2 substantial paragraphs

OUTPUT: Complete HTML article only. Start with <article> tag. No explanations, no markdown."""

    return system, user
