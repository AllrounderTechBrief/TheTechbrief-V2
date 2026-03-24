#!/usr/bin/env python3
"""
run_content_engine.py — The Tech Brief V3
CLI runner for the production AdSense content system.

Usage:
    # Generate a single article
    python scripts/run_content_engine.py --topic "Zero Trust Security" --intent guide

    # Run the full content plan (generates all 35 priority articles)
    python scripts/run_content_engine.py --plan --max 10

    # Score an existing HTML file
    python scripts/run_content_engine.py --score path/to/article.html

    # Show site readiness report
    python scripts/run_content_engine.py --site-report

    # Show content plan
    python scripts/run_content_engine.py --show-plan

Environment:
    GROQ_API_KEY    — required for article generation
    GROQ_DAILY_CAP  — optional, default 50
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.content_engine import (
    generate_article,
    score_article,
    classify_topic,
    get_content_plan,
    get_site_structure_recommendations,
    get_internal_link_graph,
    get_token_usage_summary,
)
from scripts.content_engine.content_strategy import get_intent_distribution_report

# ── Output paths ────────────────────────────────────────────────────────────
ARTICLES_OUT = ROOT / "docs" / "articles"
DATA_OUT     = ROOT / "data"
LOG_FILE     = ROOT / "data" / "content_engine.log"


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
        ],
    )


def save_article(result: dict) -> Path:
    """Save generated article HTML to docs/articles/."""
    ARTICLES_OUT.mkdir(parents=True, exist_ok=True)
    slug = result["slug"]
    out_path = ARTICLES_OUT / f"{slug}.html"
    out_path.write_text(result["html"], encoding="utf-8")
    return out_path


def save_metadata(result: dict) -> Path:
    """Save article metadata JSON for build pipeline consumption."""
    DATA_OUT.mkdir(parents=True, exist_ok=True)

    # Load existing generated_articles.json
    gen_file = DATA_OUT / "generated_articles.json"
    existing = []
    if gen_file.exists():
        try:
            existing = json.loads(gen_file.read_text(encoding="utf-8"))
        except Exception:
            existing = []

    # Build metadata entry
    entry = {
        "title":              result["title"],
        "slug":               result["slug"],
        "url":                f"articles/{result['slug']}.html",
        "category":           result["category"],
        "cat_slug":           result["category"].replace("_", "-").replace("ml", "news"),
        "meta_description":   result["meta_description"],
        "primary_keyword":    result["primary_keyword"],
        "word_count":         result["word_count"],
        "reading_time":       result["reading_time"],
        "score":              result["score"],
        "adsense_ready":      result["adsense_ready"],
        "date":               result["pub_date"],
        "pub_date":           result["pub_date"],
        "pub_date_fmt":       datetime.strptime(result["pub_date"], "%Y-%m-%d").strftime("%B %d, %Y"),
        "generated_at":       result["generated_at"],
        "image_url":          f"https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=800&q=80",
    }

    # Remove duplicate by slug, then prepend
    existing = [e for e in existing if e.get("slug") != entry["slug"]]
    existing.insert(0, entry)

    # Keep max 100 articles in JSON
    existing = existing[:100]
    gen_file.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    return gen_file


def print_score_report(score_result: dict):
    """Print a formatted score breakdown."""
    print(f"\n{'='*60}")
    print(f"  QUALITY SCORE: {score_result['total']}/100 — {score_result['grade']}")
    print(f"{'='*60}")
    print(f"  Words:    {score_result.get('word_count', '—')}")
    print(f"  AdSense:  {'✓ READY' if score_result['adsense_ready'] else '✗ NEEDS WORK'}")
    print(f"\n  DIMENSION BREAKDOWN:")
    for dim, data in score_result["breakdown"].items():
        bar = "█" * (data["score"] // 10) + "░" * (10 - data["score"] // 10)
        print(f"    {dim:<15} {bar} {data['score']:>3}/100")
    if score_result["all_issues"]:
        print(f"\n  ISSUES TO FIX ({len(score_result['all_issues'])}):")
        for issue in score_result["all_issues"][:10]:
            print(f"    • {issue}")
    print(f"{'='*60}\n")


def cmd_generate(args):
    """Generate a single article."""
    print(f"\n🚀 Generating: {args.topic}")
    print(f"   Category: {args.category or 'auto-detect'}")
    print(f"   Intent: {args.intent}")
    print(f"   Force regen: {args.force}\n")

    result = generate_article(
        topic=args.topic,
        category=args.category or None,
        intent=args.intent,
        force_regen=args.force,
    )

    print_score_report({"total": result["score"], "grade": "", "word_count": result["word_count"],
                        "adsense_ready": result["adsense_ready"], "breakdown": result["score_breakdown"],
                        "all_issues": []})

    # Save outputs
    html_path = save_article(result)
    meta_path = save_metadata(result)

    usage = get_token_usage_summary()
    print(f"✅ Article saved: {html_path}")
    print(f"   Metadata: {meta_path}")
    print(f"   Score: {result['score']}/100 | Words: {result['word_count']} | AdSense: {'✓' if result['adsense_ready'] else '✗'}")
    print(f"   Tokens used this session: {usage['total_tokens']}")
    return result


def cmd_run_plan(args):
    """Generate articles from the content plan."""
    plan = get_content_plan(max_articles=args.max, priority_max=args.priority)
    print(f"\n📋 Content Plan: {len(plan)} articles to generate")
    print(f"   API cap: {os.environ.get('GROQ_DAILY_CAP', '50')} calls/day\n")

    results = []
    failed  = []

    for i, article in enumerate(plan, 1):
        print(f"[{i}/{len(plan)}] {article['topic'][:60]}…")
        try:
            result = generate_article(
                topic=article["topic"],
                category=article["category"],
                intent=article["intent"],
            )
            save_article(result)
            save_metadata(result)
            results.append(result)
            status = "✓" if result["adsense_ready"] else "⚠"
            print(f"      {status} Score: {result['score']}/100 | Words: {result['word_count']}")
        except Exception as e:
            failed.append({"topic": article["topic"], "error": str(e)})
            print(f"      ✗ Failed: {e}")

    # Summary
    usage = get_token_usage_summary()
    print(f"\n{'='*50}")
    print(f"  PLAN COMPLETE")
    print(f"  Generated:     {len(results)}/{len(plan)}")
    print(f"  Failed:        {len(failed)}")
    print(f"  AdSense ready: {sum(1 for r in results if r['adsense_ready'])}")
    print(f"  Avg score:     {sum(r['score'] for r in results) // max(len(results),1)}/100")
    print(f"  Total tokens:  {usage['total_tokens']}")
    print(f"{'='*50}\n")


def cmd_score(args):
    """Score an existing HTML file."""
    path = Path(args.file)
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    html = path.read_text(encoding="utf-8")
    topic = path.stem.replace("-", " ")
    result = score_article(html, topic)
    print_score_report(result)


def cmd_site_report(args):
    """Print full site readiness report."""
    rec = get_site_structure_recommendations()
    dist = get_intent_distribution_report()

    print(f"\n{'='*60}")
    print(f"  THE TECH BRIEF — ADSENSE READINESS REPORT")
    print(f"{'='*60}\n")

    print("📋 CONTENT PLAN STATS:")
    print(f"   Total planned articles: {dist['total_articles']}")
    print(f"   AdSense mix target met: {'✓' if dist['meets_adsense_mix'] else '✗'}")
    print("\n   Intent distribution:")
    for intent, data in dist["intent_distribution"].items():
        print(f"     {intent:<20} {data['count']} articles ({data['pct']}%)")
    print("\n   Category distribution:")
    for cat, data in dist["category_distribution"].items():
        print(f"     {cat:<25} {data['count']} articles ({data['pct']}%)")

    print(f"\n✅ ADSENSE READINESS CHECKLIST:")
    for item in rec["adsense_readiness_checklist"]:
        print(f"   {item}")

    print(f"\n🏗️  REQUIRED PAGES:")
    for page, info in rec["required_pages"].items():
        print(f"\n   {page.upper()}")
        print(f"   Why: {info['why']}")
        for item in info["required_content"][:3]:
            print(f"   • {item}")

    print(f"\n📍 ADSENSE AD SLOT POSITIONS:")
    for slot in rec["article_pages"]["adsense_ad_slots"]:
        print(f"   • {slot}")
    print()


def cmd_show_plan(args):
    """Display the content plan."""
    plan = get_content_plan(max_articles=args.max)
    print(f"\n📋 CONTENT PLAN ({len(plan)} articles)\n")
    current_cat = None
    for i, article in enumerate(plan, 1):
        if article["category"] != current_cat:
            current_cat = article["category"]
            print(f"\n  [{current_cat.upper().replace('_',' ')}]")
        print(f"  {i:2}. [{article['intent']:<13}] {article['topic']}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="The Tech Brief V3 — AdSense Content Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-v", "--verbose", action="store_true")

    sub = parser.add_subparsers(dest="command")

    # generate
    gen_p = sub.add_parser("generate", help="Generate a single article")
    gen_p.add_argument("--topic",    required=True)
    gen_p.add_argument("--category", default=None)
    gen_p.add_argument("--intent",   default="guide",
                       choices=["guide", "explainer", "comparison", "news_analysis", "review"])
    gen_p.add_argument("--force",    action="store_true", help="Bypass cache")

    # plan
    plan_p = sub.add_parser("plan", help="Generate from content plan")
    plan_p.add_argument("--max",      type=int, default=10)
    plan_p.add_argument("--priority", type=int, default=2, choices=[1, 2, 3])

    # score
    score_p = sub.add_parser("score", help="Score an existing HTML file")
    score_p.add_argument("--file", required=True)

    # site-report
    sub.add_parser("site-report", help="Show full AdSense readiness report")

    # show-plan
    sp = sub.add_parser("show-plan", help="Display the content plan")
    sp.add_argument("--max", type=int, default=40)

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "plan":
        cmd_run_plan(args)
    elif args.command == "score":
        cmd_score(args)
    elif args.command == "site-report":
        cmd_site_report(args)
    elif args.command == "show-plan":
        cmd_show_plan(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
