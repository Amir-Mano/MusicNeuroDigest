"""Skill 2: produce a short summary of each article's abstract.

Purely local (no LLM API calls, no billing) -- an extractive summary. When
PubMed provides a structured abstract (BACKGROUND/METHODS/RESULTS/
CONCLUSIONS labels), pulls from the RESULTS/CONCLUSIONS sections so the
summary is the actual finding rather than background/rationale. Falls back
to the abstract's lead sentences when it isn't structured that way.
"""

import re

# Abbreviations whose trailing "." would otherwise be mistaken for a sentence end.
_ABBREVIATIONS = (
    "e.g.", "i.e.", "et al.", "vs.", "approx.", "fig.", "eq.",
    "no.", "pp.", "vol.", "dr.", "mr.", "mrs.", "ms.",
)

# Section labels (NlmCategory or free-text Label, already uppercased) worth
# pulling from directly -- these are where the actual finding lives, as
# opposed to BACKGROUND/METHODS/OBJECTIVE which set up the study.
_FINDING_LABEL_MARKERS = ("RESULT", "CONCLUSION", "FINDING")


def _split_sentences(text: str) -> list:
    placeholder_map = {}
    protected = text
    for idx, abbr in enumerate(_ABBREVIATIONS):
        token = f"__ABBR{idx}__"
        placeholder_map[token] = abbr
        protected = re.sub(re.escape(abbr), token, protected, flags=re.IGNORECASE)

    sentences = re.split(r"(?<=[.!?])\s+", protected.strip())

    restored = []
    for sentence in sentences:
        for token, abbr in placeholder_map.items():
            sentence = sentence.replace(token, abbr)
        restored.append(sentence.strip())
    return [s for s in restored if s]


def _finding_text(article: dict) -> str:
    """Text from RESULTS/CONCLUSIONS sections, if the abstract is structured that way."""
    sections = article.get("abstract_sections") or []
    finding_parts = [
        s["text"] for s in sections
        if any(marker in s["label"] for marker in _FINDING_LABEL_MARKERS)
    ]
    return " ".join(finding_parts).strip()


def summarize_article(article: dict, max_sentences: int = 3, max_chars: int = 400) -> str:
    """Return an extractive summary: RESULTS/CONCLUSIONS when structured, else lead sentences."""
    abstract = article["abstract"]
    if abstract == "No abstract available.":
        return abstract

    source_text = _finding_text(article) or abstract

    sentences = _split_sentences(source_text)
    summary = " ".join(sentences[:max_sentences])
    if len(summary) > max_chars:
        summary = summary[:max_chars].rsplit(" ", 1)[0] + "..."
    return summary


def summarize_articles(articles: list) -> list:
    """Attach a 'summary' field to each article dict."""
    for article in articles:
        article["summary"] = summarize_article(article)
    return articles
