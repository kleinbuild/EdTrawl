# EdTrawl — Claude Code Parallel Build Plan

## Purpose

You build EdTrawl by hand, learning each piece. In parallel, Claude Code builds a competing version from the same spec, making its own design decisions. When both are done, you compare them head-to-head: what it chose differently, what worked better, what you understand that it glossed over, and what it did that you'd steal.

The comparison is the learning tool. Two implementations of the same spec surface design tradeoffs that studying one version alone can't.


## What Claude Code gets

A single prompt (below) containing the spec, the data source, and the constraints. It does NOT get your db.py, your schema decisions, your column-naming conventions, or any of the intermediate thinking from this conversation. It starts from the same requirements, not from your code. That's what makes the comparison meaningful — if it arrives at the same schema, the design was probably well-grounded; if it diverges, the differences are worth understanding.


## When to run the parallel build

After you've finished Phase 2 of your own build (schema done, ingest working, real CDE data loaded). Starting the parallel build before that gives you nothing to compare against and risks anchoring your thinking to its choices before you've made your own. The whole point is: you go first.


## The prompt

Copy the block below into a Claude Code session. It's self-contained — no context from this conversation is assumed.

---

```
Build a Python CLI tool called EdTrawl that helps California teachers find teaching jobs within commute range of their home.

## Data source

Primary school data: the "California Public Schools 2025-26" CSV from data.ca.gov. URL for the CSV download:
https://gis.data.ca.gov/api/download/v1/items/0cab44bcfd9a44eb88197147e4d37e8b/csv?layers=0

This file contains ~10,000 TK-12 public schools with: CDS Code (the state's unique 14-character school identifier), school name, district name, address, latitude, longitude, enrollment, demographic breakdowns (counts and percentages), per-grade enrollment, staff counts, and program flags (Title I, charter, virtual, magnet, DASS, ESSA status). Coordinates are quality-controlled. Prior-year versions of this file exist on data.ca.gov for enrollment trajectory analysis.

## Core requirements

1. SQLite database with at minimum:
   - A school identity table (things that rarely change: name, location, coordinates, type)
   - A yearly snapshot table (enrollment, demographics, staff — changes annually, keyed by school + year)
   - A travel-time cache table (commute minutes from the user's home, computed once per school and cached)
   - A jobs table (scraped edjoin.org listings linked to schools)

2. CDE ingest pipeline: parse the CSV, coerce types (NULL for suppressed demographic cells), load into the identity and snapshot tables. Must be idempotent (re-running produces the same result, not duplicates). Must handle multi-year loading (ingest 2024-25 and 2025-26 into the same snapshot table).

3. Travel-time estimation: given the user's home lat/lng, filter schools by straight-line radius first (free, local), then compute traffic-aware drive time for survivors only (7:00am arrival, 3:30pm departure). Cache results. Use a provider that supports departure/arrival time for predictive traffic.

4. Job listing acquisition: the primary source for California teaching jobs is edjoin.org. It requires user authentication to search. Design and implement a way to pull job listings programmatically, handling the authentication requirement however you see fit. Criteria-based filtering of results (location, position type, etc.).

5. Job-to-school matching: job listings from edjoin use free-text school/district names that don't exactly match CDE's canonical names. Use an LLM call to fuzzy-match each listing's school/district string to the best CDS code in the database. Cache the mapping.

6. Query interface: given constraints (max commute minutes, days since posted, school level, charter/non-charter, enrollment minimum, etc.), return matching jobs joined across all four tables.

## Constraints

- CDS Code is a 14-character identifier — store as TEXT, not INTEGER (leading zeros).
- Any authentication credentials or session tokens must be gitignored.
- The LLM is a tool called by the pipeline for fuzzy matching only — it is not a router or orchestrator. The pipeline code owns all control flow.
- Demographic counts are nullable INTEGER (California suppresses small cells). Percentages are REAL.
- Y/N flags stored as TEXT 'Y'/'N', not 0/1.
- Travel-time cache has a configurable freshness threshold (default 90 days).

## Deliverables

- Working repo with README
- Schema that passes `python db.py` to initialize all tables
- Ingest that loads the real 2025-26 CSV
- At least one query demonstrating the full join across tables
- Clear separation between identity data, yearly snapshots, cached computations, and scraped listings

Make your own design decisions on: table/column naming, function signatures, file organization, which travel-time provider, how to structure the ingest loop, and how to decompose the pipeline into modules. Document your reasoning in code comments where a decision was non-obvious.
```

---


## How to compare

After both versions exist, look at these specifically:

**Schema design.** Did it also split identity from snapshots, or did it flatten into one table? What did it name columns? Did it use CDS as the primary key or a surrogate? Did it put the composite key in the same place? Differences here reveal genuine design tradeoffs — neither is automatically wrong.

**Ingest structure.** Did it use DictReader? How did it handle type coercion — inline try/except, a helper function, a mapping dict? Did it define column order once or repeat it? Compare code volume and readability.

**The upsert pattern.** Did it use INSERT...ON CONFLICT, or INSERT OR REPLACE, or a check-then-insert approach? Each has different semantics around NULL handling and COALESCE. If it used a different upsert strategy, trace what happens to a school whose coordinates you hand-corrected — does the next ingest clobber them?

**Job acquisition approach.** This is the most open-ended comparison. You chose Playwright with manual session capture and storageState reuse. What did it pick — the same, Selenium, raw requests with cookies, an RSS feed, something else entirely? Did it check whether edjoin has an API before scraping? How did it handle the authentication problem? If it chose a different tool or strategy, trace the tradeoffs: reliability, fragility to site changes, dependency weight, ease of re-authentication when sessions expire.

**Travel-time caching.** Did it use the same freshness pattern (computed_on date vs max_age_days), or something different? Did it filter by radius before travel-time, or compute travel time for everything?

**What you understand that it didn't explain.** The parallel build will produce working code. But you'll know *why* `cds_code` is TEXT, why the FK requires identity-before-snapshot load order, why COALESCE protects coordinates, why the composite key is (cds_code, academic_year) and not just cds_code. Working code that you can't explain is fragile; understanding that you can implement is durable. The comparison should show you where you're ahead on understanding and where it's ahead on technique — and let you take the technique without losing the understanding.
