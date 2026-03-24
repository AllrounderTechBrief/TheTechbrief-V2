"""
content_engine — The Tech Brief V3
Production-grade AdSense content system.

Modules:
  generator        — Main pipeline (1 API call per article)
  classifier       — Topic → category mapping
  prompt_builder   — Niche-aware Groq prompt construction
  scorer           — 6-dimension quality scoring (0–100)
  improver         — Local improvement engine (no API calls)
  safety_filter    — AdSense policy compliance checker
  enricher         — Author blocks, schema, meta, internal links
  cache            — Article cache with TTL
  content_strategy — 35-article content plan + site structure

Usage:
    from scripts.content_engine import generate_article, get_content_plan

    result = generate_article("Zero Trust Security Architecture", intent="guide")
    print(f"Score: {result['score']}/100 — {result['word_count']} words")
    print(f"AdSense ready: {result['adsense_ready']}")
"""

from .generator        import generate_article, get_token_usage_summary
from .scorer           import score_article
from .classifier       import classify_topic
from .content_strategy import get_content_plan, get_site_structure_recommendations, get_internal_link_graph

__all__ = [
    "generate_article",
    "get_token_usage_summary",
    "score_article",
    "classify_topic",
    "get_content_plan",
    "get_site_structure_recommendations",
    "get_internal_link_graph",
]
