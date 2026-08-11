"""Line authoring, heading optimisation and swath expansion."""

from __future__ import annotations

import math

import pytest

from ofpe.generate import (
    expand_swaths,
    line_from_boundary,
    make_ab_line,
    make_headland,
    make_pivot_line,
    optimize_heading,
)
from ofpe.geo import LatLon, geodesic_distance
from ofpe.models import FieldRecord, Machine, PatternType


def test_field_area_matches_hand_calculation(rectangle_field):
    # 0.015 deg of longitude at -27.845 lat is ~1.475 km; 0.009 deg of latitude
    # is ~0.996 km. That is close to 147 ha.
    assert rectangle_field.area_ha() == pytest.approx(147, rel=0.02)


def test_centroid_sits_inside_the_boundary(rectangle_field):
    centroid = rectangle_field.centroid()
    assert -27.849 < centroid.lat < -27.840
    assert -54.485 < centroid.lon < -54.470


def test_ab_line_heading_is_the_bearing_from_a_to_b():
    a = LatLon(-27.845, -54.480)
    b = LatLon(-27.840, -54.480)  # due north
    line = make_ab_line(a, b, width_m=12.0)
    assert line.pattern is PatternType.AB
    assert line.computed_heading() == pytest.approx(0.0, abs=0.01)


def test_optimizer_drives_the_long_way_on_a_rectangle(rectangle_field):
    """A 1.48 km x 1.00 km field should be driven east-west, not north-south.

    Driving the long axis means fewer passes, which means fewer turns.
    """
    choice = optimize_heading(rectangle_field, 12.0)
    # East-west is 90 degrees; modulo 180 the reciprocal 270 is the same line.
    assert choice.heading_deg % 180 == pytest.approx(90.0, abs=2.0)
    # 996 m of north-south extent at 12 m per pass is about 83 passes.
    assert 80 <= choice.pass_count <= 86


def test_optimizer_beats_the_perpendicular_alternative(rectangle_field):
    best = optimize_heading(rectangle_field, 12.0)
    # The long-edge strategy on this rectangle should agree with min_passes.
    edge = optimize_heading(rectangle_field, 12.0, strategy="longest_edge")
    assert edge.pass_count >= best.pass_count


def test_optimizer_rejects_a_field_without_a_boundary():
    field = FieldRecord(name="No boundary")
    with pytest.raises(ValueError, match="needs a field boundary"):
        optimize_heading(field, 12.0)


def test_optimizer_rejects_an_unknown_strategy(rectangle_field):
    with pytest.raises(ValueError, match="unknown strategy"):
        optimize_heading(rectangle_field, 12.0, strategy="vibes")


def test_line_from_boundary_produces_a_usable_ab_line(rectangle_field, combine):
    line, choice = line_from_boundary(rectangle_field, combine)
    assert line.validate() == []
    assert line.swath_width_m == combine.effective_width_m
    assert line.source.value == "boundary"
    assert choice.pass_count > 1
    # A and B must be far enough apart that the heading is well conditioned.
    assert geodesic_distance(line.points[0], line.points[1]) > 100


def test_swaths_cover_the_field_and_stay_inside_it(rectangle_field, combine):
    line, _ = line_from_boundary(rectangle_field, combine)
    swaths = expand_swaths(line, rectangle_field, machine=combine)
    assert len(swaths.swaths) >= 80
    # Coverage should account for essentially the whole field; the shortfall is
    # the half-swath margin at each edge.
    assert swaths.covered_ha == pytest.approx(rectangle_field.area_ha(), rel=0.05)
    # Every vertex must sit within the boundary's bounding box.
    lats = [p.lat for path in swaths.swaths for p in path]
    lons = [p.lon for path in swaths.swaths for p in path]
    assert min(lats) >= -27.8491 and max(lats) <= -27.8399
    assert min(lons) >= -54.4851 and max(lons) <= -54.4699


def test_narrower_machine_needs_more_passes(rectangle_field):
    wide = optimize_heading(rectangle_field, 36.0)
    narrow = optimize_heading(rectangle_field, 9.0)
    assert narrow.pass_count > wide.pass_count
    assert narrow.pass_count == pytest.approx(wide.pass_count * 4, rel=0.15)


def test_lateral_offset_shifts_every_pass(rectangle_field, combine):
    line, _ = line_from_boundary(rectangle_field, combine)
    centred = expand_swaths(line, rectangle_field, machine=combine)

    offset_machine = Machine(
        name="Offset", working_width_m=12.0, lateral_offset_m=3.0
    )
    shifted = expand_swaths(line, rectangle_field, machine=offset_machine)

    a = centred.reference[0]
    b = shifted.reference[0]
    assert geodesic_distance(a, b) == pytest.approx(3.0, abs=0.2)


def test_headland_rings_sit_inside_the_boundary(rectangle_field):
    headland = make_headland(rectangle_field, width_m=12.0, passes=3)
    assert headland.pattern is PatternType.HEADLAND
    assert len(headland.ring_sizes) == 3
    rings = headland.rings()
    assert len(rings) == 3
    # Each successive ring is shorter than the last, because it is further in.
    lengths = [
        sum(geodesic_distance(a, b) for a, b in zip(ring, ring[1:]))
        for ring in rings
    ]
    assert lengths[0] > lengths[1] > lengths[2]


def test_headland_refuses_when_the_machine_does_not_fit():
    tiny = FieldRecord(
        name="Tiny",
        boundary=[[
            LatLon(-27.8400, -54.4850),
            LatLon(-27.8400, -54.4849),
            LatLon(-27.8401, -54.4849),
            LatLon(-27.8401, -54.4850),
        ]],
    )
    with pytest.raises(ValueError, match="will not fit"):
        make_headland(tiny, width_m=60.0, passes=2)


def test_pivot_expands_into_concentric_rings():
    centre = LatLon(-27.845, -54.477)
    line = make_pivot_line(centre, 200.0, width_m=20.0)
    field = FieldRecord(name="Pivot field")
    swaths = expand_swaths(line, field)
    assert len(swaths.swaths) > 3
    # Every vertex on the reference ring is one radius from the centre.
    for point in swaths.reference[::16]:
        assert geodesic_distance(centre, point) == pytest.approx(200.0, abs=1.0)


def test_expand_rejects_an_invalid_line():
    bad = make_ab_line(
        LatLon(-27.845, -54.477), LatLon(-27.845, -54.477), width_m=12.0
    )
    with pytest.raises(ValueError, match="dominated by GNSS noise"):
        expand_swaths(bad, None)


def test_machine_rejects_overlap_wider_than_the_machine():
    machine = Machine(name="Bad", working_width_m=6.0, overlap_m=6.0)
    with pytest.raises(ValueError, match="not smaller than working width"):
        _ = machine.effective_width_m


def test_effective_width_subtracts_overlap():
    machine = Machine(name="Combine", working_width_m=12.2, overlap_m=0.2)
    assert machine.effective_width_m == pytest.approx(12.0)
