"""
geocode.py — turn a street address into (lat, lng).

This is an "expensive" call (API key, rate limits), so it follows the same
cache-once rule as travel_time: check the DB for coordinates first, only call
the API when they're missing, then write them back.

Planned shape:
    geocode_address(address: str) -> tuple[float, float] | None
        Call whichever provider you settle on (Google Geocoding, or the free
        Nominatim/OpenStreetMap for light use). Return (lat, lng), or None if
        the address can't be resolved.

Fill in once you've picked a provider and put its key in .env.
"""

# TODO: implement geocode_address()
