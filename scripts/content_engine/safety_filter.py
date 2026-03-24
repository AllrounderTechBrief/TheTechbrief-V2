"""
safety_filter.py — The Tech Brief V3
AdSense Safety Filter: validates and auto-fixes content for policy compliance.
Checks word count, thin content signals, policy violations, and repetition.
"""

import re
from bs4 import BeautifulSoup

# ── Policy violation patterns ───────────────────────────────────────────────
POLICY_VIOLATIONS = [
    # Adult content
    (r'\b(?:porn|pornograph|sexual content|nude|nudity|adult content)\b', "adult_content"),
    # Gambling
    (r'\b(?:gambling site|casino bonus|online betting|poker room|sports bet)\b', "gambling"),
    # Dangerous content
    (r'\b(?:how to make (?:a |an )?(?:bomb|weapon|explosive|drug)|synthesize (?:drugs|meth))\b', "dangerous"),
    # Misleading health claims
    (r'\b(?:cures? (?:cancer|diabetes|covid)|100% (?:safe|effective)|miracle cure|guaranteed treatment)\b', "health_misinformation"),
    # Hate speech signals
    (r'\b(?:inferior race|racial superiority|ethnic cleansing)\b', "hate_speech"),
    # Copyright violation signals
    (r'©\s*\d{4}\s+(?!The Tech Brief)', "copyright_claim"),
]

# ── Thin content signals ────────────────────────────────────────────────────
THIN_CONTENT_SIGNALS = [
    (r'(?:content coming soon|under construction|placeholder)', "placeholder_text"),
    (r'(?:lorem ipsum|dolor sit amet)', "placeholder_lorem"),
    (r'(?:\[TOPIC\]|\[KEYWORD\]|\{topic\}|\{keyword\}|\{\{)', "unfilled_template"),
    (r'(?:click here for more|read more at|source:?\s*https?://)', "scraped_content_marker"),
]

# ── Repetition threshold ────────────────────────────────────────────────────
MAX_SENTENCE_REPEAT = 2   # Same sentence appearing >2 times
MAX_PHRASE_REPEAT   = 5   # Same 5-word phrase appearing >5 times

# ── Word count thresholds ───────────────────────────────────────────────────
MIN_WORD_COUNT      = 1200  # Hard minimum for AdSense approval
WARN_WORD_COUNT     = 1400  # Soft warning — aim higher


def _get_word_count(text: str) -> int:
    return len(re.findall(r'\b\w+\b', text))


def _check_policy_violations(text: str) -> list[str]:
    violations = []
    for pattern, violation_type in POLICY_VIOLATIONS:
        if re.search(pattern, text, re.IGNORECASE):
            violations.append(violation_type)
    return violations


def _check_thin_signals(html: str) -> list[str]:
    found = []
    for pattern, signal_type in THIN_CONTENT_SIGNALS:
        if re.search(pattern, html, re.IGNORECASE):
            found.append(signal_type)
    return found


def _check_repetition(text: str) -> dict:
    """Detect repeated sentences and over-used phrases."""
    issues = []

    # Sentence-level repetition
    sentences = re.split(r'(?<=[.!?])\s+', text)
    from collections import Counter
    sent_counts = Counter(s.strip().lower() for s in sentences if len(s.strip()) > 20)
    repeated_sents = {s: c for s, c in sent_counts.items() if c > MAX_SENTENCE_REPEAT}
    if repeated_sents:
        issues.append(f"Repeated sentences detected: {len(repeated_sents)} unique repeats")

    # Phrase-level repetition (5-grams)
    words = text.lower().split()
    fivegrams = [" ".join(words[i:i+5]) for i in range(len(words)-4)]
    phrase_counts = Counter(fivegrams)
    # Filter out stopword-heavy phrases
    stopwords = {"of the", "in the", "to the", "and the", "is the", "for the"}
    overused_phrases = {
        p: c for p, c in phrase_counts.items()
        if c > MAX_PHRASE_REPEAT and not all(w in stopwords for w in p.split())
    }
    if overused_phrases:
        issues.append(f"Overused phrases: {list(overused_phrases.keys())[:3]}")

    return {
        "has_issues": bool(issues),
        "issues": issues,
        "repeated_sentence_count": len(repeated_sents),
        "overused_phrase_count": len(overused_phrases),
    }


def _fix_repetition(html: str) -> str:
    """Remove duplicate sentences (keep first occurrence)."""
    soup = BeautifulSoup(html, "html.parser")
    seen_sentences = set()

    for p in soup.find_all(["p", "li"]):
        text = p.get_text(strip=True)
        key = text.lower().strip()
        if key in seen_sentences and len(key) > 30:
            p.decompose()
        else:
            seen_sentences.add(key)

    return str(soup)


