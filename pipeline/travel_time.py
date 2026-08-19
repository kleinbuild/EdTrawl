"""
travel_time.py — minutes between home and a school at fixed clock times.

Requirement that drives the provider choice: you need TRAFFIC-AWARE times at a
specific time of day (arrive 7:00am, depart 3:30pm). That rules out plain
OpenRouteService (no traffic model) and points to Google Routes / Distance
Matrix Advanced, TravelTime, or Amazon Location — any provider that accepts a
departure/arrival time and applies predictive traffic.

Because you compute this once per school and cache it, your volume is tiny and
should sit inside the free tier of any of them.

Planned shape:
    travel_minutes(home: tuple[float, float],
                   school: tuple[float, float]) -> tuple[int, int] | None
        Returns (arrive_min, depart_min):
            arrive_min = home -> school, arriving 7:00am
            depart_min = school -> home, departing 3:30pm
        These are two separate one-way requests (morning vs afternoon traffic
        differ). Return None if the route can't be computed.

The DB caching (save_travel_time / get_cached_travel_time) lives in db.py — this
module just makes the API call; db.py decides whether the call is even needed.
"""

HOME_ARRIVAL = "07:00"    # arrive at the school by this time
HOME_DEPARTURE = "15:30"  # leave the school at this time

# TODO: implement travel_minutes()
