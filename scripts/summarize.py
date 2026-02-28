"""
summarize.py  —  Text summarisation helper for The Tech Brief build pipeline.

Uses sumy TextRank with NLTK punkt tokenizer.
Falls back to sentence-split truncation if sumy/nltk unavailable.
"""

import re


def summarize_text(text, sentences=2, language="english"):
    """
    Return a summary of `text` containing at most `sentences` sentences.
    Tries sumy TextRank first; falls back to simple truncation on any error.
    """
    text = (text or "").strip()
    if not text:
        return ""

    try:
        from sumy.parsers.plaintext import PlaintextParser
        from sumy.nlp.tokenizers import Tokenizer
        from sumy.summarizers.text_rank import TextRankSummarizer

        parser = PlaintextParser.from_string(text, Tokenizer(language))
        summarizer = TextRankSummarizer()
        result = summarizer(parser.document, sentences)
        if result:
            return " ".join(str(s) for s in result)
    except Exception:
        pass

    # Fallback: split on sentence boundaries and return first N
    parts = re.split(r"(?<=[.!?])\s+", text)
    joined = " ".join(parts[:sentences])
    if joined:
        return joined
    return text[:280] + ("…" if len(text) > 280 else "")
