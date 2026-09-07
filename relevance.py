"""Score how relevant an article is to Amir's research (music learning,
neuroplasticity, and instrument-specific brain differences) using local keyword
matching -- no external API, no billing.
"""

import re

from keywords import KEYWORDS as _KEYWORDS


def score_article(article: dict) -> float:
    """Higher score = more relevant to Amir's specific research focus."""
    title = article.get("title", "").lower()
    abstract = article.get("abstract", "").lower()
    score = 0.0
    for keyword, weight in _KEYWORDS:
        pattern = re.escape(keyword.lower())
        score += weight * 2 * len(re.findall(pattern, title))
        score += weight * len(re.findall(pattern, abstract))
    return score


def rank_articles(articles: list) -> list:
    """Return articles sorted most-relevant first."""
    return sorted(articles, key=score_article, reverse=True)
