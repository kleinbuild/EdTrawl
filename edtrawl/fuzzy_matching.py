import sqlite3
from pathlib import Path


from rapidfuzz.process import extractOne

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "edtrawl.db"


# Planned shape:
#     get_coordinates
#         SQL Query to rapidfuzz matching; returns lat/long and cds code to add to listings row



def get_coordinates()
    """uses rapidfuzz to find match and then adds coordinates and cds_code to listing
    """
