"""Orchestrates the weekly pipeline: search -> rank -> summarize -> email -> update state."""

import logging
import sys

import config
import journal_quality
import metadata_extraction
import preprints
import relevance
import search_articles
import send_email
import summarize

NOT_PEER_REVIEWED_LABEL = "Not applicable -- preprint, not yet peer-reviewed"


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
        try:
            fresh = search_articles.get_new_articles(seen_pmids | queued_pmids)
        except Exception:
            log.exception("PubMed article search failed; continuing with existing backlog only")
            fresh = []
        if fresh:
            log.info("Found %d fresh article(s): %s", len(fresh), [a["pmid"] for a in fresh])
        pending.extend(fresh)

        # Most-relevant-first, so the "must-read" naturally floats to the top and
        # anything beyond the per-email cap (the least relevant) waits its turn.
        ranked = relevance.rank_articles(pending)
        this_week = ranked[: config.MAX_DIGEST_SIZE]
        backlog = ranked[config.MAX_DIGEST_SIZE :]

        try:
            classic = search_articles.get_classic_article(
                seen_classic_pmids | seen_pmids | {a["pmid"] for a in this_week}
            )
        except Exception:
            log.exception("Classic-pick search failed; continuing without a classic pick this run")
            classic = None

        # Preprints are tracked entirely separately (own state, own backlog, own
        # small cap) since they're not peer-reviewed and shouldn't crowd out or
        # blend in with the PubMed-vetted pool above.
        seen_preprint_ids = preprints.load_seen_preprint_ids()
        pending_preprints = preprints.load_pending_preprints()
        queued_preprint_ids = {p["pmid"] for p in pending_preprints}
        try:
            fresh_preprints = preprints.get_new_preprints(seen_preprint_ids | queued_preprint_ids)
        except Exception:
            log.exception("Preprint search failed; continuing without new preprints this run")
            fresh_preprints = []
        if fresh_preprints:
            log.info(
                "Found %d fresh preprint(s): %s",
                len(fresh_preprints), [p["pmid"] for p in fresh_preprints],
            )
        pending_preprints.extend(fresh_preprints)
        ranked_preprints = relevance.rank_articles(pending_preprints)
        this_week_preprints = ranked_preprints[: config.PREPRINT_MAX_PER_DIGEST]
        preprint_backlog = ranked_preprints[config.PREPRINT_MAX_PER_DIGEST :]

        if not this_week and not classic and not this_week_preprints:
            log.info("No new, classic, or preprint articles found. Nothing to send.")
            search_articles.save_pending_articles(backlog)
            preprints.save_pending_preprints(preprint_backlog)
            return

        log.info(
            "Sending %d new article(s) (%d held back), classic pick: %s, %d preprint(s) (%d held back)",
            len(this_week), len(backlog), classic["pmid"] if classic else "none",
            len(this_week_preprints), len(preprint_backlog),
        )

        all_for_email = this_week + ([classic] if classic else []) + this_week_preprints
        for article in all_for_email:
            article["study_type"] = metadata_extraction.classify_study_type(article)
            article["methods"] = metadata_extraction.extract_methods(article)
            article["sample_size"] = metadata_extraction.extract_sample_size(article)

        # Journal-quality (OpenAlex, PMID-based) is meaningless for preprints --
        # they have no journal yet -- so only look it up for the peer-reviewed set.
        journal_quality.attach_journal_quality(this_week + ([classic] if classic else []))
        for preprint in this_week_preprints:
            preprint["journal_quality"] = NOT_PEER_REVIEWED_LABEL

        summarize.summarize_articles(this_week)
        if classic:
            summarize.summarize_articles([classic])
        summarize.summarize_articles(this_week_preprints)

        must_read = this_week[0] if this_week else None
        send_email.send_digest(
            this_week, must_read=must_read, classic=classic, preprints=this_week_preprints
        )

        seen_pmids.update(a["pmid"] for a in this_week)
        search_articles.save_seen_pmids(seen_pmids)
        search_articles.save_pending_articles(backlog)
        if classic:
            seen_classic_pmids.add(classic["pmid"])
            search_articles.save_seen_classic_pmids(seen_classic_pmids)
        seen_preprint_ids.update(p["pmid"] for p in this_week_preprints)
        preprints.save_seen_preprint_ids(seen_preprint_ids)
        preprints.save_pending_preprints(preprint_backlog)

        log.info("Digest sent; state updated.")
    except Exception as exc:
        log.exception("Run failed")
        send_email.send_error_email(f"{type(exc).__name__}: {exc}")
        raise
    finally:
        log.info("Run finished")


if __name__ == "__main__":
    run()
