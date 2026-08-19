# EdTrawl

Personal tool for finding California teaching jobs within commute range of home. Scrapes [edjoin.org](https://www.edjoin.org) listings, enriches them with school data from the [California Department of Education](https://www.cde.ca.gov/ds/si/ds/pubschls.asp), filters by traffic-aware drive time, and stores everything in a local SQLite database.

**Status: early development (Phase 1 of 7).** The repo skeleton, schema, and scraper scripts exist. The database layer (`db.py`) is partially written — SQL is drafted but the Python wrappers don't run yet. No data has been ingested. See `notes/01_project_plan.md` for the full phase breakdown.

## How AI is used in this project

This project is being built by a self-taught beginner learning Python, SQL, and web scraping. [Claude Code](https://docs.anthropic.com/en/docs/claude-code) is used as a pair-programming partner throughout development: explaining concepts, scaffolding code with worked examples, reviewing drafts, and helping debug. The learning notes in `notes/` were written in conversation with Claude.

The code itself is written by the developer — Claude provides the scaffolding and explanations (see the commented-out `upsert_district()` worked example in `db.py`), then the developer fills in the real implementations by following those patterns. Where Claude wrote code directly, it's marked.

In the finished tool, Phase 5 plans to use an LLM API call for one specific task: fuzzy-matching free-text school names from edjoin.org to CDS codes in the CDE database. Everything else is deterministic.

## Structure

```
scraper/           Node/Playwright scripts for edjoin.org
  capture_login.js   Save an authenticated browser session (run manually)
  search_edjoin.js   Scrape job listings (discovery mode + scrape mode)
data/
  db.py              SQLite schema and upsert functions (WIP)
  reference/         CDE source CSVs (not committed; see below)
pipeline/
  column_dict.py     CSV header → DB column name mappings
  geocode.py         Address → lat/lng (stub)
  match.py           Haversine radius filter (implemented), commute filter (stub)
  travel_time.py     Traffic-aware drive time (stub)
notes/               Learning notes and project plan
```

## Reference data

The school data comes from CDE's "California Public Schools" file on [data.ca.gov](https://data.ca.gov/dataset/california-school-directory/resource/798ff104-de68-4a5e-95b2-6da38833bd9b). Download the CSV and place it in `data/reference/`. These files are `.gitignored` because they're large (~5 MB) and freely available from the source.

## Setup

```bash
# Node side (scraper)
npm install

# Python side
pip install -e .          # or: pip install requests
cp .env.example .env      # fill in your address and API keys
python data/db.py         # initialize the database (once schema is complete)
```

## Usage (planned)

```bash
npm run login             # one-time: log into edjoin.org in a browser window
npm run search            # scrape job listings
python -m pipeline.ingest # (Phase 2) load CDE school data
python -m pipeline.run    # (Phase 3+) geocode, compute travel times, filter
```

## Note on scraping

This tool logs into edjoin.org using your own credentials and scrapes your own search results. It is built for personal use. Respect the site's terms of service and rate limits.

## License

Not yet decided. All rights reserved until a license is added.
