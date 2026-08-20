"""Look up citation counts via NIH's free iCite API (no key, no billing).

Used to find genuinely high-impact older articles for the "classic pick".
"""

import http_utils

ICITE_URL = "https://icite.od.nih.gov/api/pubs"
_BATCH_SIZE = 200


def get_citation_counts(pmids: list) -> dict:
    """Return {pmid: citation_count} for the given PMIDs. Missing entries default to 0."""
    if not pmids:
        return {}
    counts = {}
    for i in range(0, len(pmids), _BATCH_SIZE):
        batch = pmids[i:i + _BATCH_SIZE]
        resp = http_utils.get_with_retry(ICITE_URL, params={"pmids": ",".join(batch)}, timeout=30)
        for record in resp.json().get("data", []):
            counts[str(record["pmid"])] = record.get("citation_count") or 0
    return counts
