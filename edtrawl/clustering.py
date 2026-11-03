"""
clustering.py — collapse schools on the same campus / block into "school clusters".

[Claude-written]

Why: drive-time lookups are the expensive step (see travel_time.py). Many
schools share a campus or sit across the street from each other (an elementary
and a middle school on one lot, a charter in a district building, etc.), so
their drive times from home are effectively identical. Clustering them means we
compute one drive time per cluster instead of one per school.

How it works:
    1. Load cds_code / latitude / longitude from the `schools` table (filled by
       csv_ingest.py). Skip rows with missing or impossible coordinates.
    2. DBSCAN with the haversine metric groups every school that is within
       `radius_miles` of another school in the group. min_samples=1 means a
       school with no neighbors becomes its own one-school cluster.
    3. DBSCAN "chains": A near B, B near C, C near D... can produce a cluster
       miles long. Any cluster whose widest pair of schools is farther apart
       than `max_span_miles` is split with complete-linkage clustering
       (explained in _split_by_max_distance below).
    4. Optional (off by default): ask a self-hosted OSRM server for drive times
       inside each multi-school cluster and split clusters where two members
       are more than `max_internal_minutes` apart by road (a freeway or river
       between two schools that look close on a map).
    5. Write the result to two tables in data/edtrawl.db:
           school_clusters        (cluster_id, centroid_lat, centroid_lon, n_schools, max_span_miles)
           school_cluster_members (cds_code, cluster_id)

Usage:
    python -m edtrawl.clustering                  # build clusters at 0.4 mi and save them
    python -m edtrawl.clustering --radius 0.25    # different radius
    python -m edtrawl.clustering --compare        # radius comparison report (no DB writes)
    python -m edtrawl.clustering --osrm           # also split by drive time via OSRM
    python -m edtrawl.clustering --osrm --osrm-url http://localhost:5000 --max-internal-minutes 3
"""
import argparse
import math
import sys
from dataclasses import dataclass, field

import numpy as np
import requests
from sklearn.cluster import DBSCAN, AgglomerativeClustering
from sklearn.metrics.pairwise import haversine_distances

from edtrawl.db import get_school_coordinates, replace_school_clusters

EARTH_RADIUS_MILES = 3958.8  # same constant as match.haversine_miles

# Anything outside this box is not a California school — treat it as a bad
# coordinate (catches 0,0 placeholders, swapped lat/lon, missing minus signs).
CA_LAT_RANGE = (32.0, 42.5)
CA_LON_RANGE = (-124.6, -114.0)

DEFAULT_RADIUS_MILES = 0.4
DEFAULT_MAX_SPAN_MILES = 0.75
DEFAULT_OSRM_URL = "http://localhost:5000"
DEFAULT_MAX_INTERNAL_MINUTES = 3.0
COMPARE_RADII = (0.1, 0.25, 0.4, 0.5, 0.75)

# Stand-in for "OSRM found no route" so the split treats the pair as far apart.
_NO_ROUTE_MINUTES = 1e6


class OSRMError(RuntimeError):
    """OSRM is unreachable or returned an error."""


@dataclass
class ClusterResult:
    ids: list                  # school IDs (cds_code) that were clustered
    lats: np.ndarray
    lons: np.ndarray
    groups: list               # one np.ndarray of row indexes per cluster
    skipped: list = field(default_factory=list)  # IDs with missing/invalid coords
    largest_before_split: int = 0  # biggest raw DBSCAN cluster (shows chaining)
    n_split_by_span: int = 0
    n_split_by_drive_time: int = 0

    @property
    def n_schools(self) -> int:
        return len(self.ids)

    @property
    def n_clusters(self) -> int:
        return len(self.groups)

    @property
    def largest_cluster(self) -> int:
        return max((len(g) for g in self.groups), default=0)

    def cluster_rows(self) -> list[tuple]:
        """(cluster_id, centroid_lat, centroid_lon, n_schools, max_span_miles)"""
        rows = []
        for cluster_id, g in enumerate(self.groups, start=1):
            span = _max_pairwise_miles(self.lats[g], self.lons[g])
            rows.append((
                cluster_id,
                round(float(self.lats[g].mean()), 6),
                round(float(self.lons[g].mean()), 6),
                len(g),
                round(span, 4),
            ))
        return rows

    def member_rows(self) -> list[tuple]:
        """(cds_code, cluster_id)"""
        return [
            (self.ids[i], cluster_id)
            for cluster_id, g in enumerate(self.groups, start=1)
            for i in g
        ]


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _clean_coordinate(lat, lon) -> tuple[float, float] | None:
    """Return (lat, lon) as floats, or None if missing / not a CA location."""
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(lat) and math.isfinite(lon)):
        return None
    if not (CA_LAT_RANGE[0] <= lat <= CA_LAT_RANGE[1]):
        return None
    if not (CA_LON_RANGE[0] <= lon <= CA_LON_RANGE[1]):
        return None
    return lat, lon


