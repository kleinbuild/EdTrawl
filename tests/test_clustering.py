# [Claude-written] Tests for edtrawl/clustering.py. Run with:  pytest
import numpy as np
import pytest

from edtrawl import clustering
from edtrawl.clustering import cluster_schools, _max_pairwise_miles
from edtrawl.match import haversine_miles

# A point in Sacramento; offsets below move due north from it.
BASE_LAT, BASE_LON = 38.5816, -121.4944
MILES_PER_DEG_LAT = clustering.EARTH_RADIUS_MILES * np.pi / 180  # ~69.09


def north_of_base(miles: float) -> tuple[float, float]:
    return BASE_LAT + miles / MILES_PER_DEG_LAT, BASE_LON


def run(points, **kwargs):
    ids = [f"school_{i}" for i in range(len(points))]
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    return cluster_schools(ids, lats, lons, **kwargs)


def test_schools_100m_apart_cluster_together():
    a = (BASE_LAT, BASE_LON)
    b = north_of_base(0.1 / 1.609344)  # 100 m
    assert haversine_miles(*a, *b) == pytest.approx(0.0621, abs=1e-3)

    result = run([a, b])
    assert result.n_clusters == 1
    assert result.cluster_rows()[0][3] == 2  # n_schools


def test_schools_2_miles_apart_stay_separate():
    result = run([(BASE_LAT, BASE_LON), north_of_base(2.0)])
    assert result.n_clusters == 2
    assert result.largest_cluster == 1


def test_chain_is_split_by_span_limit():
    # 6 schools in a line, 0.3 mi apart: every neighbor is within the 0.4 mi
    # radius, so DBSCAN chains them into one 1.5 mi-long cluster.
    points = [north_of_base(0.3 * i) for i in range(6)]
    result = run(points, radius_miles=0.4, max_span_miles=0.75)

    assert result.largest_before_split == 6
    assert result.n_split_by_span == 1
    assert result.n_clusters > 1
    for g in result.groups:
        assert _max_pairwise_miles(result.lats[g], result.lons[g]) <= 0.75 + 1e-9
    # every school still belongs to exactly one cluster
    assert sorted(i for g in result.groups for i in g) == list(range(6))


def test_missing_and_invalid_coordinates_are_skipped():
    ids = ["ok", "blank", "null_island", "swapped"]
    lats = [BASE_LAT, "", 0.0, BASE_LON]
    lons = [BASE_LON, None, 0.0, BASE_LAT]
    result = cluster_schools(ids, lats, lons)
    assert result.ids == ["ok"]
    assert sorted(result.skipped) == ["blank", "null_island", "swapped"]


def test_drive_time_check_splits_cluster(monkeypatch):
    # Two schools 100 m apart but on opposite sides of a freeway: 10 min drive.
    def fake_osrm(lats, lons, osrm_url):
        n = len(lats)
        return np.where(np.eye(n, dtype=bool), 0.0, 10.0)

    monkeypatch.setattr(clustering, "osrm_duration_minutes", fake_osrm)
    result = run([(BASE_LAT, BASE_LON), north_of_base(0.06)], check_drive_time=True)
    assert result.n_clusters == 2
    assert result.n_split_by_drive_time == 1


def test_unreachable_osrm_fails_loudly():
    # Port 9 (discard) — nothing should be listening there.
    with pytest.raises(clustering.OSRMError, match="Could not reach the OSRM server"):
        run([(BASE_LAT, BASE_LON), north_of_base(0.06)],
            check_drive_time=True, osrm_url="http://127.0.0.1:9")
