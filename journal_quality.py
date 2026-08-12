"""Skill: estimate journal quality via OpenAlex (free, keyless).

Uses each journal's 2-year mean citedness -- computed the same way as a
journal impact factor, just not the trademarked Clarivate/JCR number (that's
a paid product; this is the free, open equivalent). Best-effort: OpenAlex
doesn't index every journal or every brand-new article, so this degrades
gracefully to "unavailable" rather than failing the whole digest run.
"""

import requests

WORKS_URL = "https://api.openalex.org/works/pmid:{pmid}"
SOURCES_URL = "https://api.openalex.org/sources/{source_id}"
_TIMEOUT = 15


def _tier_label(citedness: float) -> str:
    if citedness >= 8:
        return "Very high impact"
    if citedness >= 4:
        return "High impact"
    if citedness >= 2:
        return "Moderate impact"
    if citedness > 0:
        return "Lower impact"
    return "Impact data unavailable"


def _lookup_source_id(pmid: str) -> str | None:
    try:
        resp = requests.get(WORKS_URL.format(pmid=pmid), timeout=_TIMEOUT)
        if resp.status_code != 200:
            return None
        source = (resp.json().get("primary_location") or {}).get("source") or {}
        return source.get("id")
    except (requests.RequestException, ValueError):
        return None


def _lookup_source_quality(source_id: str) -> str:
    try:
        resp = requests.get(SOURCES_URL.format(source_id=source_id), timeout=_TIMEOUT)
        if resp.status_code != 200:
            return "Impact data unavailable"
        stats = resp.json().get("summary_stats") or {}
        citedness = stats.get("2yr_mean_citedness")
        if citedness is None:
            return "Impact data unavailable"
        return f"{_tier_label(citedness)} (~{citedness:.1f} cites/paper, 2yr avg via OpenAlex)"
    except (requests.RequestException, ValueError):
        return "Impact data unavailable"


def attach_journal_quality(articles: list) -> None:
    """Set article['journal_quality'] in place for each article. Never raises --
    any lookup failure just falls back to an 'unavailable' label so a network
    hiccup here doesn't stop the digest from sending.
    """
    source_quality_cache: dict[str, str] = {}

    for article in articles:
        article["journal_quality"] = "Impact data unavailable"
        source_id = _lookup_source_id(article["pmid"])
        if not source_id:
            continue

        if source_id not in source_quality_cache:
            source_quality_cache[source_id] = _lookup_source_quality(source_id)
        article["journal_quality"] = source_quality_cache[source_id]
