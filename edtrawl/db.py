# db.py — SQLite layer for EdTrawl.

# Tables (see SCHEMA below):
#     schools        - one row per school, linked to its district DONE
#     schools_snapshots - annual updates of variable data  DONE
#     travel_times   - cached minutes from home, per school (the expensive cache) 
#     jobs           - job listings, linked to a school

import sqlite3
from pathlib import Path

# Store the db next to the data files, not next to the code.
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "edtrawl.db"


def get_connection() -> sqlite3.Connection:
    """Open a connection with the settings we want on EVERY connection.

    Two settings worth understanding:

    1. row_factory = sqlite3.Row
       Without this, a fetched row is a plain tuple: row[0], row[1], ...
       With it, you get dict-like access: row["name"], row["lat"].
       Far less error-prone than remembering column positions.

    2. PRAGMA foreign_keys = ON
       This is the big one. SQLite does NOT enforce foreign keys by default —
       you can insert a school pointing at a district_id that doesn't exist and
       it will happily accept it. The pragma has to be turned on PER CONNECTION,
       every time. Forgetting it is one of the most common SQLite surprises.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# -----------------------------------------------------------------------------
# SCHEMA
# Each table is its own CREATE statement. "IF NOT EXISTS" makes init_db()
# safe to run repeatedly — it won't error if the table is already there.
# -----------------------------------------------------------------------------

SCHEMA = [
       """
    CREATE TABLE IF NOT EXISTS schools (
        cds_code          TEXT PRIMARY KEY,
        academic_year     TEXT,
        fed_id            TEXT,
        district_code     TEXT,
        school_code       TEXT,
        region            TEXT,
        county_name       TEXT,
        district_name     TEXT,
        school_name       TEXT,
        school_type       TEXT,
        open_date         TEXT,
        school_level      TEXT,
        grade_low         TEXT,
        grade_high        TEXT,
        charter           TEXT,
        charter_num       TEXT,
        street            TEXT,
        city              TEXT,
        zip               TEXT,
        state             TEXT,
        locale            TEXT,
        school_website    TEXT,
        latitude          REAL,  
        longitude         REAL
    );
    """,

    """
    CREATE TABLE IF NOT EXISTS schools_snapshots (
        cds_code                TEXT,
        academic_year           TEXT,
        charter_fund_type       TEXT,
        virtual                 TEXT,
        magnet                  TEXT,
        title_i                 TEXT,
        dass                    TEXT,
        essa                    TEXT,
        enroll_total            INTEGER,
        african_amer            INTEGER,
        african_amer_pct        REAL,
        amer_indian             INTEGER,
        amer_indian_pct         REAL,
        asian                   INTEGER,
        asian_pct               REAL,
        filipino                INTEGER,
        filipino_pct            REAL,            
        hispanic                INTEGER,
        hispanic_pct            REAL,
        pac_islander            INTEGER,
        pac_islander_pct        REAL,
        white                   INTEGER,
        white_pct               REAL,
        two_or_more_races       INTEGER,
        two_or_more_races_pct   REAL,
        not_reported            TEXT,
        not_reported_pct        REAL,
        english_learner         INTEGER,
        english_learner_pct     REAL,
        foster                  INTEGER,
        foster_pct              REAL,
        homeless                INTEGER,
        homeless_pct            REAL,
        migrant                 INTEGER,
        migrant_pct             REAL,
        soc_disadvantaged       INTEGER,
        soc_disadvantaged_pct   REAL,
        students_with_dis       INTEGER,
        students_with_dis_pct   REAL,
        free_reduced_meal       INTEGER,
        free_reduced_meal_pct   REAL,
        grade_tk                INTEGER,
        grade_kg                INTEGER,
        grade_01                INTEGER,
        grade_02                INTEGER,
        grade_03                INTEGER,
        grade_04                INTEGER,
        grade_05                INTEGER,
        grade_06                INTEGER,           
        grade_07                INTEGER,
        grade_08                INTEGER,
        grade_09                INTEGER,
        grade_10                INTEGER,
        grade_11                INTEGER,
        grade_12                INTEGER,
        staff_total             INTEGER,
        staff_teachers          INTEGER,
        staff_admin             INTEGER,
        staff_pupil_svcs        INTEGER,
        staff_other             INTEGER,
        snapshot_row_updated    DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (cds_code, academic_year),
        FOREIGN KEY (cds_code) REFERENCES schools(cds_code)
        
    );
    """,
]

def init_db() -> None:
    """Create every table. Safe to run as many times as you like."""
    with get_connection() as conn:
        for statement in SCHEMA:
            # Skip the commented-out TODO blocks so the file runs before you've
            # finished them. Once you write real SQL in a block, it executes.
            if "CREATE TABLE" in statement:
                conn.executescript(statement)
    print(f"Initialized database at {DB_PATH}")

# -----------------------------------------------------------------------------
# WRITES
# Note every query uses  ?  placeholders instead of f-strings / string
# concatenation. This is parameterization: the driver handles quoting and makes
# SQL injection impossible. Get in the habit now even for a personal tool.
# -----------------------------------------------------------------------------

SCHOOL_COLUMNS = [
        "academic_year", "fed_id", "cds_code", "district_code", "school_code", "region", "county_name", 
        "district_name", "school_name", "school_type", "open_date", "school_level", 
        "grade_low", "grade_high", "charter", "charter_num", "street", "city", "zip", 
        "state", "locale", "school_website", "latitude", "longitude" 
    ]

def upsert_schools(academic_year: str, cds_code: str, fed_id: str, district_code: str, school_code: str, region: str, county_name: str, district_name: str, school_name: str, school_type: str, open_date: str, school_level: str, grade_low: str, grade_high: str, charter: str, charter_num: str, street: str, city: str, zip: str, state: str, locale: str, school_website: str | None = None, latitude: float | None = None, longitude: float | None = None) -> int:
    
    SQL = """
        INSERT INTO schools (academic_year, cds_code, fed_id, district_code, school_code, region, county_name, district_name, school_name, school_type, open_date, school_level, grade_low, grade_high, charter, charter_num, street, city, zip, state, locale, school_website, latitude, longitude)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (cds_code) DO 
        UPDATE  
        SET
          academic_year  = excluded.academic_year,
          fed_id         = excluded.fed_id,
          district_code  = excluded.district_code,
          school_code    = excluded.school_code,
          region         = excluded.region,
          county_name    = excluded.county_name,
          district_name  = excluded.district_name,
          school_name    = excluded.school_name,
          school_type    = excluded.school_type,
          open_date      = excluded.open_date,
          school_level   = excluded.school_level,
          grade_low      = excluded.grade_low,
          grade_high     = excluded.grade_high,
          charter        = excluded.charter,
          charter_num    = excluded.charter_num,
          street         = excluded.street,
          city           = excluded.city,
          zip            = excluded.zip,
          state          = excluded.state,
          locale         = excluded.locale,
          school_website = excluded.school_website,
          latitude = COALESCE(excluded.latitude, schools.latitude),
          longitude = COALESCE(excluded.longitude, schools.longitude)
        WHERE excluded.academic_year > schools.academic_year
        RETURNING cds_code;
        
    """
    with get_connection() as conn:
        row = conn.execute(SQL, (academic_year, cds_code, fed_id, district_code, school_code, region, county_name, district_name, school_name, school_type, open_date, school_level, grade_low, grade_high, charter, charter_num, street, city, zip, state, locale, school_website, latitude, longitude)).fetchone()
        return row ["cds_code"]
 

SCHOOL_SNAPSHOT_COLUMNS = [
         "academic_year", "cds_code", "charter_fund_type", "virtual", "magnet", "title_i", "dass", "essa", "enroll_total", "african_amer", "african_amer_pct", "amer_indian", "amer_indian_pct", "asian", "asian_pct", "filipino", "filipino_pct", "hispanic", "hispanic_pct", "pac_islander", "pac_islander_pct", "white", "white_pct", "two_or_more_races", "two_or_more_races_pct", "not_reported", "not_reported_pct", "english_learner", "english_learner_pct", "foster", "foster_pct", "homeless", "homeless_pct", "migrant", "migrant_pct", "soc_disadvantaged", "soc_disadvantaged_pct", "students_with_dis", "students_with_dis_pct", "free_reduced_meal", "free_reduced_meal_pct", "grade_tk", "grade_kg", "grade_01", "grade_02", "grade_03", "grade_04","grade_05","grade_06","grade_07","grade_08","grade_09","grade_10","grade_11","grade_12","staff_total","staff_teachers","staff_admin","staff_pupil_svcs","staff_other"
    ] 

def upsert_schools_snapshots(data: tuple) -> None:
    cols         = ", ".join(SCHOOL_SNAPSHOT_COLUMNS)
    placeholders = ", ".join("?" * len(SCHOOL_SNAPSHOT_COLUMNS))
    
    SQL = f"""
        INSERT INTO schools_snapshots ({cols})
        VALUES ({placeholders})
        ON CONFLICT(cds_code, academic_year) DO NOTHING
    """
    with get_connection() as conn:
        row = conn.execute(SQL, data)

if __name__ == "__main__":
    # Running `python db.py` directly initializes the database.
    # As you complete the TODOs, add quick test calls here to check them, e.g.:
    #     init_db()
    #     did = upsert_district("Whittier Union High School District")
    #     print("district id:", did)
    init_db()

# move a copy of this list over to the ingest so I can see the data order clearly in both 
# data: tuple[cds_code, academic_year, charter_fund_type, virtual, magnet, title_i, dass, essa, enroll_total, african_amer, african_amer_pct, amer_indian, amer_indian_pct, asian, asian_pct, filipino, filipino_pct, hispanic, hispanic_pct, pac_islander, pac_islander_pct, white, white_pct, two_or_more_races, two_or_more_races_pct, not_reported, not_reported_pct, english_learner, english_learner_pct, foster, foster_pct, homeless, homeless_pct, migrant, migrant_pct, soc_disadvantaged, soc_disadvantaged_pct, students_with_dis, students_with_dis_pct, free_reduced_meal, free_reduced_meal_pct, grade_tk, grade_kg, grade_01, grade_02, grade_03, grade_04, grade_05, grade_06, grade_07, grade_08, grade_09, grade_10, grade_11, grade_12, staff_total, staff_teachers, staff_admin, staff_pupil_svcs, staff_other]
