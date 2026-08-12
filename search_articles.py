"""Skill 1: search PubMed for new music + neuroplasticity/neuroimaging articles."""

import json
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta

import requests

import citations
import config
import relevance

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def load_seen_pmids() -> set:
    if not config.SEEN_PMIDS_PATH.exists():
        return set()
    return set(json.loads(config.SEEN_PMIDS_PATH.read_text(encoding="utf-8")))


def save_seen_pmids(pmids: set) -> None:
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    config.SEEN_PMIDS_PATH.write_text(
        json.dumps(sorted(pmids), indent=2), encoding="utf-8"
    )


def load_seen_classic_pmids() -> set:
    if not config.SEEN_CLASSIC_PMIDS_PATH.exists():
        return set()
    return set(json.loads(config.SEEN_CLASSIC_PMIDS_PATH.read_text(encoding="utf-8")))


def save_seen_classic_pmids(pmids: set) -> None:
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    config.SEEN_CLASSIC_PMIDS_PATH.write_text(
        json.dumps(sorted(pmids), indent=2), encoding="utf-8"
    )


def load_pending_articles() -> list:
    if not config.PENDING_PATH.exists():
        return []
    return json.loads(config.PENDING_PATH.read_text(encoding="utf-8"))


def save_pending_articles(articles: list) -> None:
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    config.PENDING_PATH.write_text(
        json.dumps(articles, indent=2), encoding="utf-8"
    )


def _esearch_params(mindate: str, maxdate: str) -> dict:
    params = {
        "db": "pubmed",
        "term": config.PUBMED_QUERY,
        "datetype": "edat",  # entrez date = when PubMed indexed it, catches late-added records
        "mindate": mindate,
        "maxdate": maxdate,
        "retmax": config.MAX_RESULTS_PER_RUN,
        "sort": "most+recent",
        "retmode": "json",
    }
    if config.NCBI_API_KEY:
        params["api_key"] = config.NCBI_API_KEY
    return params


def _search_pmids() -> list:
    maxdate = date.today()
    mindate = maxdate - timedelta(days=config.SEARCH_LOOKBACK_DAYS)
    resp = requests.get(
        ESEARCH_URL,
        params=_esearch_params(mindate.isoformat(), maxdate.isoformat()),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("esearchresult", {}).get("idlist", [])


def _fetch_details(pmids: list) -> list:
    if not pmids:
        return []
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "xml",
    }
    if config.NCBI_API_KEY:
        params["api_key"] = config.NCBI_API_KEY
    resp = requests.get(EFETCH_URL, params=params, timeout=30)
    resp.raise_for_status()

    articles = []
    root = ET.fromstring(resp.content)
    for art in root.findall(".//PubmedArticle"):
        pmid = art.findtext(".//PMID", default="").strip()
        title = "".join(art.find(".//ArticleTitle").itertext()).strip() if art.find(".//ArticleTitle") is not None else ""
        abstract_parts = art.findall(".//Abstract/AbstractText")
        abstract = " ".join("".join(p.itertext()).strip() for p in abstract_parts) if abstract_parts else ""
        journal = art.findtext(".//Journal/Title", default="").strip()
        publication_types = [
            (pt.text or "").strip()
            for pt in art.findall(".//PublicationTypeList/PublicationType")
            if (pt.text or "").strip()
        ]

        authors = []
        for author in art.findall(".//AuthorList/Author"):
            last = author.findtext("LastName")
            fore = author.findtext("ForeName")
            if last and fore:
                authors.append(f"{fore} {last}")
            elif last:
                authors.append(last)

        pub_date_el = art.find(".//Article/Journal/JournalIssue/PubDate")
        pub_date = ""
        if pub_date_el is not None:
            year = pub_date_el.findtext("Year", default="")
            month = pub_date_el.findtext("Month", default="")
            pub_date = f"{month} {year}".strip()

        if not pmid or not title:
            continue

        articles.append({
            "pmid": pmid,
            "title": title,
            "authors": authors,
            "journal": journal,
            "pub_date": pub_date,
            "abstract": abstract or "No abstract available.",
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "publication_types": publication_types,
        })
    return articles


def get_new_articles(seen_pmids: set) -> list:
    """Search PubMed and return articles not already in seen_pmids."""
    pmids = _search_pmids()
    new_pmids = [p for p in pmids if p not in seen_pmids]
    return _fetch_details(new_pmids)


def _search_pmids_by_relevance(mindate: str, maxdate: str, retmax: int) -> list:
    params = {
        "db": "pubmed",
        "term": config.PUBMED_QUERY,
        "datetype": "pdat",  # publication date, not indexing date -- age is what matters here
        "mindate": mindate,
        "maxdate": maxdate,
        "retmax": retmax,
        "sort": "relevance",
        "retmode": "json",
    }
    if config.NCBI_API_KEY:
        params["api_key"] = config.NCBI_API_KEY
    resp = requests.get(ESEARCH_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("esearchresult", {}).get("idlist", [])


def get_classic_article(exclude_pmids: set) -> dict | None:
    """Find one older (>= CLASSIC_MIN_AGE_DAYS), highly relevant, highly cited
    article not already featured -- the "not so fresh" high-impact pick.
    """
    maxdate = date.today() - timedelta(days=config.CLASSIC_MIN_AGE_DAYS)
    mindate = datetime.strptime(config.CLASSIC_SEARCH_FLOOR, "%Y/%m/%d").date()

    pmids = _search_pmids_by_relevance(
        mindate.isoformat(), maxdate.isoformat(), config.CLASSIC_CANDIDATE_POOL
    )
    candidate_pmids = [p for p in pmids if p not in exclude_pmids]
    if not candidate_pmids:
        return None

    candidates = _fetch_details(candidate_pmids)
    candidates = [a for a in candidates if relevance.score_article(a) > 0]
    if not candidates:
        return None

    counts = citations.get_citation_counts([a["pmid"] for a in candidates])
    for article in candidates:
        article["citation_count"] = counts.get(article["pmid"], 0)

    candidates.sort(key=lambda a: a["citation_count"], reverse=True)
    return candidates[0]
