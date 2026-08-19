# EdTrawl — Vocabulary and Syntax Reference

Terms, concepts, and syntax patterns you need for this project, grouped by domain. Each entry states what it is, why it matters for EdTrawl, and (where applicable) the syntax.


## Python fundamentals

**dict (dictionary)** — A collection of key-value pairs. `{"cds_code": "19647331930023", "school_name": "Whittier HS"}`. Keys are strings (or any hashable type); values are anything. Accessed by key: `row["cds_code"]`. This is the shape your CSV parser produces per row, and the input to every database writer function.

**tuple** — An immutable ordered sequence. `("19647331930023", "Whittier HS")`. Created with parentheses or `tuple()`. Tuples are what `sqlite3`'s `execute()` expects as the parameter sequence for `?` placeholders. A tuple's order matters — position 0 maps to the first `?`, position 1 to the second, and so on.

**list** — A mutable ordered sequence. `["cds_code", "school_name"]`. Created with brackets. You'll use a list of column names as the fixed order that controls how dicts get converted to tuples.

**list comprehension** — A one-line loop that builds a list. `[row[col] for col in columns]` walks `columns` in order, pulls each value from `row`, and collects them into a new list. This is the dict→tuple bridge.

**`tuple(iterable)`** — Converts a list (or any iterable) to a tuple. `tuple([1, 2, 3])` → `(1, 2, 3)`. Used after a list comprehension to produce the parameter tuple for `execute()`.

**type hint** — An annotation on a function parameter or return value. `def foo(name: str, lat: float | None = None) -> int:` says `name` is a str, `lat` is either a float or None (defaulting to None), and the function returns an int. Type hints don't enforce anything at runtime — they're documentation for humans and tools. The `: ` in a type hint is not the same as `: ` in a dict literal.

**default parameter value** — `= None` after a parameter in a function signature means "if the caller doesn't supply this argument, use None." Not the same as a dict value. Only applies in `def` lines.

**`try` / `except`** — Exception handling. `try:` runs code that might fail; `except ValueError:` catches a specific error type and runs fallback code. Used in type coercion: `try: return int(value)` / `except (ValueError, TypeError): return None`. This is how you turn unparseable demographic cells into NULL.

**`with` statement (context manager)** — `with open(file) as f:` or `with get_connection() as conn:`. Guarantees cleanup (closing the file or committing/rolling back the transaction) even if an error occurs inside the block. Every database operation in your code uses this.

**f-string** — `f"Found {count} schools"`. Embeds expressions inside string literals. Fine for log messages. Never use for SQL queries (see parameterization below).

**`pathlib.Path`** — Object-oriented file paths. `Path(__file__).resolve().parent` gives the directory containing the current script. Used in `db.py` to locate `edtrawl.db` relative to the code, not hardcoded.


## Python's `sqlite3` module

**`sqlite3.connect(path)`** — Opens (or creates) a SQLite database file. Returns a Connection object.

**`conn.execute(sql, params)`** — Runs one SQL statement with parameterized values. `params` is a tuple whose values replace the `?` placeholders in `sql`, in order. Returns a Cursor you can call `.fetchone()`, `.fetchall()`, or `.fetchmany()` on.

**`conn.executescript(sql)`** — Runs multiple SQL statements separated by `;`. Used for schema creation. Does not support `?` parameterization — only for DDL (CREATE, DROP), never for data.

**`conn.row_factory = sqlite3.Row`** — Makes fetched rows behave like dicts: `row["column_name"]` instead of `row[0]`. Set once per connection.

**`cursor.fetchone()`** — Returns the next row from a query result, or None if no rows remain.

**`cursor.fetchall()`** — Returns all remaining rows as a list.

**Parameterization (`?` placeholders)** — The practice of using `?` in SQL and passing values as a separate tuple, instead of embedding values in the SQL string with f-strings or concatenation. Prevents SQL injection (a security vulnerability where user-supplied text is interpreted as SQL commands). Habit: always parameterize, even in personal tools. Syntax: `conn.execute("SELECT * FROM schools WHERE cds_code = ?", (cds_code,))`. Note the trailing comma in `(cds_code,)` — that makes it a one-element tuple; without the comma, Python sees just parentheses around a value.

**PRAGMA** — A SQLite-specific command that sets database-level configuration. `PRAGMA foreign_keys = ON;` enables foreign key enforcement for the current connection. Must be run on every new connection; it's not stored in the database.


## SQL — Data Definition (DDL)

**CREATE TABLE** — Defines a table's structure: column names, types, and constraints. `IF NOT EXISTS` makes it safe to run repeatedly.

