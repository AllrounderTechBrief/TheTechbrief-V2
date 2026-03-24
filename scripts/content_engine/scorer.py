"""
scorer.py — The Tech Brief V3
Advanced Scoring Engine: 6-dimension quality analysis.
Returns score 0–100 with detailed breakdown. NO API calls.
"""

import re
import math
from collections import Counter
from typing import Optional
from bs4 import BeautifulSoup


# ── Weights (must sum to 100) ───────────────────────────────────────────────
WEIGHTS = {
    "structural":    20,
    "readability":   18,
    "ai_detection":  20,
    "depth":         22,
    "seo":           10,
    "value":         10,
}

# ── AI-tell phrases (instant deduction) ────────────────────────────────────
AI_TELLS = [
    r"\bin today'?s? (?:digital |fast-?paced |ever-?changing )?(?:world|landscape|era|age)\b",
    r"\bit(?:'s| is) (?:worth|important to) (?:noting|mention|consider)\b",
    r"\bin (?:this|the following) article[,\s]",
    r"\bwithout further ado\b",
    r"\blet'?s (?:dive|delve) (?:in|into)\b",
    r"\bas (?:we|you) (?:can see|explore|navigate)\b",
    r"\bthe (?:ever-?evolving|rapidly changing|fast-?paced)\b",
    r"\bin conclusion[,\s]",
    r"\bto (?:summarize|summarise|conclude|wrap up)\b",
    r"\bthe (?:world|landscape|ecosystem) of [\w\s]+is (?:evolving|changing|growing)\b",
    r"\bfundamental(?:ly)? (?:transform|change|reshape|revolutionize)\b",
    r"\bempower(?:ing)? (?:businesses|organizations|individuals|users)\b",
    r"\bunlock(?:ing)? (?:the|new|full)? (?:potential|power|value)\b",
    r"\bleverage (?:the|this|these|your)\b",
    r"\bseamless(?:ly)?\b",
    r"\bbespoke\b",
    r"\brobust solution\b",
    r"\bsynergy\b",
    r"\bgame[-\s]changer\b",
    r"\bcutting[-\s]edge\b",
    r"\bgroundbreaking\b",
    r"\bstate[-\s]of[-\s]the[-\s]art\b",
    r"\bright[- ]?click\b.*\bai\b",
]

# ── Generic openings ────────────────────────────────────────────────────────
GENERIC_OPENINGS = [
    r"^<[^>]+>\s*(?:in today|with the rise|the world of|as technology|technology (?:has|is|continues))",
    r"^<[^>]+>\s*(?:have you ever wondered|are you looking for|do you want to)",
    r"^<[^>]+>\s*\w+ (?:is|are) (?:a|an) (?:important|crucial|vital|key|essential)",
]

# ── Required structural elements ────────────────────────────────────────────
REQUIRED_TAGS = ["h1", "h2"]
REQUIRED_PATTERNS = [
    r'faq',
    r'conclusion|final',
    r'use case|real.?world',
    r'what is|overview|introduction',
]


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(" ", strip=True)


def _word_count(text: str) -> int:
    return len(re.findall(r'\b\w+\b', text))


def _sentences(text: str) -> list[str]:
    # Split on .!? followed by space/end
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 10]


