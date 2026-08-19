# EdTrawl — Project Plan

## What exists so far

The repo skeleton is built. Two Node/Playwright scripts handle edjoin.org session capture and search-page scraping (selectors unconfirmed — that happens on first real run). The SQLite schema has two live tables: `schools` (identity, keyed on `cds_code`) and `schools_snapshots` (yearly demographic/enrollment/staff data, composite-keyed on `cds_code, academic_year`, with a foreign key back to `schools`). The `districts`, `travel_times`, and `jobs` tables are deferred as commented-out placeholders. `upsert_district()` is a complete worked example; `upsert_school()` is in progress — the SQL is drafted but the Python wrapper (dict→tuple parameter passing, connection execution) is unfinished. No data has been ingested yet.

Data source confirmed: CDE's "California Public Schools 2025-26" CSV from data.ca.gov, with prior-year files available for backfill. Coordinates are quality-controlled and present in the file. Geocoding is needed only for the user's home address (one call, free provider). Traffic-aware travel time is the only paid API, and volume is tiny (a few hundred schools, computed once, cached).

## Phases

### Phase 1 — Finish the database layer (db.py)

1a. Complete `upsert_school()`: write the Python wrapper that takes a `row` dict, builds the parameter tuple, and executes the INSERT...ON CONFLICT SQL you've already drafted. This is the dict→tuple mechanic — the new learning.

1b. Write `upsert_snapshot()`: same pattern, but the ON CONFLICT target is the composite key `(cds_code, academic_year)`. Handles nullable INTEGER for suppressed demographic cells, REAL for percentages.

1c. Write `save_travel_time()` and `get_cached_travel_time()`: the cache-write and cache-read pair. `save_travel_time` upserts one row keyed on `cds_code`, storing minutes and today's ISO date. `get_cached_travel_time` selects a row only if `computed_on >= date('now', '-N days')`.

1d. Write `get_schools_missing_travel_time()`: LEFT JOIN from `schools` to `travel_times`, returning schools with no cached row or a stale one. This is the API work queue.

1e. Uncomment and finalize the `travel_times` CREATE TABLE. `jobs` stays deferred until Phase 5.

### Phase 2 — CDE data ingest (ingest_cde.py)

2a. Write a CSV reader that opens the CDE file, prints headers on first run (confirm column names), and maps CDE column names to your snake_case schema names.

2b. Build the per-row type coercion: parse integers (NULL on failure), parse reals for percentages (NULL on failure), pass text through, strip/normalize whitespace.

2c. Wire the loop: for each row, call `upsert_school()` (identity), then `upsert_snapshot()` (yearly data). Identity first, snapshot second — the FK requires it.

2d. Run against the real 2025-26 CSV. Verify row counts, spot-check a few schools by CDS code, confirm the composite key prevents duplicates on re-run.

2e. Download and ingest at least one prior-year file (2024-25). Confirm multi-year snapshots coexist and enrollment trajectory is queryable (`SELECT cds_code, academic_year, enroll_total FROM school_snapshots WHERE cds_code = ? ORDER BY academic_year`).

### Phase 3 — Geocoding and travel time

3a. Resolve your home address to lat/lng. One-time call to the free US Census Geocoder or Nominatim. Store in `.env` as `HOME_LAT`/`HOME_LNG`.

3b. Implement `match.py`: `within_radius()` using the haversine function (already given), filtering schools to a candidate set before any API call. Test with a 30-mile radius from home; print the count of survivors.

3c. Pick a traffic-aware travel-time provider (Google Routes, TravelTime, or Amazon Location). Get an API key, add to `.env`.

3d. Implement `travel_time.py`: `travel_minutes(home, school)` making two one-way requests (morning arrival, afternoon departure). Return `(arrive_min, depart_min)`.

3e. Wire the pipeline: call `get_schools_missing_travel_time()` → filter by radius → call `travel_minutes()` for survivors → call `save_travel_time()` for each. Confirm the cache prevents repeat API calls on re-run.

### Phase 4 — Playwright scraper (edjoin.org)

4a. Run `npm run login` on your machine to capture a live session (`auth_state.json`).

4b. Run `npm run search` in discovery mode. Save `discovery.html`, inspect it, and update the `SELECTORS` block in `search_edjoin.js` to match edjoin's actual DOM.

4c. Set real criteria in the `CRITERIA` block. Run a real scrape. Inspect `results.csv` for correctness.

4d. (Later, Phase 5) Link scraped jobs to schools in the database — this requires fuzzy matching between edjoin's school/district text and your CDE-sourced `school_name`/`district_name`. This is the one place an LLM call earns its keep.

### Phase 5 — Jobs table and LLM matching

5a. Finalize the `jobs` CREATE TABLE: decide what makes a job unique (likely the edjoin URL), write the schema.

5b. Write a job ingest function that takes a scraped row and upserts it into `jobs`.

5c. Build the fuzzy matcher: given edjoin's free-text school/district name, find the best `cds_code` match in your `schools` table. This is the LLM-assisted step — send the edjoin string plus a candidate list to a cheap model, get back the matched CDS code. Cache the mapping so each edjoin string is resolved only once.

5d. Wire scraping → matching → job upsert into a single pipeline run.

### Phase 6 — Query and output

6a. Write query functions: "show me jobs within N minutes of home, posted in the last M days, at schools matching [criteria]." This joins `jobs`, `schools`, `school_snapshots`, and `travel_times`.

6b. Output to terminal (table printout) or CSV for now. A web UI or dashboard is a future bolt-on, not a Phase 6 requirement.

### Phase 7 — Bolt-ons (future, not blocking)

- Enrollment trajectory analysis (multi-year snapshot comparison — the data is already there after Phase 2e).
- CAASPP/Dashboard academic data, keyed by CDS code.
- District financial health from SACS/FCMAT reporting.
- Thursday/Friday traffic columns in `travel_times`.
- Packaging for other California teachers.


## Dependencies between phases

Phase 2 depends on Phase 1 (ingest calls the writers you build in Phase 1).
Phase 3 depends on Phase 2 (travel time needs schools with coordinates loaded).
Phase 4 is independent of Phases 2-3 — you can capture your edjoin session and confirm selectors any time.
Phase 5 depends on both Phase 2 (schools in DB for matching) and Phase 4 (scraped jobs to match).
Phase 6 depends on everything above.
Phase 7 is all optional, all independent of each other, all possible after Phase 2.
