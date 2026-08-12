# Music & Neuroplasticity Digest

Watches PubMed for new articles on music + neuroplasticity/neuroimaging, ranks them
by relevance to a specific research focus (music training, motor learning,
auditory-motor integration, brass/trombone performance), and emails a weekly digest.

No paid API involved anywhere in the pipeline: PubMed's E-utilities, NIH's iCite,
OpenAlex, and Europe PMC are all free with no key required, relevance scoring and
summarization are done locally, and Gmail SMTP is free. The only external cost is
nothing.

## How it works

1. **`search_articles.py`** — queries PubMed E-utilities for new articles matching
   music AND (neuroplasticity/neuroimaging/fMRI/MRI/EEG/MEG). Also searches for an
   older, relevance-sorted "classic" candidate pool (see below).
2. **`relevance.py`** — scores every article against a local keyword profile
   (trombone, embouchure, auditory-motor integration, motor learning, etc.) — no
   LLM call, just weighted keyword matching. Used to rank the weekly batch and to
   pick the must-read.
3. **`citations.py`** — looks up real citation counts from NIH's free
   [iCite API](https://icite.od.nih.gov/) for classic-pick candidates.
4. **`metadata_extraction.py`** — pulls study type, method/metrics, and reported
   sample size for each article (see below). Local heuristics only, no network.
5. **`journal_quality.py`** — looks up each article's journal quality via the free
   [OpenAlex API](https://openalex.org/) (see below).
6. **`summarize.py`** — produces a short summary of each abstract **locally**. When
   PubMed provides a structured abstract (BACKGROUND/METHODS/RESULTS/CONCLUSIONS
   labels), pulls from RESULTS/CONCLUSIONS so the summary is the actual finding;
   otherwise falls back to the lead 1–3 sentences.
7. **`preprints.py`** — searches bioRxiv/medRxiv preprints via the free
   [Europe PMC API](https://europepmc.org/) (see below).
8. **`send_email.py`** — builds and sends the digest over Gmail SMTP.
9. **`main.py`** ties it together and manages the state below.

## Digest shape

- **Up to 8 new articles per email.** New PubMed hits accumulate in a backlog
  (`state/pending_articles.json`); each run sends the 8 most relevant and carries
  the rest into next week rather than dropping them.
- **1 must-read.** The most relevant of that week's 8 (by the local relevance
  score) is highlighted at the top of the email.
- **1 classic pick, every email.** A separate search looks for articles at least
  `CLASSIC_MIN_AGE_DAYS` old (default 2 years) that still match the relevance
  keywords, ranks the candidates by real citation count via iCite, and features
  the most-cited one that hasn't been sent before. This surfaces high-impact
  older work alongside the fresh stuff — never repeats.

- **Up to 2 preprints per email, always clearly marked.** A separate search on
  bioRxiv/medRxiv via Europe PMC finds new preprints matching the same relevance
  keywords. They're tracked in their own backlog, capped at
  `PREPRINT_MAX_PER_DIGEST` per email, and rendered in their own section with an
  explicit "NOT PEER-REVIEWED" badge — never mixed into the peer-reviewed pool
  above, and no journal-quality score is shown for them (they don't have one yet).

State lives in `state/`: `seen_pmids.json` (already-sent new articles),
`seen_classic_pmids.json` (already-featured classics), `pending_articles.json`
(this week's overflow, for next week), `seen_preprint_ids.json`, and
`pending_preprints.json` (same overflow model, separate from the main pool).

## Per-article metadata

Every article in the digest — must-read, "also new," and the classic pick — gets
four extra fields, all extracted automatically (no LLM, no billing) and shown as
a best-effort reading aid, not a substitute for reading the paper:

- **Type** — PubMed's own publication-type tags when informative (Review,
  Meta-Analysis, Randomized Controlled Trial, etc.); falls back to detecting
  design language in the abstract (longitudinal, cross-sectional, cohort, pilot,
  etc.) when PubMed only has it tagged as a generic "Journal Article."
- **Method** — modality (fMRI, diffusion MRI, EEG, MEG, structural MRI, PET,
  fNIRS, TMS, MRS, behavioral) plus, within each, specific metrics/analyses
  mentioned in the abstract (graph theory, ISC, FA, MD, ERP, functional
  connectivity, MVPA, etc.).
- **N** — sample size as reported in the abstract, e.g. "32 musicians, 28
  controls" or "N = 45." Abstracts phrase this inconsistently, so this is
  regex-based best-effort, not guaranteed complete.
- **Journal** — a quality signal from each journal's 2-year mean citedness via
  [OpenAlex](https://openalex.org/) (free, no key) — the same underlying
  computation as a journal impact factor, just not the trademarked Clarivate/JCR
  number. Falls back to "Impact data unavailable" if OpenAlex doesn't have the
  journal or the article isn't indexed yet.

## One-time setup

```bash
cd MusicNeuroDigest
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Then fill in `.env`:

- **`EMAIL_ADDRESS`** / **`EMAIL_TO`** — the Gmail account to send from/to.
- **`EMAIL_APP_PASSWORD`** — Gmail requires an *App Password*, not your normal login
  password, to send mail via SMTP:
  1. Turn on 2-Step Verification on the Google account, if not already on:
     https://myaccount.google.com/security
  2. Generate an App Password: https://myaccount.google.com/apppasswords
  3. Paste the 16-character password into `.env`.

## Run it manually

```bash
venv\Scripts\activate
python main.py
```

Check `logs/run.log` for what happened. Run it twice in a row to confirm the
second run's backlog/dedup behaves as expected.

## Schedule it (Windows Task Scheduler)

```powershell
schtasks /create /tn "MusicNeuroDigest" /tr "<full path to>\run_weekly.bat" /sc weekly /d MON /st 08:00
```

- Check it exists: `schtasks /query /tn "MusicNeuroDigest"`
- Run it on demand: `schtasks /run /tn "MusicNeuroDigest"`
- Change the day/time: `schtasks /change /tn "MusicNeuroDigest" /st 09:30`
- Remove it: `schtasks /delete /tn "MusicNeuroDigest"`

**"Run as soon as possible after a missed start" is enabled** (`StartWhenAvailable`),
so if the PC is off/asleep at the scheduled time, the digest fires as soon as it's
next on instead of silently skipping that week:

```powershell
$task = Get-ScheduledTask -TaskName "MusicNeuroDigest"
$task.Settings.StartWhenAvailable = $true
Set-ScheduledTask -InputObject $task | Out-Null
```

## Tuning

- `config.py`: `PUBMED_QUERY` / `SEARCH_LOOKBACK_DAYS` (search scope),
  `MAX_DIGEST_SIZE` (per-email cap), `CLASSIC_MIN_AGE_DAYS` /
  `CLASSIC_CANDIDATE_POOL` (classic-pick behavior), `PREPRINT_QUERY` /
  `PREPRINT_MAX_PER_DIGEST` (preprint search and cap).
- `relevance.py`: `_KEYWORDS` — adjust the weighted keyword list to match your
  own research focus if you fork this for a different field.
- `metadata_extraction.py`: `_MODALITY_PATTERNS` / `_FMRI_METRIC_PATTERNS` /
  `_DIFFUSION_METRIC_PATTERNS` / `_EEG_METRIC_PATTERNS` / `_DESIGN_PATTERNS` —
  extend these if you notice a common method/design term the digest is missing.