def _paragraphs(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    return [p.get_text(" ", strip=True) for p in soup.find_all("p") if len(p.get_text()) > 40]


def _headings(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    return [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"])]


# ── A: Structural Score ─────────────────────────────────────────────────────

def score_structural(html: str, category: str = "") -> dict:
    """Check for required HTML structure, section presence, logical flow."""
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    score = 100

    # Required tags
    for tag in REQUIRED_TAGS:
        if not soup.find(tag):
            issues.append(f"Missing <{tag}>")
            score -= 20

    # H1 count (should be exactly 1)
    h1s = soup.find_all("h1")
    if len(h1s) == 0:
        issues.append("No H1 found")
        score -= 15
    elif len(h1s) > 1:
        issues.append(f"Multiple H1s ({len(h1s)}) — bad for SEO")
        score -= 10

    # H2 count (need at least 4 for depth)
    h2s = soup.find_all("h2")
    if len(h2s) < 4:
        issues.append(f"Too few H2 sections ({len(h2s)}) — need ≥4")
        score -= 15

    # Required section patterns
    full_text = html.lower()
    for pattern in REQUIRED_PATTERNS:
        if not re.search(pattern, full_text):
            issues.append(f"Missing section matching: {pattern}")
            score -= 8

    # FAQ section
    if not soup.find(class_=re.compile(r'faq')) and "faq" not in full_text:
        issues.append("No FAQ section")
        score -= 10

    # Paragraph count
    paras = _paragraphs(html)
    if len(paras) < 8:
        issues.append(f"Too few paragraphs ({len(paras)}) — content feels thin")
        score -= 12

    score = max(0, score)
    return {
        "score": score,
        "issues": issues,
        "h1_count": len(h1s),
        "h2_count": len(h2s),
        "paragraph_count": len(paras),
    }


# ── B: Readability Score ────────────────────────────────────────────────────

def score_readability(html: str) -> dict:
    """Sentence variation, paragraph balance, no robotic blocks."""
    text = _extract_text(html)
    sentences = _sentences(text)
    paras = _paragraphs(html)
    issues = []
    score = 100

    if not sentences:
        return {"score": 0, "issues": ["No readable text found"]}

    # Sentence length variation
    lengths = [len(s.split()) for s in sentences]
    avg_len = sum(lengths) / len(lengths)
    std_dev = math.sqrt(sum((l - avg_len) ** 2 for l in lengths) / len(lengths))

    if std_dev < 4:
        issues.append(f"Monotonous sentence length (std_dev={std_dev:.1f}) — lacks rhythm")
        score -= 18

    # Penalise very long sentences (>45 words) — hard to read
    long_sents = sum(1 for l in lengths if l > 45)
    if long_sents > len(sentences) * 0.15:
        issues.append(f"{long_sents} sentences over 45 words — too dense")
        score -= 12

    # Penalise very short sentences that cluster (< 8 words, 3 in a row)
    short_clusters = 0
    for i in range(len(lengths) - 2):
        if all(l < 8 for l in lengths[i:i+3]):
            short_clusters += 1
    if short_clusters > 2:
        issues.append(f"Short sentence clusters ({short_clusters}) — feels choppy")
        score -= 8

    # Paragraph length balance
    para_lens = [len(p.split()) for p in paras]
    if para_lens:
        overlong = sum(1 for pl in para_lens if pl > 120)
        if overlong > 2:
            issues.append(f"{overlong} paragraphs over 120 words — wall of text")
            score -= 15

        underlong = sum(1 for pl in para_lens if pl < 20)
        if underlong > len(paras) * 0.3:
            issues.append(f"Too many thin paragraphs ({underlong}) — padded structure")
            score -= 10

    # Repetitive paragraph starters
    starters = [" ".join(p.lower().split()[:3]) for p in paras]
    starter_counts = Counter(starters)
    repeats = {k: v for k, v in starter_counts.items() if v > 2}
    if repeats:
        issues.append(f"Repeated paragraph openers: {list(repeats.keys())}")
        score -= 12

    score = max(0, score)
    return {
        "score": score,
        "issues": issues,
        "avg_sentence_len": round(avg_len, 1),
        "sentence_len_std_dev": round(std_dev, 1),
        "paragraph_count": len(paras),
    }


# ── C: AI Detection Heuristics ──────────────────────────────────────────────

def score_ai_detection(html: str) -> dict:
    """Detect AI-tell phrases, generic openings, low lexical diversity."""
    text = _extract_text(html)
    html_lower = html.lower()
    issues = []
    deductions = 0

    # AI-tell phrases
    triggered_tells = []
    for pattern in AI_TELLS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            triggered_tells.extend(matches[:2])
            deductions += 8

    if triggered_tells:
        issues.append(f"AI-tell phrases detected: {triggered_tells[:5]}")

    # Generic opening check
    for pattern in GENERIC_OPENINGS:
        if re.search(pattern, html_lower):
            issues.append("Generic/robotic article opening detected")
            deductions += 12
            break

    # Lexical diversity (Type-Token Ratio)
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())
    if words:
        ttr = len(set(words)) / len(words)
        if ttr < 0.35:
            issues.append(f"Low lexical diversity (TTR={ttr:.2f}) — repetitive vocabulary")
            deductions += 15
        elif ttr < 0.42:
            issues.append(f"Below-average lexical diversity (TTR={ttr:.2f})")
            deductions += 8

    # Repetitive bigrams
    bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)] if words else []
    bigram_counts = Counter(bigrams)
    overused = {k: v for k, v in bigram_counts.items() if v > 4 and k not in
                {"of the", "in the", "to the", "on the", "for the", "is a", "it is"}}
    if len(overused) > 3:
        issues.append(f"Overused phrase patterns: {list(overused.keys())[:5]}")
        deductions += 10

    # Predictable transition words
    transition_overuse = len(re.findall(
        r'\b(furthermore|moreover|additionally|however|therefore|consequently|subsequently|nevertheless)\b',
        text, re.IGNORECASE
    ))
    if transition_overuse > 6:
        issues.append(f"Over-reliance on formal transitions ({transition_overuse} uses)")
        deductions += 8

    score = max(0, 100 - deductions)
    return {
        "score": score,
        "issues": issues,
        "ai_tells_found": len(triggered_tells),
        "lexical_diversity": round(len(set(words)) / len(words), 3) if words else 0,
    }


