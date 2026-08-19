# EdTrawl — Study Plan

Readings and exercises embedded in the build sequence. Each phase lists what to study before writing the code, what to reference during, and what to review after to reinforce. Page numbers reference Python Crash Course 3rd ed. (PCC) and Practical SQL 2nd ed. (PSQL). Free online resources are listed by URL or searchable title.

## Before Phase 1 — the dict→tuple mechanic and SQL foundations

This is the current blocker. The immediate task is converting a dictionary of column values into an ordered tuple that feeds `conn.execute(sql, params)`.

Study before writing:

- PCC Chapter 6, "Dictionaries" — accessing values by key (`row['cds_code']`), looping through keys, building new structures from dict contents. This is the core mechanic for every writer function.
- PCC Chapter 4, "List Comprehensions" — the `[row[col] for col in column_list]` pattern that builds an ordered list from a dict by walking a fixed sequence of keys. The list comprehension is the one-liner that ties dict access to tuple construction.
- `tuple()` — converting a list to a tuple. PCC Chapter 3 covers tuples as immutable sequences. The move is: list comprehension → `tuple()` → pass to `execute()`.
- Python docs, `sqlite3` module tutorial: `docs.python.org/3/library/sqlite3.html`. Read the "Tutorial" section top to bottom. It shows `cursor.execute(sql, params)` with `?` placeholders and a tuple. This is the contract your code has to satisfy.

Reference during:

- Your working `upsert_district()` in `db.py` — the structural template for every writer. The differences are the column count and the conflict target, not the shape.
- PSQL Chapter 4, "Data Types" — for verifying your INTEGER vs REAL vs TEXT decisions line up with what the data actually contains.

Review after:

- Run `python db.py` and use `sqlite3 data/edtrawl.db ".schema"` to confirm every table. Then insert a test row with `upsert_school()` and query it back with `SELECT * FROM schools WHERE cds_code = '...'`. Seeing your dict arrive as a database row closes the loop.


## Phase 1 continued — SQL cache pattern and JOINs

After the school/snapshot writers work, you build the travel-time cache. This introduces date comparisons and LEFT JOIN.

Study before writing:

- PSQL Chapter 7, "Joining Tables" — specifically LEFT JOIN. The concept: "give me every row from the left table, and if there's a matching row in the right table, include it; if not, fill those columns with NULL." This is the shape of `get_schools_missing_travel_time()`.
- PSQL Chapter 12 or the index entry for "date/time types and functions" — how date arithmetic works in SQL. SQLite's version is simpler than Postgres but the concept is the same: `date('now', '-90 days')` computes a boundary date you compare against.
- SQLite-specific date docs: search "sqlite date and time functions" — the official page at `sqlite.org/lang_datefunc.html`. Short, canonical, covers `date()`, `datetime()`, and the modifier syntax (`'-90 days'`).

Reference during:

- The TODO comments already in `db.py` for `get_cached_travel_time()` and `get_schools_missing_travel_time()` — they walk the logic in English; you're translating to SQL.

Exercise after:

- Insert two fake travel_time rows: one with `computed_on` set to today, one set to a year ago. Call `get_cached_travel_time()` with `max_age_days=90` for each school. Confirm the fresh one returns a row and the stale one returns None. Then call `get_schools_missing_travel_time()` and confirm the stale school shows up in the work queue. This is the test that proves the cache logic works.


## Phase 2 — CSV parsing and type coercion

Study before writing:

- Python docs, `csv` module: `docs.python.org/3/library/csv.html`. Read the `DictReader` section specifically — it reads each CSV row as a dict keyed by header names, which is exactly the input shape your writer functions expect. This is the bridge between the CDE file and `upsert_school(row)`.
- PCC Chapter 10, "Files and Exceptions" — the try/except pattern for type coercion. Each demographic cell needs `try: int(value)` with `except: None` as the fallback. This chapter teaches that flow. Also covers `with open(...)` for file handling.
- PCC Chapter 8, "Functions" — if you haven't revisited it recently. You'll write small helper functions like `parse_int(value)` and `parse_real(value)` that encapsulate the try/except coercion. Clean function decomposition matters here because you're applying the same logic to 40+ columns.

Reference during:

- Your two uploaded header files (the fixed/variable split) as the column-name reference.
- The actual CDE CSV download — open it in a text editor (not a spreadsheet) to see exact header strings, quoting, and encoding. `DictReader` needs the real header strings to match keys.

Exercise after:

- After ingesting 2025-26, write and run:
  ```sql
  SELECT cds_code, school_name, enroll_total
  FROM school_snapshots
  JOIN schools USING (cds_code)
  WHERE academic_year = '2025-26'
  ORDER BY enroll_total DESC
  LIMIT 10;
  ```
  This exercises the JOIN you studied in Phase 1 against real data. If it returns the ten largest schools with sensible enrollment numbers, your ingest and both tables are working correctly.


## Phase 3 — APIs, environment variables, and the pipeline pattern

Study before writing:

- PCC Chapter 17, "Working with APIs" — covers `requests`, JSON responses, API keys, and the request-response cycle. The travel-time API call is this chapter's subject matter in practice.
- Python docs, `os.environ` and/or `dotenv` — for loading `.env` values. If you're on Python 3.11+, the built-in `tomllib` can read config; for `.env` files specifically, the `python-dotenv` package is the standard. Read its README on PyPI: `pypi.org/project/python-dotenv/`.
- Your chosen travel-time provider's API docs — Google Routes, TravelTime, or Amazon Location. Read the "get started" and "request a route matrix" sections. The key concept is the departure_time / arrival_time parameter that activates traffic-aware estimates.

Concept to internalize:

- The "radius filter before API call" ordering. `within_radius()` is free (local math); travel-time is not. Filtering first is a cost-optimization pattern that applies everywhere you have a cheap filter guarding an expensive operation. This isn't in either book — it's a design principle. Think about it as: the cheapest request is the one you never make.


## Phase 4 — Playwright and browser automation

This phase is mostly hands-on rather than book-study.

Study before writing:

- Playwright docs, "Getting Started" for Node: `playwright.dev/docs/intro`. Read through "Writing tests" even though you're not testing — it teaches the selector, navigation, and waiting patterns you'll use in the scraper.
- Playwright docs, "Selectors": `playwright.dev/docs/selectors`. Specifically CSS selectors — `.class`, `#id`, `[attribute]`, and combinators. Your discovery.html output is what you'll match selectors against.
- MDN Web Docs, "CSS selectors": `developer.mozilla.org/en-US/docs/Web/CSS/CSS_selectors`. The canonical reference for selector syntax if Playwright's docs assume too much.

Exercise:

- Open `discovery.html` in a browser. Right-click a job listing → Inspect. Find the repeating element (a div, tr, or li that wraps one listing). Note its class name. That's your `resultRow` selector. Then find the child elements for title, link, location, posted date. Update the SELECTORS block. This is a hands-on DOM-reading exercise, not a coding one.


## Phase 5 — LLM integration for fuzzy matching

Study before writing:

- Anthropic API docs, "Getting started": `docs.anthropic.com`. Read the messages API section — sending a user message, getting a response. The fuzzy-matching call is a single request/response: you send edjoin's school string plus a candidate list, and ask for the best CDS code match.
- The `anthropic` Python SDK README on PyPI or GitHub — installation, basic usage, how to pass a system prompt and a user message.
- Prompt engineering basics: `docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview`. For the matching task, the key technique is giving the model a constrained output format (e.g., "respond with only the CDS code, nothing else") so parsing is trivial.

Concept to internalize:

- LLMs are tools for genuinely fuzzy tasks (ambiguous string matching where rules would be brittle), not routers or orchestrators. The Python pipeline owns control flow; the LLM owns "which of these 12 school names best matches this edjoin string." That boundary was a design decision made early in this project.


## Phase 6 — Queries and output

Study before writing:

- PSQL chapters on subqueries and multi-table joins — your final query joins four tables (`jobs`, `schools`, `school_snapshots`, `travel_times`) with WHERE filters on travel minutes, posting date, and school-level criteria. Practice building this query incrementally: start with a two-table join, add a third, then a fourth.
- Python `csv.DictWriter` (in the `csv` module docs) for writing output CSVs.

Exercise:

- Write the "holy grail" query on paper before coding it: "jobs within 45 minutes of home, posted in the last 14 days, at non-charter high schools with enrollment over 500." Identify which table each filter comes from. That mapping — filter to table — is the mental model for multi-table queries.


## Ongoing references to keep open

- SQLite official docs: `sqlite.org/docs.html` — particularly "SQL Language Expressions" and "INSERT."
- Python docs, `sqlite3` module: `docs.python.org/3/library/sqlite3.html`.
- Your own `upsert_district()` as the canonical worked example.
- This document itself — revisit the "exercise after" sections; they're designed to confirm each phase actually works before you build on top of it.