**column type (storage class)** — SQLite has five: NULL, INTEGER, REAL, TEXT, BLOB. Every value stored is one of these. Type names in CREATE TABLE (VARCHAR, BOOL, DATE, NUMERIC) are mapped to these five by "type affinity" rules — they work but they're aliases, not distinct types. In EdTrawl: identifiers and labels are TEXT, counts are INTEGER, percentages are REAL, coordinates are REAL, Y/N flags are TEXT, dates are TEXT (ISO-8601 strings).

**PRIMARY KEY** — The column (or columns) that uniquely identify each row. No two rows can have the same primary key value. Implies NOT NULL and UNIQUE. In `schools`, it's `cds_code` alone. A single column: declared inline after the type. A composite key across multiple columns: declared as a separate line, `PRIMARY KEY (col_a, col_b)`.

**composite primary key** — A primary key made of two or more columns. The *combination* must be unique, not each column individually. `PRIMARY KEY (cds_code, academic_year)` means one row per school per year — `cds_code` can repeat (same school, different years), `academic_year` can repeat (different schools, same year), but the pair cannot.

**UNIQUE** — A constraint that forbids duplicate values. Can be on one column (`name TEXT UNIQUE`) or a combination (`UNIQUE(district_id, name)`). Similar to a primary key but a table can have multiple UNIQUE constraints. Also the mechanism that ON CONFLICT detects.

**NOT NULL** — A constraint that forbids NULL values in a column. Primary keys are automatically NOT NULL.

**FOREIGN KEY** — A constraint that says "this column's value must exist in another table's column." `FOREIGN KEY (cds_code) REFERENCES schools(cds_code)` means every `cds_code` in `school_snapshots` must already be a `cds_code` in `schools`. Prevents orphan rows. SQLite does NOT enforce foreign keys by default — you must run `PRAGMA foreign_keys = ON` per connection.

**TEXT vs INTEGER for identifiers** — Identifiers (CDS codes, ZIP codes, federal IDs) look like numbers but aren't — they can have leading zeros, you never do arithmetic on them, and their numeric value is meaningless. Store as TEXT. Storing as INTEGER silently drops leading zeros and breaks cross-dataset joins.


## SQL — Data Manipulation (DML)

**INSERT INTO** — Adds a new row. `INSERT INTO schools (cds_code, school_name) VALUES (?, ?)`.

**UPSERT (INSERT ... ON CONFLICT ... DO UPDATE SET)** — Tries to insert; if a row with the same UNIQUE/PK value already exists, updates instead of erroring. The conflict target (in parentheses after ON CONFLICT) must name columns that have a UNIQUE or PRIMARY KEY constraint. Single-column: `ON CONFLICT (cds_code)`. Composite: `ON CONFLICT (cds_code, academic_year)`.

**`excluded` table** — Inside an ON CONFLICT DO UPDATE SET clause, `excluded.column_name` refers to the value that was *attempted* in the INSERT (the new/incoming value), as opposed to the value already stored in the table. So `school_name = excluded.school_name` means "overwrite the stored name with the incoming one."

**COALESCE(a, b)** — Returns the first non-NULL argument. `COALESCE(excluded.latitude, schools.latitude)` means "use the incoming latitude if it's not NULL; otherwise keep the existing one." Used to protect already-good values from being overwritten by a NULL in a later upsert.

**RETURNING** — Appended to INSERT/UPDATE/DELETE to return column values from the affected row(s). `INSERT INTO districts (...) VALUES (...) RETURNING id;` gives back the auto-assigned id. Not needed when you already know the key (as with `cds_code`).

**SELECT** — Retrieves rows. `SELECT cds_code, school_name FROM schools WHERE county_name = 'Los Angeles';`

**WHERE** — Filters rows. Supports `=`, `!=`, `>`, `<`, `>=`, `<=`, `LIKE`, `IN`, `IS NULL`, `IS NOT NULL`, `AND`, `OR`. Date comparison: `WHERE computed_on >= date('now', '-90 days')`.

**JOIN / LEFT JOIN** — Combines rows from two tables based on a matching column. `JOIN` (inner join) returns only rows that match in both tables. `LEFT JOIN` returns every row from the left table, with NULLs for unmatched right-table columns. `LEFT JOIN` is how you find "schools with no travel_time row" — the unmatched rows have `travel_times.cds_code IS NULL`.

**USING (column)** — Shorthand for a join condition when the join column has the same name in both tables. `JOIN school_snapshots USING (cds_code)` is equivalent to `JOIN school_snapshots ON schools.cds_code = school_snapshots.cds_code`.

