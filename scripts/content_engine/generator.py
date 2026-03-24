"""
generator.py — The Tech Brief V3
Content Generator Module: 1 Groq API call per article, intelligence-grade output.
"""

import os
import re
import json
import time
import hashlib
import logging
import requests
from datetime import datetime, timezone
from typing import Optional

from .classifier import classify_topic
from .prompt_builder import build_prompt
from .scorer import score_article
from .improver import improve_article
from .safety_filter import adsense_safety_check
from .enricher import enrich_article
from .cache import ArticleCache

logger = logging.getLogger("techbrief.generator")

# ── Config ─────────────────────────────────────────────────────────────────
GROQ_API_KEY  = os.environ.get("GROQ_API_KEY", "")
GROQ_URL      = "https://api.groq.com/openai/v1/chat/completions"
MODEL         = "llama3-70b-8192"
DAILY_API_CAP = int(os.environ.get("GROQ_DAILY_CAP", "50"))
MIN_SCORE     = 60  # Only retry if score < this (hard fail threshold)

# Token usage log
_usage_log: list[dict] = []


def _groq_call(system: str, user: str, max_tokens: int = 2000) -> tuple[str, dict]:
    """
    Single Groq API call. Returns (content, usage_stats).
    Raises on failure — caller decides whether to retry.
    """
    if not GROQ_API_KEY:
        raise EnvironmentError("GROQ_API_KEY not set")

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.75,
        "top_p": 0.95,
    }
    resp = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"].strip()
    usage   = data.get("usage", {})
    return content, usage


def _log_usage(topic: str, usage: dict):
    entry = {
        "topic": topic[:60],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_tokens":     usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens":      usage.get("total_tokens", 0),
    }
    _usage_log.append(entry)
    logger.info(
        "Token usage — prompt: %d, completion: %d, total: %d",
        entry["prompt_tokens"], entry["completion_tokens"], entry["total_tokens"]
    )


def _check_daily_cap() -> int:
    """Return number of API calls made today. Raise if over cap."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_count = sum(
        1 for e in _usage_log
        if e["timestamp"].startswith(today)
    )
    if today_count >= DAILY_API_CAP:
        raise RuntimeError(
            f"Daily API cap reached ({DAILY_API_CAP} calls). "
            "Increase GROQ_DAILY_CAP or wait until tomorrow."
        )
    return today_count


def generate_article(
    topic: str,
    category: Optional[str] = None,
    intent: str = "guide",
    force_regen: bool = False,
) -> dict:
    """
    Main entry point. Full pipeline:
      classify → build_prompt → groq (1 call) → score →
      improve (local) → safety_check → enrich → return

    Returns a rich dict with html, score, metadata, seo fields.
    """
    logger.info("Starting pipeline: topic=%r category=%s intent=%s", topic, category, intent)

    # ── Step 0: Cache lookup ───────────────────────────────────────────────
    cache = ArticleCache()
    cache_key = hashlib.md5(f"{topic}::{intent}".encode()).hexdigest()
    if not force_regen:
        cached = cache.get(cache_key)
        if cached:
            logger.info("Cache hit for %r — skipping API call", topic)
            return cached

    # ── Step 1: Classification ─────────────────────────────────────────────
    if not category:
        category = classify_topic(topic)
    logger.info("Classified as: %s", category)

    # ── Step 2: Prompt Construction ────────────────────────────────────────
    system_prompt, user_prompt = build_prompt(topic, category, intent)

    # ── Step 3: API Call (exactly 1) ───────────────────────────────────────
    _check_daily_cap()
    raw_content = ""
    usage = {}
    try:
        logger.info("Calling Groq API…")
        raw_content, usage = _groq_call(system_prompt, user_prompt, max_tokens=2200)
        _log_usage(topic, usage)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            logger.warning("Rate limited — waiting 20s then retrying once")
            time.sleep(20)
            raw_content, usage = _groq_call(system_prompt, user_prompt, max_tokens=2200)
            _log_usage(topic, usage)
        else:
            raise

    # ── Step 4: Score ──────────────────────────────────────────────────────
    score_result = score_article(raw_content, topic, category)
    logger.info(
        "Initial score: %d/100 — %s",
        score_result["total"],
        score_result["summary"]
    )

    # ── Step 5: Retry only on hard fail (score < MIN_SCORE) ───────────────
    if score_result["total"] < MIN_SCORE:
        logger.warning(
            "Score %d below threshold %d — retrying with enhanced prompt",
            score_result["total"], MIN_SCORE
        )
        _check_daily_cap()
        enhanced_system, enhanced_user = build_prompt(
            topic, category, intent,
            score_feedback=score_result["breakdown"]
        )
        raw_content, usage2 = _groq_call(enhanced_system, enhanced_user, max_tokens=2400)
        _log_usage(topic, usage2)
        score_result = score_article(raw_content, topic, category)
        logger.info("Retry score: %d/100", score_result["total"])

    # ── Step 6: Local Improvement (NO API calls) ───────────────────────────
    improved_content = improve_article(raw_content, score_result["breakdown"], topic, category)
    score_after_improvement = score_article(improved_content, topic, category)
    logger.info("Score after local improvement: %d/100", score_after_improvement["total"])

    # ── Step 7: AdSense Safety Filter ─────────────────────────────────────
    safety_result = adsense_safety_check(improved_content)
    if not safety_result["passed"]:
        logger.warning("Safety filter triggered: %s — auto-fixing", safety_result["issues"])
        improved_content = safety_result["fixed_content"]

    # ── Step 8: Content Enrichment ─────────────────────────────────────────
    pub_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    final = enrich_article(
        content=improved_content,
        topic=topic,
        category=category,
        intent=intent,
        pub_date=pub_date,
        score=score_after_improvement,
    )

    # ── Step 9: Cache + return ─────────────────────────────────────────────
    result = {
        "topic":      topic,
        "category":   category,
        "intent":     intent,
        "pub_date":   pub_date,
        "html":       final["html"],
        "title":      final["title"],
        "slug":       final["slug"],
        "meta_description": final["meta_description"],
        "primary_keyword":  final["primary_keyword"],
        "secondary_keywords": final["secondary_keywords"],
        "word_count": final["word_count"],
        "reading_time": final["reading_time"],
        "author_block": final["author_block"],
        "internal_links": final["internal_links"],
        "score": score_after_improvement["total"],
        "score_breakdown": score_after_improvement["breakdown"],
        "token_usage": usage,
        "adsense_ready": score_after_improvement["total"] >= 72 and safety_result["passed"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    cache.set(cache_key, result)
    logger.info(
        "Pipeline complete — score: %d, words: %d, adsense_ready: %s",
        result["score"], result["word_count"], result["adsense_ready"]
    )
    return result


def get_token_usage_summary() -> dict:
    """Return aggregated token usage stats."""
    if not _usage_log:
        return {"calls": 0, "total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}
    return {
        "calls": len(_usage_log),
        "total_tokens":      sum(e["total_tokens"] for e in _usage_log),
        "prompt_tokens":     sum(e["prompt_tokens"] for e in _usage_log),
        "completion_tokens": sum(e["completion_tokens"] for e in _usage_log),
        "log": _usage_log,
    }