# ── D: Depth Score ──────────────────────────────────────────────────────────

def score_depth(html: str, topic: str, category: str) -> dict:
    """Measure explanation vs summary ratio, insights, real-world usefulness."""
    text = _extract_text(html)
    words = _word_count(text)
    issues = []
    score = 100

    # Word count minimum
    if words < 800:
        issues.append(f"Too short ({words} words) — AdSense requires substantial content")
        score -= 40
    elif words < 1100:
        issues.append(f"Below recommended length ({words} words) — aim for 1200+")
        score -= 20
    elif words < 1400:
        score -= 8  # Slight deduction

    # Specific technical terms / named entities (proxy for depth)
    # Look for numbers, percentages, named products, versions
    specificity_signals = re.findall(
        r'\b(\d+(?:\.\d+)?(?:%|ms|GB|TB|GHz|MHz|fps|kWh|mph|km|W|V|A)\b'
        r'|\bv?\d+\.\d+(?:\.\d+)?\b'
        r'|CVE-\d{4}-\d+|CVSS \d+\.\d+)',
        text
    )
    if len(specificity_signals) < 3:
        issues.append("Lacks specific technical data points (numbers, specs, versions, CVE IDs)")
        score -= 15

    # Insight indicators (beyond "what" to "why" and "so what")
    insight_patterns = [
        r'\b(?:this means|which means|the implication|what this means)\b',
        r'\b(?:because|the reason|the cause|this happens when)\b',
        r'\b(?:as a result|consequently|this leads to|the effect)\b',
        r'\b(?:for example|for instance|such as|to illustrate)\b',
        r'\b(?:unlike|compared to|in contrast|whereas)\b',
    ]
    insight_count = sum(
        len(re.findall(p, text, re.IGNORECASE))
        for p in insight_patterns
    )
    if insight_count < 5:
        issues.append(f"Low insight density ({insight_count} insight signals) — reads like summary")
        score -= 15

    # Actionability (steps, recommendations, best practices)
    action_signals = re.findall(
        r'\b(should|must|recommend|ensure|avoid|consider|best practice|step \d|first[,\s]|next[,\s])\b',
        text, re.IGNORECASE
    )
    if len(action_signals) < 4:
        issues.append("Low actionability — readers can't do anything with this content")
        score -= 10

    score = max(0, score)
    return {
        "score": score,
        "issues": issues,
        "word_count": words,
        "specificity_signals": len(specificity_signals),
        "insight_signals": insight_count,
        "action_signals": len(action_signals),
    }


# ── E: SEO Score ────────────────────────────────────────────────────────────

def score_seo(html: str, topic: str) -> dict:
    """Check heading structure, keyword distribution, meta quality."""
    soup = BeautifulSoup(html, "html.parser")
    text = _extract_text(html).lower()
    issues = []
    score = 100

    # Extract key topic words
    topic_words = set(re.findall(r'\b[a-z]{4,}\b', topic.lower())) - {
        "that", "this", "with", "from", "they", "have", "will", "your", "about"
    }

    # H1 must contain topic keywords
    h1 = soup.find("h1")
    if h1:
        h1_text = h1.get_text().lower()
        matched = topic_words & set(h1_text.split())
        if not matched:
            issues.append(f"H1 does not contain topic keywords: {topic_words}")
            score -= 15
    else:
        issues.append("No H1 tag")
        score -= 20

    # Keyword appears in first 100 words
    first_100 = " ".join(text.split()[:100])
    matched_in_intro = topic_words & set(re.findall(r'\b\w+\b', first_100))
    if not matched_in_intro:
        issues.append("No topic keywords in first 100 words")
        score -= 10

    # Meta description
    meta = soup.find("meta", attrs={"name": "description"})
    if not meta:
        # Look for HTML comment with meta description
        if "meta_description" not in html.lower() and "<!-- META:" not in html:
            issues.append("No meta description tag")
            score -= 10
    else:
        desc = meta.get("content", "")
        if len(desc) < 120:
            issues.append(f"Meta description too short ({len(desc)} chars)")
            score -= 8
        elif len(desc) > 160:
            issues.append(f"Meta description too long ({len(desc)} chars)")
            score -= 5

    # H2 subheadings contain topic variations
    h2s = soup.find_all("h2")
    h2_texts = " ".join(h.get_text().lower() for h in h2s)
    h2_keyword_match = len(topic_words & set(h2_texts.split()))
    if h2_keyword_match < 2 and topic_words:
        issues.append("H2 subheadings lack topic keyword variations")
        score -= 10

    # Heading hierarchy (no skipping levels)
    all_headings = soup.find_all(["h1", "h2", "h3", "h4"])
    levels = [int(h.name[1]) for h in all_headings]
    for i in range(len(levels) - 1):
        if levels[i+1] - levels[i] > 1:
            issues.append(f"Heading level skipped: h{levels[i]} → h{levels[i+1]}")
            score -= 5
            break

    # Image alt texts (if images present)
    imgs = soup.find_all("img")
    no_alt = [img for img in imgs if not img.get("alt")]
    if no_alt:
        issues.append(f"{len(no_alt)} images missing alt text")
        score -= 5

    score = max(0, score)
    return {
        "score": score,
        "issues": issues,
        "h1_has_keywords": bool(matched_in_intro if h1 else False),
        "h2_count": len(h2s),
        "has_meta": bool(meta),
    }


