"""Score how relevant an article is to Amir's research (music learning,
neuroplasticity, and brass/trombone performance) using local keyword
matching -- no external API, no billing.
"""

import re

# (keyword, weight) -- higher weight = more central to Amir's specific work.
_KEYWORDS = [
    ("trombone", 5), ("embouchure", 5), ("brass", 3), ("wind instrument", 3),
    ("wind instruments", 3), ("auditory-motor", 4), ("audiomotor", 4),
    ("sensorimotor integration", 3), ("sensorimotor", 2), ("motor learning", 3),
    ("music training", 3), ("musical training", 3), ("musician", 2), ("musicians", 2),
    ("instrumentalist", 3), ("instrumentalists", 3), ("neuroplasticity", 3),
    ("neural plasticity", 3), ("plasticity", 2), ("cortical reorganization", 3),
    ("structural plasticity", 3), ("gray matter", 2), ("grey matter", 2),
    ("white matter", 2), ("functional connectivity", 2), ("motor cortex", 2),
    ("cerebellum", 2), ("procedural learning", 2), ("skill acquisition", 2),
    ("expertise", 2), ("longitudinal", 1), ("neuroimaging", 1),
    ("fmri", 1), ("mri", 1), ("eeg", 1), ("meg", 1),
]


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
