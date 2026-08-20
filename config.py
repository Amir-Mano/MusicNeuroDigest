"""Shared configuration for the digest pipeline, loaded from .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# --- PubMed search ---
PUBMED_QUERY = (
    '(music[Title/Abstract]) AND '
    '(neuroplasticity[Title/Abstract] OR "neural plasticity"[Title/Abstract] '
    'OR neuroimaging[Title/Abstract] OR fMRI[Title/Abstract] OR MRI[Title/Abstract] '
    'OR EEG[Title/Abstract] OR MEG[Title/Abstract])'
)
MAX_RESULTS_PER_RUN = 25
SEARCH_LOOKBACK_DAYS = 30  # always search this window; state file dedups reruns
NCBI_API_KEY = os.getenv("NCBI_API_KEY")  # optional, raises rate limit if set

# --- Digest shaping ---
MAX_DIGEST_SIZE = 8  # new articles per email; overflow carries to next week's backlog
CLASSIC_MIN_AGE_DAYS = 730  # "not so fresh" cutoff for the high-impact pick
CLASSIC_SEARCH_FLOOR = "1990/01/01"  # don't look further back than this
CLASSIC_CANDIDATE_POOL = 40  # how many relevance-ranked older articles to pull before citation-ranking

# --- Preprints (bioRxiv/medRxiv via Europe PMC) ---
# Plain-text version of PUBMED_QUERY -- Europe PMC doesn't use PubMed's [Title/Abstract] field tags.
PREPRINT_QUERY = (
    '(music) AND (neuroplasticity OR "neural plasticity" OR neuroimaging '
    'OR fMRI OR MRI OR EEG OR MEG)'
)
PREPRINT_MAX_PER_DIGEST = 2  # not peer-reviewed -- kept small and clearly labeled

# --- Email ---
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO", EMAIL_ADDRESS)
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

# --- State / paths ---
STATE_DIR = BASE_DIR / "state"
SEEN_PMIDS_PATH = STATE_DIR / "seen_pmids.json"
SEEN_CLASSIC_PMIDS_PATH = STATE_DIR / "seen_classic_pmids.json"
PENDING_PATH = STATE_DIR / "pending_articles.json"
SEEN_PREPRINT_IDS_PATH = STATE_DIR / "seen_preprint_ids.json"
PENDING_PREPRINTS_PATH = STATE_DIR / "pending_preprints.json"
LOGS_DIR = BASE_DIR / "logs"
LOG_PATH = LOGS_DIR / "run.log"
HISTORY_PATH = BASE_DIR / "history.md"
