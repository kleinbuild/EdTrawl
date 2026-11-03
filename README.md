# EdTrawl

Personal tool for finding California teaching jobs within commute range of home. Scrapes [edjoin.org](https://www.edjoin.org) listings, enriches them with school data from the [California Department of Education](https://www.cde.ca.gov/ds/si/ds/pubschls.asp), filters by traffic-aware drive time, and stores everything in a local SQLite database.

**Status: early development (Phase 1 of 7).** The repo skeleton, schema, and scraper scripts exist. The database layer (`db.py`) is partially written — SQL is drafted but the Python wrappers don't run yet. No data has been ingested. See `notes/01_project_plan.md` for the full phase breakdown.

## How AI is used in this project

This project is being built by a self-taught beginner learning Python, SQL, and web scraping. [Claude Code](https://docs.anthropic.com/en/docs/claude-code) is used as a pair-programming partner throughout development: explaining concepts, scaffolding code with worked examples, reviewing drafts, and helping debug. The learning notes in `notes/` were written in conversation with Claude.

The code itself is written by the developer — Claude provides the scaffolding and explanations (see the commented-out `upsert_district()` worked example in `db.py`), then the developer fills in the real implementations by following those patterns. Where Claude wrote code directly, it's marked.

In the finished tool, Phase 5 plans to use an LLM API call for one specific task: fuzzy-matching free-text school names from edjoin.org to CDS codes in the CDE database. Everything else is deterministic.

## Structure

```
scraper/           Node/Playwright scripts for edjoin.org (Currently Deprecated)
  capture_login.js   Save an authenticated browser session (run manually; Currently Deprecated)
  search_edjoin.js   Scrape job listings (discovery mode + scrape mode; currently deprecated.)
data/                CDE source CSVs and edtrawl.db (not committed; see below)
edtrawl/
  db.py              SQLite schema, upserts, and queries
  csv_ingest.py      Load the CDE school/district CSVs into the database
  column_dict.py     CSV header → DB column name mappings
  edjoin_client.py   Pull edjoin.org listings into the database
  fuzzy_matching.py  Match listings to schools/districts (rapidfuzz)
  clustering.py      Collapse nearby schools into clusters for drive times
  geocode.py         Address → lat/lng (stub)
  match.py           Haversine radius filter (implemented), commute filter (stub)
  travel_time.py     Traffic-aware drive time (stub)
  scraper/           Python/Playwright versions of the scraper scripts (Deprecated)
tests/               pytest tests
notes/               Learning notes and project plan
```

## Reference data

The school data comes from CDE's "California Public Schools" file on [data.ca.gov](https://data.ca.gov/dataset/california-public-schools-2025-26)). Download the CSV and place it in `data/reference/`. These files are `.gitignored` because they're large (~5 MB) and freely available from the source.

## Setup

```bash
# Node side (scraper)
npm install

# Python side
pip install -e ".[dev]"   # project + pytest
cp .env.example .env      # fill in your address and API keys
python -m edtrawl.db      # initialize the database
pytest                    # run the tests
```

## Usage (planned)

```bash
npm run login             # one-time: log into edjoin.org in a browser window
npm run search            # scrape job listings
python -m pipeline.ingest # (Phase 2) load CDE school data
python -m pipeline.run    # (Phase 3+) geocode, compute travel times, filter
```

### School clusters

Schools on the same campus or block get the same drive time from home, so
`edtrawl/clustering.py` groups them and travel times can be computed once per
cluster instead of once per school. It reads the `schools` table and writes two
tables to `data/edtrawl.db`: `school_clusters` (one row per cluster, with its
centroid) and `school_cluster_members` (`cds_code` → `cluster_id`).

```bash
python -m edtrawl.clustering --compare      # compare radii 0.1–0.75 mi (no DB writes)
python -m edtrawl.clustering                # build at the default 0.4 mi radius and save
python -m edtrawl.clustering --radius 0.25  # build at a different radius
python -m edtrawl.clustering --osrm         # also split clusters by road drive time
```

- **Radius** (`--radius`, default 0.4 mi): schools within this distance of each
  other are grouped (DBSCAN). A school with no neighbors is its own cluster.
- **Span limit** (`--max-span`, default 0.75 mi): DBSCAN can chain schools into
  a long cluster, so any cluster wider than this is split.
- **Drive-time check** (`--osrm`, off by default): needs a self-hosted
  [OSRM](https://project-osrm.org/) server (`--osrm-url`, default
  `http://localhost:5000`). Splits clusters where two schools are more than
  `--max-internal-minutes` (default 3) apart by road. If the server can't be
  reached, the command stops with an error.

Rebuilding replaces both tables, and cluster IDs can change between runs, so
anything keyed on `cluster_id` should be recomputed after a rebuild.

## Note on scraping

This tool logs into edjoin.org using your own credentials and scrapes your own search results. It is built for personal use. Respect the site's terms of service and rate limits.

## License

Not yet decided. All rights reserved until a license is added.