**ORDER BY** — Sorts results. `ORDER BY enroll_total DESC` for largest first.

**LIMIT** — Caps the number of returned rows. `LIMIT 10`.

**Aggregate functions** — `COUNT(*)`, `SUM(column)`, `AVG(column)`, `MIN()`, `MAX()`. Used with `GROUP BY` to compute per-group summaries. `COUNT(column)` skips NULLs; `COUNT(*)` counts all rows.

**GROUP BY** — Groups rows for aggregation. `SELECT district_name, COUNT(*) FROM schools GROUP BY district_name` gives school count per district.


## SQL — SQLite-specific

**`date('now')` and modifiers** — SQLite's date function. `date('now')` returns today as `'YYYY-MM-DD'`. `date('now', '-90 days')` returns the date 90 days ago. Used in the travel-time freshness check. Dates stored as ISO-8601 TEXT sort and compare correctly as strings because the format is lexicographically ordered.

**rowid** — SQLite silently gives every table (except WITHOUT ROWID tables) an auto-incrementing integer row identifier. If you declare `id INTEGER PRIMARY KEY`, it becomes an alias for rowid. You get this for free; you don't always need to declare it explicitly.

**Type affinity** — SQLite's rule for mapping declared type names to the five storage classes. "VARCHAR" → TEXT affinity. "BOOL" → NUMERIC affinity (not what you'd expect). "INT", "INTEGER" → INTEGER affinity. Understanding this explains why `BOOL` doesn't behave like a boolean and why you should use the real storage class names.


## Database design concepts

**identity table vs snapshot table** — Separating data that describes *what something is* (name, location, type — changes rarely) from data that describes *its state at a point in time* (enrollment, demographics, staff — changes yearly). The identity table has one row per entity; the snapshot table has one row per entity per time period. Linked by a shared key.

**natural key vs surrogate key** — A natural key is a real-world identifier (`cds_code`). A surrogate key is an invented internal identifier (`id INTEGER PRIMARY KEY`). Natural keys are meaningful and joinable across datasets; surrogate keys are compact and never change. EdTrawl uses CDS code (natural) as the primary key because it's the join key to every California education dataset.

**denormalization** — Storing redundant data to avoid a join. `schools` carries `district_name` and `district_code` directly instead of joining to a separate districts table. Trades storage for query simplicity. Appropriate when the related entity (district) doesn't yet have its own rich data.

**upsert** — Insert-or-update in one statement. The pattern for idempotent data loading: running the same ingest twice produces the same result, not duplicate rows.

**cache table** — A table whose purpose is to remember expensive-to-compute results. `travel_times` stores API responses so you don't re-call the maps API for schools you've already computed. The freshness check (`computed_on` vs `max_age_days`) is the cache-invalidation policy.


## Naming conventions

**snake_case** — `lowercase_with_underscores`. Used for: Python variables/functions, SQL column names, SQL table names, npm package names. The dominant convention in both Python and SQL.

**camelCase** — `firstWordLowerRestCapitalized`. Used for: JavaScript variables and functions.

**PascalCase** — `EveryWordCapitalized`. Used for: Python/JS class names, React components, tool brand names (EdTrawl, Playwright).

**kebab-case** — `lowercase-with-hyphens`. Used for: npm packages, repo names, URLs, CSS classes. Can't be used as identifiers in Python/JS (hyphen reads as minus).

**SCREAMING_SNAKE_CASE** — `ALL_CAPS_WITH_UNDERSCORES`. Used for: constants, environment variables (`HOME_LAT`, `MAPS_API_KEY`).


## File and project concepts

**`.env` file** — Stores environment-specific configuration (API keys, home coordinates) as `KEY=VALUE` lines. Never committed to git. Loaded at runtime by `python-dotenv` or Node's `--env-file` flag.

**`.env.example`** — Committed template showing which keys are expected, with no values. Documents the config contract for future-you or other users.

**`.gitignore`** — Lists files/patterns git should never track. Critical for secrets (`auth_state.json`, `.env`) and generated output (`edtrawl.db`, `results.csv`, `node_modules/`).

**`storageState` (Playwright)** — A JSON file containing cookies and localStorage from a browser session. Captures "logged in as you" without storing your password. Equivalent to a session token — treat it as a secret.

**ISO-8601** — The international date format: `YYYY-MM-DD` (e.g., `2026-08-17`). Used for dates in SQLite because it sorts correctly as a plain string comparison — `'2025-01-15' < '2026-08-17'` is true both lexicographically and chronologically. Also the format returned by Python's `date.today().isoformat()`.