def _distance_matrix_miles(lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    coords = np.radians(np.column_stack([lats, lons]))
    return haversine_distances(coords) * EARTH_RADIUS_MILES


def _max_pairwise_miles(lats: np.ndarray, lons: np.ndarray) -> float:
    if len(lats) < 2:
        return 0.0
    return float(_distance_matrix_miles(lats, lons).max())


def _split_by_max_distance(dist: np.ndarray, limit: float) -> np.ndarray:
    """Split one cluster so no two members are more than `limit` apart.

    Uses complete-linkage agglomerative clustering. In complete linkage the
    distance between two groups is the distance between their two FARTHEST
    members, so with distance_threshold=limit two groups are only merged if the
    merged group's widest pair is still within the limit. That is exactly the
    rule we want, so it is guaranteed to hold after one pass — no loop of
    "shrink eps and try again" (DBSCAN can still chain at a smaller eps) and no
    guessing a k for k-means (which minimizes average spread, not the max).

    The same function handles miles (span limit) and minutes (OSRM drive time).
    Returns a label per row of `dist`.
    """
    # sklearn won't merge at a distance *equal* to the threshold; nudge it up
    # so a pair exactly at the limit is allowed (the rule is "exceeds").
    threshold = float(np.nextafter(limit, np.inf))
    model = AgglomerativeClustering(
        n_clusters=None,
        metric="precomputed",
        linkage="complete",
        distance_threshold=threshold,
    )
    return model.fit_predict(dist)


def _apply_split(groups: list, needs_split) -> tuple[list, int]:
    """Run `needs_split(group) -> labels | None` over each multi-school group.

    Returns the new list of groups and how many groups were split.
    """
    out, n_split = [], 0
    for g in groups:
        labels = needs_split(g) if len(g) > 1 else None
        if labels is None:
            out.append(g)
            continue
        pieces = [g[labels == k] for k in np.unique(labels)]
        if len(pieces) > 1:
            n_split += 1
        out.extend(pieces)
    return out, n_split


# -----------------------------------------------------------------------------
# OSRM (optional road-network check)
# -----------------------------------------------------------------------------

def osrm_duration_minutes(lats, lons, osrm_url: str = DEFAULT_OSRM_URL) -> np.ndarray:
    """Drive-time matrix in minutes from OSRM's /table endpoint.

    result[i][j] = minutes driving from point i to point j. Pairs OSRM can't
    route come back as a very large number.
    """
    # OSRM wants lon,lat — the opposite of how we store them.
    coord_str = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in zip(lats, lons))
    url = f"{osrm_url.rstrip('/')}/table/v1/driving/{coord_str}"
    try:
        resp = requests.get(url, params={"annotations": "duration"}, timeout=30)
    except requests.RequestException as e:
        raise OSRMError(
            f"Could not reach the OSRM server at {osrm_url} ({type(e).__name__}). "
            f"Start it (or pass --osrm-url), or run without --osrm."
        ) from e

    try:
        data = resp.json()
    except ValueError:
        raise OSRMError(
            f"{osrm_url} answered with HTTP {resp.status_code} but not OSRM JSON — "
            f"is something else running on that port?"
        )
    if resp.status_code != 200 or data.get("code") != "Ok":
        raise OSRMError(
            f"OSRM /table request failed: HTTP {resp.status_code}, "
            f"code={data.get('code')!r}, message={data.get('message')!r}. "
            f"(A 'TooBig' code means the cluster has more points than the "
            f"server's --max-table-size.)"
        )

    durations = np.array(
        [[np.nan if d is None else d for d in row] for row in data["durations"]],
        dtype=float,
    )
    minutes = durations / 60.0
    minutes[np.isnan(minutes)] = _NO_ROUTE_MINUTES
    return minutes


