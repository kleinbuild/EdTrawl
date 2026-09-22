"""
match.py — filter schools/jobs against your commute constraints.
It readsncached coordinates and travel times and decides what clears your bar.

Planned shape:
    within_radius(home, school, miles) -> bool
        Straight-line (haversine) distance filter. Cheap first pass 
        
    within_commute(school_id, max_minutes) -> bool
        The real filter, using the cached travel_times (both directions).

Order matters for cost: radius-filter first (free, local), THEN travel-time the
survivors. That ordering is what keeps API usage minimal.
"""

from math import radians, sin, cos, asin, sqrt


def haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in miles between two lat/lng points.
    """
    r = 3958.8  # Earth radius in miles
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * r * asin(sqrt(a))


# TODO: within_radius(), within_commute()
