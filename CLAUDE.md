# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A weekly email digest that tracks new PubMed articles on music + neuroplasticity/neuroimaging,
ranks them by relevance to a specific research focus (music training, motor learning,
auditory-motor integration, brass/trombone performance), and emails a summary. Built as a
standalone Python project — no client framework, no build step.

**Zero paid APIs anywhere in the pipeline.** PubMed E-utilities and NIH's iCite are both free
and keyless; relevance scoring and summarization are local keyword/heuristic logic, not an LLM
call; Gmail SMTP is free. Keep it that way — don't introduce a billed API without discussing it
first, since "no ongoing cost" is a deliberate design constraint here, not an oversight.

## Commands

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # then fill in EMAIL_ADDRESS / EMAIL_APP_PASSWORD / EMAIL_TO
python main.py               # run the full pipeline once
```

There is no automated test suite — verify changes by running `main.py` and checking
`logs/run.log` plus the actual received email.

## Architecture

Three "skills" orchestrated by `main.py`:

- `search_articles.py` — PubMed E-utilities search (`esearch`/`efetch`). Two search modes:
  a recency-sorted search over the last `SEARCH_LOOKBACK_DAYS` for new articles, and a
  relevance-sorted search over articles older than `CLASSIC_MIN_AGE_DAYS` for the classic pick.
  Owns all state file I/O (`state/seen_pmids.json`, `state/seen_classic_pmids.json`,
  `state/pending_articles.json`).
- `relevance.py` — scores an article dict against a hand-maintained weighted keyword list
  (`_KEYWORDS`) reflecting the target research focus. No ML, no embeddings — just weighted
  regex counts over title (2x) and abstract (1x). Used both to rank the weekly batch (so the
  top-ranked article becomes the "must-read") and to filter classic-pick candidates.
- `citations.py` — looks up citation counts for a batch of PMIDs via NIH's free iCite API.
  Used only for ranking classic-pick candidates by actual impact.
- `summarize.py` — turns an abstract into a short summary by extracting its lead 1–3
  sentences (research abstracts conventionally front-load the aim/method). Purely local.
- `send_email.py` — builds the plain-text + HTML digest and sends it via Gmail SMTP
  (`smtplib`, STARTTLS). Layout: must-read article highlighted first, then the rest of the
  week's new articles, then the classic pick in its own section.

`main.py` ties it together each run:

1. Load state (`seen_pmids`, `seen_classic_pmids`, `pending_articles`).
2. Search PubMed for fresh articles not already seen or queued; append to the pending backlog.
3. Rank the full backlog by relevance; take the top `MAX_DIGEST_SIZE` (default 8) for this
   email, leave the rest in the backlog for next run. The top-ranked article is the must-read.
4. Search for one classic pick (older, relevant, ranked by real citation count via iCite,
   excluding anything already featured or already in this week's batch).
5. Summarize, send, update state.

If there's nothing to send (no new articles and no classic candidate), no email goes out —
`logs/run.log` still records that the run happened, since it's meant to run unattended via
Windows Task Scheduler and there's no other way to confirm it's alive.

## Config

All tunable behavior lives in `config.py`: the PubMed query, search windows, digest size cap,
classic-pick age threshold and candidate pool size. Secrets (`EMAIL_ADDRESS`,
`EMAIL_APP_PASSWORD`, `EMAIL_TO`, optional `NCBI_API_KEY`) load from `.env` via `python-dotenv`
— `.env` is gitignored, `.env.example` is the checked-in template and must never contain a real
value.

## State files

`state/*.json` and `logs/` are gitignored (runtime data, not source). If you reset state during
testing, delete `state/seen_pmids.json` to let the next run re-treat everything in the lookback
window as new — useful for verifying formatting changes without waiting for real new articles.

## Scheduling

Meant to run unattended via Windows Task Scheduler (`run_weekly.bat`, weekly), not via any
Claude-Code-specific scheduling — see README for the `schtasks` command. The pipeline has no
dependency on Claude Code or any Anthropic service at runtime.