def check_osrm_reachable(osrm_url: str, lat: float, lon: float) -> None:
    """Fail fast (before any clustering work) if OSRM isn't usable."""
    osrm_duration_minutes([lat, lat], [lon, lon], osrm_url)


# -----------------------------------------------------------------------------
# Main entry points
# -----------------------------------------------------------------------------

def cluster_schools(
    ids,
    lats,
    lons,
    radius_miles: float = DEFAULT_RADIUS_MILES,
    max_span_miles: float = DEFAULT_MAX_SPAN_MILES,
    check_drive_time: bool = False,
    osrm_url: str = DEFAULT_OSRM_URL,
    max_internal_minutes: float = DEFAULT_MAX_INTERNAL_MINUTES,
) -> ClusterResult:
    """Cluster schools by location. Pure function — no DB access.

    ids/lats/lons are parallel lists. Rows with missing or invalid
    coordinates are left out and listed in result.skipped.
    """
    keep_ids, keep_lats, keep_lons, skipped = [], [], [], []
    for school_id, lat, lon in zip(ids, lats, lons):
        clean = _clean_coordinate(lat, lon)
        if clean is None:
            skipped.append(school_id)
        else:
            keep_ids.append(school_id)
            keep_lats.append(clean[0])
            keep_lons.append(clean[1])

    lats_arr = np.array(keep_lats, dtype=float)
    lons_arr = np.array(keep_lons, dtype=float)
    result = ClusterResult(keep_ids, lats_arr, lons_arr, groups=[], skipped=skipped)
    if not keep_ids:
        return result

    if check_drive_time:
        check_osrm_reachable(osrm_url, lats_arr[0], lons_arr[0])

    # 1. DBSCAN. haversine metric expects [lat, lon] in radians and returns
    #    distances in radians, so eps is miles / earth radius.
    coords = np.radians(np.column_stack([lats_arr, lons_arr]))
    labels = DBSCAN(
        eps=radius_miles / EARTH_RADIUS_MILES,
        min_samples=1,
        metric="haversine",
        algorithm="ball_tree",
    ).fit_predict(coords)
    groups = [np.flatnonzero(labels == k) for k in np.unique(labels)]
    result.largest_before_split = max(len(g) for g in groups)

    # 2. Break up chained clusters that are wider than max_span_miles.
    def span_split(g):
        dist = _distance_matrix_miles(lats_arr[g], lons_arr[g])
        if dist.max() <= max_span_miles:
            return None
        return _split_by_max_distance(dist, max_span_miles)

    groups, result.n_split_by_span = _apply_split(groups, span_split)

    # 3. Optional: break up clusters with a long drive between two members.
    if check_drive_time:
        def drive_split(g):
            minutes = osrm_duration_minutes(lats_arr[g], lons_arr[g], osrm_url)
            # A->B and B->A can differ (one-way streets); use the worse one.
            minutes = np.maximum(minutes, minutes.T)
            np.fill_diagonal(minutes, 0.0)
            if minutes.max() <= max_internal_minutes:
                return None
            return _split_by_max_distance(minutes, max_internal_minutes)

        groups, result.n_split_by_drive_time = _apply_split(groups, drive_split)

    # Stable cluster ids: order clusters by their first school (input is
    # sorted by cds_code), so re-running on the same data gives the same ids.
    result.groups = sorted(groups, key=lambda g: g.min())
    return result


def load_school_coordinates() -> tuple[list, list, list]:
    """cds_code, latitude, longitude for every school in the `schools` table."""
    rows = get_school_coordinates()
    return (
        [r["cds_code"] for r in rows],
        [r["latitude"] for r in rows],
        [r["longitude"] for r in rows],
    )


