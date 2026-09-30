import sqlite3
from pathlib import Path
from edtrawl.db import get_listings_needing_school_match, get_listings_needing_district_match, update_listings_district_match, update_listings_school_match, get_schools_in_district

from rapidfuzz import fuzz
from rapidfuzz.process import extractOne

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "edtrawl.db"


# Planned shape:
#     get_coordinates
#         SQL Query to rapidfuzz matching; returns lat/long and cds code to add to listings row

    print(f"Processing row {posting_id}...", flush=True)

def best_school_match(position_title: str, district_name: str):
    candidates = get_schools_in_district(district_name)
    if not candidates:
        return None, None, None

    choices = {cds_code: school_name for cds_code, school_name in candidates}

    result = extractOne(position_title, choices, scorer=fuzz.partial_ratio)
    if result is None:
        return None, None, None

    school_name, score, cds_code = result
    return school_name, cds_code, score

THRESHOLD = 85

for posting_id, position_title, district_name in get_listings_needing_school_match():
    name, cds_code, score = best_school_match(position_title, district_name)

    if name is None:
        status = "no_match"
    elif score < THRESHOLD:
        status = "below_threshold"
    else:
        status = "matched"

    update_listings_school_match((name, cds_code, score, status, posting_id))


#output_file.write(f"\n--- Processed {row_count} total rows ---\n")
# def get_coordinates()
#     """uses rapidfuzz to find match and then adds coordinates and cds_code to listing
#     """
