"""Skill: search bioRxiv/medRxiv preprints via Europe PMC (free, keyless).

Preprints are NOT peer-reviewed. Every article returned here carries
is_preprint=True so the email can flag it distinctly and separately from
the peer-reviewed PubMed digest. Output is capped at PREPRINT_MAX_PER_DIGEST
per run; overflow queues in its own backlog for next week, same carryover
approach as the main article pool in search_articles.py.
"""

import json
from datetime import date, timedelta

import config
import http_utils
import state_utils

EUROPEPMC_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
_TIMEOUT = 30


def load_seen_preprint_ids() -> set:
    if not config.SEEN_PREPRINT_IDS_PATH.exists():
        return set()
    return set(json.loads(config.SEEN_PREPRINT_IDS_PATH.read_text(encoding="utf-8")))


def save_seen_preprint_ids(ids: set) -> None:
    state_utils.save_json(config.SEEN_PREPRINT_IDS_PATH, sorted(ids))


def load_pending_preprints() -> list:
    if not config.PENDING_PREPRINTS_PATH.exists():
        return []
    return json.loads(config.PENDING_PREPRINTS_PATH.read_text(encoding="utf-8"))


def save_pending_preprints(preprints: list) -> None:
    state_utils.save_json(config.PENDING_PREPRINTS_PATH, preprints)


def _search_preprint_records() -> list:
    maxdate = date.today()
    mindate = maxdate - timedelta(days=config.SEARCH_LOOKBACK_DAYS)
    query = (
        f"{config.PREPRINT_QUERY} AND SRC:PPR "
        f"AND FIRST_PDATE:[{mindate.isoformat()} TO {maxdate.isoformat()}]"
    )
    params = {
        "query": query,
        "format": "json",
        "pageSize": 50,
        "resultType": "core",
    }
    resp = http_utils.get_with_retry(EUROPEPMC_URL, params=params, timeout=_TIMEOUT)
    return resp.json().get("resultList", {}).get("result", [])


def get_new_preprints(seen_ids: set) -> list:
    """Search Europe PMC for new bioRxiv/medRxiv preprints not already seen/queued."""
    articles = []
    for record in _search_preprint_records():
        server = (record.get("bookOrReportDetails") or {}).get("publisher")
        if server not in ("bioRxiv", "medRxiv"):
            continue  # Europe PMC's SRC:PPR spans many preprint servers; keep only these two

        preprint_id = record.get("id", "")  # Europe PMC IDs are already "PPR"-prefixed and unique
        if not preprint_id or preprint_id in seen_ids:
            continue

        title = (record.get("title") or "").strip()
        if not title:
            continue

        doi = record.get("doi", "")
        authors = [a.strip() for a in (record.get("authorString") or "").split(",") if a.strip()]

        articles.append({
            "pmid": preprint_id,
            "title": title,
            "authors": authors,
            "journal": server,
            "pub_date": record.get("firstPublicationDate", ""),
            "abstract": record.get("abstractText") or "No abstract available.",
            "abstract_sections": [],  # preprint abstracts aren't structured like PubMed's
            "url": f"https://doi.org/{doi}" if doi else "",
            "publication_types": ["Preprint"],
            "is_preprint": True,
        })
    return articles
