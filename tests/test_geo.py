"""Geodesy: the layer everything else trusts silently."""

from __future__ import annotations

import math

import pytest

from abline.geo import (
    LatLon,
    LocalFrame,
    circular_mean_180,
    densify,
    destination,
    geodesic_distance,
    initial_bearing,
    normalize_heading_180,
)


def test_projection_round_trips_to_millimetre():
    frame = LocalFrame(LatLon(-27.845, -54.477))
    for lat, lon in [(-27.845, -54.477), (-27.84, -54.485), (-27.85, -54.46)]:
        x, y = frame.to_xy(LatLon(lat, lon))
        back = frame.to_latlon(x, y)
        # A degree of latitude is ~111 km, so 1e-8 degrees is well under a
        # millimetre -- far tighter than any GNSS receiver in a cab.
        assert back.lat == pytest.approx(lat, abs=1e-8)
        assert back.lon == pytest.approx(lon, abs=1e-8)


def test_projection_preserves_distance_over_a_field():
    """Scale error at field range must be negligible against GNSS noise."""
    a = LatLon(-27.8400, -54.4850)
    b = LatLon(-27.8490, -54.4700)
    frame = LocalFrame.around([a, b])
    ax, ay = frame.to_xy(a)
    bx, by = frame.to_xy(b)
    planar = math.hypot(bx - ax, by - ay)
    geodesic = geodesic_distance(a, b)
    # Well under a centimetre over ~1.8 km.
    assert planar == pytest.approx(geodesic, abs=0.01)


def test_frame_around_averages_longitude_across_the_antimeridian():
    """A field at +179.9 and -179.9 must not centre on longitude zero."""
    frame = LocalFrame.around([LatLon(0.0, 179.9), LatLon(0.0, -179.9)])
    assert abs(frame.origin.lon) > 179.0


def test_bearing_and_distance_are_inverse_of_destination():
    start = LatLon(-27.845, -54.477)
    for bearing in (0.0, 45.0, 137.5, 270.0, 359.9):
        end = destination(start, bearing, 1500.0)
        assert initial_bearing(start, end) == pytest.approx(bearing, abs=0.02)
        # destination() is spherical and geodesic_distance() is ellipsoidal, so
        # they differ by the flattening -- about 0.3% at worst.
        assert geodesic_distance(start, end) == pytest.approx(1500.0, rel=0.005)


def test_geodesic_distance_matches_a_known_value():
    """Lisbon to New York is about 5435 km on the WGS84 ellipsoid."""
    lisbon = LatLon(38.7223, -9.1393)
    new_york = LatLon(40.7128, -74.0060)
    assert geodesic_distance(lisbon, new_york) == pytest.approx(5_435_000, rel=0.002)


def test_geodesic_distance_beats_a_sphere_over_long_distances():
    """The ellipsoidal answer must differ measurably from the spherical one."""
    from abline.geo import _haversine

    lisbon = LatLon(38.7223, -9.1393)
    new_york = LatLon(40.7128, -74.0060)
    exact = geodesic_distance(lisbon, new_york)
    spherical = _haversine(lisbon, new_york)
    # Flattening costs a sphere roughly 0.1-0.3% at this range.
    assert 1_000 < abs(exact - spherical) < 40_000


def test_geodesic_distance_of_coincident_points_is_zero():
    point = LatLon(-27.845, -54.477)
    assert geodesic_distance(point, point) == 0.0


def test_circular_mean_handles_the_wrap_at_180():
    # The naive arithmetic mean of these is 90 degrees, which is a right angle
    # away from the truth.
    assert circular_mean_180([179.0, 1.0]) == pytest.approx(0.0, abs=0.5)
    assert circular_mean_180([44.0, 46.0]) == pytest.approx(45.0, abs=0.01)


def test_normalize_heading_folds_reciprocals_together():
    assert normalize_heading_180(200.0) == pytest.approx(20.0)
    assert normalize_heading_180(-10.0) == pytest.approx(170.0)


def test_true_azimuth_corrects_for_grid_convergence():
    """Away from the central meridian, grid north is not true north."""
    frame = LocalFrame(LatLon(45.0, 0.0))
    x, y = frame.to_xy(LatLon(45.0, 0.06))  # about 4.7 km east
    corrected = frame.true_azimuth_at(x, y, 0.0)
    # Convergence is roughly dlon * sin(lat) = 0.06 * 0.707 = 0.042 degrees.
    assert corrected == pytest.approx(0.042, abs=0.01)
    assert corrected != 0.0


def test_densify_bounds_segment_length():
    points = [(0.0, 0.0), (100.0, 0.0)]
    result = densify(points, 10.0)
    assert len(result) == 11
    for (x0, y0), (x1, y1) in zip(result, result[1:]):
        assert math.hypot(x1 - x0, y1 - y0) <= 10.0 + 1e-9


def test_densify_rejects_a_non_positive_spacing():
    with pytest.raises(ValueError, match="must be positive"):
        densify([(0.0, 0.0), (1.0, 1.0)], 0.0)