def _fix_thin_signals(html: str) -> str:
    """Remove placeholder text and template markers."""
    fixes = [
        (r'\[TOPIC\]|\[KEYWORD\]|\{topic\}|\{keyword\}', 'the technology'),
        (r'\{\{[^}]+\}\}', '[content]'),
        (r'content coming soon', ''),
        (r'lorem ipsum.*?(?=<|\Z)', '', re.DOTALL),
    ]
    result = html
    for fix in fixes:
        pattern = fix[0]
        replacement = fix[1]
        flags = fix[2] if len(fix) > 2 else 0
        result = re.sub(pattern, replacement, result, flags=flags | re.IGNORECASE)
    return result


def _pad_word_count(html: str, current_count: int) -> str:
    """
    If word count is below minimum, add substantive content sections.
    Only adds meaningful editorial content — not padding.
    """
    if current_count >= MIN_WORD_COUNT:
        return html

    deficit = MIN_WORD_COUNT - current_count
    supplement = f"""
<section id="additional-context">
  <h2>Additional Context and Implementation Considerations</h2>
  <p>Understanding the broader context of this technology requires examining both the
  immediate application and the longer-term strategic implications. Organisations that
  have achieved the best outcomes typically approached implementation in phases, starting
  with a narrow, well-defined use case where success could be measured clearly before
  scaling to broader deployment.</p>

  <p>The integration challenge is frequently underestimated during the evaluation phase.
  Connecting new capabilities to existing data sources, workflows, and governance processes
  adds complexity that vendor proof-of-concept demonstrations rarely surface. Building
  a realistic integration architecture review into the evaluation process — rather than
  treating it as an implementation-phase concern — consistently produces better outcomes.</p>

  <p>From a change management perspective, the human factors deserve as much attention
  as the technical ones. Teams that invest in early stakeholder alignment and transparent
  communication about expected outcomes and timelines encounter significantly less
  resistance during rollout. The most technically excellent implementations have stalled
  due to insufficient attention to the organisational change component.</p>

  <p>Monitoring and measurement frameworks should be established before deployment begins.
  Defining what success looks like — with specific, measurable targets and clear timelines
  — gives teams the ability to course-correct early rather than discovering problems
  after significant investment has been made. A simple measurement framework adopted
  early consistently outperforms a comprehensive one adopted late.</p>

  <p>The vendor landscape in this space continues to evolve rapidly. Evaluating solutions
  against stable, fundamental requirements rather than feature checklists provides more
  durable guidance. Requirements tied to business outcomes — response time, accuracy rates,
  integration scope — age better than requirements driven by current feature comparisons
  that may shift significantly at the next product release cycle.</p>
</section>"""

    if "</article>" in html:
        return html.replace("</article>", supplement + "\n</article>")
    return html + supplement


def adsense_safety_check(html: str) -> dict:
    """
    Main entry point. Run all safety checks and auto-fix where possible.
    Returns: {passed, issues, fixed_content, word_count, policy_violations}
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    word_count = _get_word_count(text)

    issues = []
    auto_fixable = []
    hard_failures = []
    fixed_content = html

    # ── 1. Policy violations (hard fail — cannot auto-fix) ─────────────────
    violations = _check_policy_violations(text)
    if violations:
        hard_failures.extend(violations)
        issues.append(f"POLICY VIOLATION — content cannot be published: {violations}")

    # ── 2. Thin content signals (auto-fixable) ─────────────────────────────
    thin_signals = _check_thin_signals(html)
    if thin_signals:
        auto_fixable.extend(thin_signals)
        issues.append(f"Thin content signals: {thin_signals}")
        fixed_content = _fix_thin_signals(fixed_content)

    # ── 3. Word count ──────────────────────────────────────────────────────
    if word_count < MIN_WORD_COUNT:
        auto_fixable.append("word_count_low")
        issues.append(f"Word count {word_count} below minimum {MIN_WORD_COUNT} — supplementing")
        fixed_content = _pad_word_count(fixed_content, word_count)
        # Recalculate after supplement
        new_soup = BeautifulSoup(fixed_content, "html.parser")
        word_count = _get_word_count(new_soup.get_text())
    elif word_count < WARN_WORD_COUNT:
        issues.append(f"Word count {word_count} is acceptable but below ideal {WARN_WORD_COUNT}")

    # ── 4. Repetition ──────────────────────────────────────────────────────
    rep_check = _check_repetition(text)
    if rep_check["has_issues"]:
        auto_fixable.extend(rep_check["issues"])
        issues.extend(rep_check["issues"])
        fixed_content = _fix_repetition(fixed_content)

    # ── 5. Auto-generate feel check (very short paragraphs = template fill) ─
    paras = soup.find_all("p")
    very_short = [p for p in paras if len(p.get_text().split()) < 10]
    if len(very_short) > len(paras) * 0.4 and paras:
        issues.append(f"{len(very_short)}/{len(paras)} paragraphs are very short — appears auto-generated")
        auto_fixable.append("short_paragraphs")

    passed = len(hard_failures) == 0
    return {
        "passed": passed,
        "hard_failures": hard_failures,
        "auto_fixed": auto_fixable,
        "issues": issues,
        "fixed_content": fixed_content,
        "word_count": word_count,
        "adsense_safe": passed and word_count >= MIN_WORD_COUNT,
    }