def build_clusters(**kwargs) -> ClusterResult:
    """Load schools from the DB, cluster them, and save both cluster tables."""
    ids, lats, lons = load_school_coordinates()
    result = cluster_schools(ids, lats, lons, **kwargs)
    replace_school_clusters(result.cluster_rows(), result.member_rows())

    reduction = 100 * (1 - result.n_clusters / result.n_schools) if result.n_schools else 0
    print(f"Schools clustered:      {result.n_schools}")
    print(f"Skipped (bad coords):   {len(result.skipped)}")
    print(f"Clusters:               {result.n_clusters}  ({reduction:.1f}% fewer drive-time lookups)")
    print(f"Largest cluster:        {result.largest_cluster} schools")
    print(f"Split by span limit:    {result.n_split_by_span}")
    if kwargs.get("check_drive_time"):
        print(f"Split by drive time:    {result.n_split_by_drive_time}")
    print("Saved to school_clusters / school_cluster_members.")
    return result


def compare_radii(radii=COMPARE_RADII, **kwargs) -> list[dict]:
    """Run clustering at several radii and print a comparison table.

    Nothing is written to the DB. Extra kwargs (max_span_miles, OSRM options)
    are passed through to cluster_schools.
    """
    ids, lats, lons = load_school_coordinates()
    show_drive = kwargs.get("check_drive_time", False)

    rows = []
    for radius in radii:
        r = cluster_schools(ids, lats, lons, radius_miles=radius, **kwargs)
        rows.append({
            "radius_miles": radius,
            "schools": r.n_schools,
            "clusters": r.n_clusters,
            "reduction_pct": 100 * (1 - r.n_clusters / r.n_schools) if r.n_schools else 0.0,
            "largest_cluster": r.largest_cluster,
            "largest_before_split": r.largest_before_split,
            "split_by_span": r.n_split_by_span,
            "split_by_drive_time": r.n_split_by_drive_time,
            "skipped": len(r.skipped),
        })

    max_span = kwargs.get("max_span_miles", DEFAULT_MAX_SPAN_MILES)
    print(f"Skipped (missing/invalid coordinates): {rows[0]['skipped'] if rows else 0}")
    print(f"Span limit: {max_span} mi")
    header = f"{'radius_mi':>9}  {'schools':>7}  {'clusters':>8}  {'reduction':>9}  {'largest':>7}  {'largest_pre_split':>17}  {'split_by_span':>13}"
    if show_drive:
        header += f"  {'split_by_drive':>14}"
    print(header)
    print("-" * len(header))
    for row in rows:
        line = (
            f"{row['radius_miles']:>9}  {row['schools']:>7}  {row['clusters']:>8}  "
            f"{row['reduction_pct']:>8.1f}%  {row['largest_cluster']:>7}  "
            f"{row['largest_before_split']:>17}  {row['split_by_span']:>13}"
        )
        if show_drive:
            line += f"  {row['split_by_drive_time']:>14}"
        print(line)
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collapse nearby schools into school clusters.")
    parser.add_argument("--radius", type=float, default=DEFAULT_RADIUS_MILES,
                        help=f"DBSCAN neighbor radius in miles (default {DEFAULT_RADIUS_MILES})")
    parser.add_argument("--max-span", type=float, default=DEFAULT_MAX_SPAN_MILES,
                        help=f"split clusters wider than this many miles (default {DEFAULT_MAX_SPAN_MILES})")
    parser.add_argument("--compare", action="store_true",
                        help=f"print a comparison at radii {', '.join(map(str, COMPARE_RADII))} instead of saving")
    parser.add_argument("--osrm", action="store_true",
                        help="also split clusters by OSRM drive time (off by default)")
    parser.add_argument("--osrm-url", default=DEFAULT_OSRM_URL,
                        help=f"OSRM server URL (default {DEFAULT_OSRM_URL})")
    parser.add_argument("--max-internal-minutes", type=float, default=DEFAULT_MAX_INTERNAL_MINUTES,
                        help=f"max drive time between schools in a cluster (default {DEFAULT_MAX_INTERNAL_MINUTES:g})")
    args = parser.parse_args()

    options = dict(
        max_span_miles=args.max_span,
        check_drive_time=args.osrm,
        osrm_url=args.osrm_url,
        max_internal_minutes=args.max_internal_minutes,
    )
    try:
        if args.compare:
            compare_radii(**options)
        else:
            build_clusters(radius_miles=args.radius, **options)
    except OSRMError as e:
        sys.exit(f"Error: {e}")
