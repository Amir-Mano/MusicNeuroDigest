"""Orchestrates the weekly pipeline: search -> rank -> summarize -> email -> update state."""

import logging
import sys

import config
import relevance
import search_articles
import send_email
import summarize


def setup_logging() -> None:
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(config.LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def run() -> None:
    setup_logging()
    log = logging.getLogger(__name__)
    log.info("Run started")

    try:
        seen_pmids = search_articles.load_seen_pmids()
        seen_classic_pmids = search_articles.load_seen_classic_pmids()
        pending = search_articles.load_pending_articles()

        # Pull in fresh PubMed hits, skipping anything already sent or already queued.
        queued_pmids = {a["pmid"] for a in pending}
        fresh = search_articles.get_new_articles(seen_pmids | queued_pmids)
        if fresh:
            log.info("Found %d fresh article(s): %s", len(fresh), [a["pmid"] for a in fresh])
        pending.extend(fresh)

        # Most-relevant-first, so the "must-read" naturally floats to the top and
        # anything beyond the per-email cap (the least relevant) waits its turn.
        ranked = relevance.rank_articles(pending)
        this_week = ranked[: config.MAX_DIGEST_SIZE]
        backlog = ranked[config.MAX_DIGEST_SIZE :]

        classic = search_articles.get_classic_article(
            seen_classic_pmids | seen_pmids | {a["pmid"] for a in this_week}
        )

        if not this_week and not classic:
            log.info("No new or classic articles found. Nothing to send.")
            search_articles.save_pending_articles(backlog)
            return

        log.info(
            "Sending %d new article(s) (%d held back for next week); classic pick: %s",
            len(this_week), len(backlog), classic["pmid"] if classic else "none",
        )

        summarize.summarize_articles(this_week)
        if classic:
            summarize.summarize_articles([classic])

        must_read = this_week[0] if this_week else None
        send_email.send_digest(this_week, must_read=must_read, classic=classic)

        seen_pmids.update(a["pmid"] for a in this_week)
        search_articles.save_seen_pmids(seen_pmids)
        search_articles.save_pending_articles(backlog)
        if classic:
            seen_classic_pmids.add(classic["pmid"])
            search_articles.save_seen_classic_pmids(seen_classic_pmids)

        log.info("Digest sent; state updated.")
    except Exception:
        log.exception("Run failed")
        raise
    finally:
        log.info("Run finished")


if __name__ == "__main__":
    run()