# ── F: Value Score ──────────────────────────────────────────────────────────

def score_value(html: str, category: str) -> dict:
    """Does it provide actionable, insightful content specific to the niche?"""
    text = _extract_text(html)
    issues = []
    score = 100

    # FAQ quality
    if "faq" in text.lower():
        faq_questions = re.findall(r'\?', text)
        if len(faq_questions) < 5:
            issues.append(f"FAQ section has fewer than 5 questions ({len(faq_questions)} found)")
            score -= 10
    else:
        issues.append("No FAQ section — high-value content should answer common questions")
        score -= 15

    # Comparison or contrast signals (high-value for readers)
    comparison_signals = re.findall(
        r'\b(vs\.|versus|compared to|in contrast|unlike|better than|worse than|advantage|disadvantage)\b',
        text, re.IGNORECASE
    )
    if len(comparison_signals) < 2:
        issues.append("No comparison/contrast — misses an engagement opportunity")
        score -= 8

    # Real-world use cases
    usecase_signals = re.findall(
        r'\b(use case|real.?world|scenario|example|such as|for instance|practical)\b',
        text, re.IGNORECASE
    )
    if len(usecase_signals) < 3:
        issues.append("Insufficient real-world use cases or examples")
        score -= 12

    # Takeaway/recommendation signals
    takeaway_signals = re.findall(
        r'\b(takeaway|key point|remember|bottom line|key insight|recommendation|action)\b',
        text, re.IGNORECASE
    )
    if len(takeaway_signals) < 2:
        issues.append("No clear takeaways or key points — readers won't remember this")
        score -= 10

    score = max(0, score)
    return {
        "score": score,
        "issues": issues,
        "faq_questions": len(re.findall(r'\?', text)),
        "comparison_signals": len(comparison_signals),
        "usecase_signals": len(usecase_signals),
    }


# ── Master Scoring Function ─────────────────────────────────────────────────

def score_article(html: str, topic: str = "", category: str = "") -> dict:
    """
    Run all 6 scoring dimensions. Return weighted total + full breakdown.
    """
    breakdown = {
        "structural":   score_structural(html, category),
        "readability":  score_readability(html),
        "ai_detection": score_ai_detection(html),
        "depth":        score_depth(html, topic, category),
        "seo":          score_seo(html, topic),
        "value":        score_value(html, category),
    }

    # Weighted total
    total = sum(
        breakdown[dim]["score"] * (WEIGHTS[dim] / 100)
        for dim in WEIGHTS
    )
    total = round(total)

    # Aggregate all issues
    all_issues = []
    for dim, result in breakdown.items():
        for issue in result.get("issues", []):
            all_issues.append(f"[{dim.upper()}] {issue}")

    # Summary grade
    if total >= 85:
        grade = "A — AdSense Ready"
    elif total >= 72:
        grade = "B — Good, minor improvements suggested"
    elif total >= 60:
        grade = "C — Needs improvement before publishing"
    else:
        grade = "F — Requires regeneration"

    return {
        "total": total,
        "grade": grade,
        "summary": f"Score: {total}/100 ({grade})",
        "breakdown": breakdown,
        "all_issues": all_issues,
        "adsense_ready": total >= 72,
        "word_count": breakdown["depth"]["word_count"],
    }
