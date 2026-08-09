"""Skill 2: produce a short summary of each article's abstract.

Purely local (no LLM API calls, no billing) -- an extractive summary that
takes the lead sentences of the abstract, which is where research abstracts
conventionally state the aim/method before results and conclusions.
"""

import re

import config

# Abbreviations whose trailing "." would otherwise be mistaken for a sentence end.
_ABBREVIATIONS = (
    "e.g.", "i.e.", "et al.", "vs.", "approx.", "fig.", "eq.",
    "no.", "pp.", "vol.", "dr.", "mr.", "mrs.", "ms.",
)


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


def summarize_article(article: dict, max_sentences: int = 3, max_chars: int = 400) -> str:
    """Return a lead-sentence extract of the abstract as a lightweight summary."""
    abstract = article["abstract"]
    if abstract == "No abstract available.":
        return abstract

    sentences = _split_sentences(abstract)
    summary = " ".join(sentences[:max_sentences])
    if len(summary) > max_chars:
        summary = summary[:max_chars].rsplit(" ", 1)[0] + "..."
    return summary


def summarize_articles(articles: list) -> list:
    """Attach a 'summary' field to each article dict."""
    for article in articles:
        article["summary"] = summarize_article(article)
    return articles
