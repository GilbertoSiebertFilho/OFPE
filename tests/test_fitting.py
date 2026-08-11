"""Fitting a guidance line to a track a machine already drove.

The tracks here are synthesised from a known line, so the test can assert that
the fitter recovers the parameters it was given -- heading, spacing, geometry.
Real logs are messier; the noise levels used are deliberately worse than a
working RTK receiver to keep the tests honest.
"""

from __future__ import annotations

import math
import random

import pytest

from ofpe.fitting import (
    TrackPoint,
    detect_passes,
    dominant_heading,
    estimate_swath_width,
    fit_guidance_from_track,
)
from ofpe.geo import LatLon, LocalFrame, geodesic_distance
from ofpe.models import PatternType

ORIGIN = LatLon(-27.845, -54.477)


def synth_track(
    *,
    heading_deg: float = 90.0,
    width_m: float = 12.0,
    passes: int = 8,
    length_m: float = 800.0,
    spacing_m: float = 4.0,
    noise_m: float = 0.05,
    include_turns: bool = True,
    seed: int = 7,
) -> list[TrackPoint]:
    """Build a serpentine track: straight passes joined by headland turns."""
    rng = random.Random(seed)
    frame = LocalFrame(ORIGIN)
    rad = math.radians(heading_deg)
    along = (math.sin(rad), math.cos(rad))
    across = (math.cos(rad), -math.sin(rad))

    points: list[TrackPoint] = []
    for index in range(passes):
        offset = index * width_m
        steps = int(length_m / spacing_m)
        forward = index % 2 == 0
        for step in range(steps + 1):
            distance = step * spacing_m if forward else length_m - step * spacing_m
            x = along[0] * distance + across[0] * offset + rng.gauss(0, noise_m)
            y = along[1] * distance + across[1] * offset + rng.gauss(0, noise_m)
            point = frame.to_latlon(x, y)
            points.append(TrackPoint(lat=point.lat, lon=point.lon, recording=True))

        if include_turns and index < passes - 1:
            # A quarter-circle-ish turn on the headland, logged with the
            # implement lifted. These points must not influence the fit.
            end = length_m if forward else 0.0
            for t in range(8):
                angle = math.pi * t / 8
                x = (
                    along[0] * (end + math.sin(angle) * width_m)
                    + across[0] * (offset + (1 - math.cos(angle)) * width_m / 2)
                )
                y = (
                    along[1] * (end + math.sin(angle) * width_m)
                    + across[1] * (offset + (1 - math.cos(angle)) * width_m / 2)
                )
                point = frame.to_latlon(x, y)
                points.append(TrackPoint(lat=point.lat, lon=point.lon, recording=False))
    return points


def test_dominant_heading_recovers_the_driven_direction():
    import numpy as np

    headings = np.array([90.0] * 100 + [12.0, 200.0, 44.0])  # passes plus turns
    lengths = np.array([50.0] * 100 + [3.0, 3.0, 3.0])
    heading, concentration = dominant_heading(headings, lengths)
    assert heading == pytest.approx(90.0, abs=0.5)
    assert concentration > 0.95


def test_dominant_heading_is_weighted_by_distance_not_point_count():
    """Many short turn samples must not outvote a few long passes."""
    import numpy as np

    headings = np.array([90.0] * 5 + [10.0] * 50)
    lengths = np.array([200.0] * 5 + [0.5] * 50)
    heading, _ = dominant_heading(headings, lengths)
    assert heading == pytest.approx(90.0, abs=1.0)


def test_detect_passes_finds_each_pass_and_ignores_turns():
    track = synth_track(passes=6, length_m=600.0)
    _frame, passes, heading, concentration = detect_passes(track)
    assert len(passes) == 6
    assert heading % 180 == pytest.approx(90.0, abs=0.5)
    assert concentration > 0.9
    for segment in passes:
        assert segment.length_m == pytest.approx(600.0, rel=0.02)


def test_swath_width_is_recovered_from_pass_spacing():
    track = synth_track(width_m=15.0, passes=8)
    _frame, passes, _heading, _c = detect_passes(track)
    width, diagnostics = estimate_swath_width(passes)
    assert width == pytest.approx(15.0, abs=0.15)
    assert diagnostics["gap_count"] == 7


def test_swath_width_survives_skipped_passes():
    """An operator working back and forth leaves gaps of 2x and 3x the width."""
    track = synth_track(width_m=12.0, passes=8)
    _frame, passes, _heading, _c = detect_passes(track)
    # Keep passes 0, 1, 3, 6 -- gaps of 12, 24 and 36 metres.
    thinned = [passes[i] for i in (0, 1, 3, 6)]
    width, _diagnostics = estimate_swath_width(thinned)
    assert width == pytest.approx(12.0, abs=0.2)


def test_fit_recovers_an_ab_line_from_a_serpentine_track():
    track = synth_track(heading_deg=90.0, width_m=12.0, passes=8, length_m=800.0)
    result = fit_guidance_from_track(track, name="Recovered")

    assert result.line.pattern is PatternType.AB
    assert result.confidence == "high"
    assert result.pass_count == 8
    assert result.estimated_width_m == pytest.approx(12.0, abs=0.15)

    heading = result.line.computed_heading() % 180
    assert heading == pytest.approx(90.0, abs=0.3)


def test_fit_recovers_a_rotated_line():
    """Nothing may be special-cased about north-south or east-west."""
    for truth in (0.0, 33.0, 137.0):
        track = synth_track(heading_deg=truth, passes=6, length_m=600.0, seed=3)
        result = fit_guidance_from_track(track)
        assert result.line.computed_heading() % 180 == pytest.approx(truth % 180, abs=0.5)


def test_declared_width_wins_but_a_disagreement_is_flagged():
    track = synth_track(width_m=11.4, passes=8)
    result = fit_guidance_from_track(track, declared_width_m=12.0)
    assert result.line.swath_width_m == 12.0
    assert any("overlap" in warning for warning in result.warnings)


def test_matching_width_produces_no_overlap_warning():
    track = synth_track(width_m=12.0, passes=8)
    result = fit_guidance_from_track(track, declared_width_m=12.0)
    assert not any("overlap" in warning for warning in result.warnings)


def test_a_curved_track_is_fitted_as_a_curve():
    """A field driven on a contour should not be forced into a straight line."""
    frame = LocalFrame(ORIGIN)
    points: list[TrackPoint] = []
    radius = 400.0
    for pass_index in range(4):
        r = radius + pass_index * 15.0
        for step in range(120):
            angle = math.pi * step / 240  # a quarter turn of arc
            point = frame.to_latlon(r * math.sin(angle), r * math.cos(angle))
            points.append(TrackPoint(lat=point.lat, lon=point.lon, recording=True))

    result = fit_guidance_from_track(points)
    assert result.line.pattern is PatternType.CURVE
    assert len(result.line.points) > 2


def test_forcing_ab_on_a_curved_track_still_returns_a_straight_line():
    frame = LocalFrame(ORIGIN)
    points = []
    for pass_index in range(3):
        for step in range(150):
            angle = math.pi * step / 300
            r = 400.0 + pass_index * 15.0
            point = frame.to_latlon(r * math.sin(angle), r * math.cos(angle))
            points.append(TrackPoint(lat=point.lat, lon=point.lon, recording=True))
    result = fit_guidance_from_track(points, force_pattern="AB")
    assert result.line.pattern is PatternType.AB


def test_lifted_implement_points_are_dropped():
    track = synth_track(passes=4, length_m=500.0)
    lifted = [p for p in track if p.recording is False]
    assert lifted, "the synthetic track should contain headland turns"
    _frame, passes, _heading, concentration = detect_passes(track)
    # With turns excluded, essentially all remaining travel is on-heading.
    assert concentration > 0.95
    assert len(passes) == 4


def test_a_single_pass_without_a_machine_is_refused():
    track = synth_track(passes=1, length_m=400.0, include_turns=False)
    with pytest.raises(ValueError, match="cannot determine a swath width"):
        fit_guidance_from_track(track)


def test_a_single_pass_with_a_declared_width_works_but_warns():
    track = synth_track(passes=1, length_m=400.0, include_turns=False)
    result = fit_guidance_from_track(track, declared_width_m=12.0)
    assert result.line.swath_width_m == 12.0
    assert result.confidence == "low"
    assert any("only 1 usable pass" in w for w in result.warnings)


def test_a_track_that_never_moves_is_refused():
    track = [TrackPoint(lat=ORIGIN.lat, lon=ORIGIN.lon) for _ in range(20)]
    with pytest.raises(ValueError, match="never moves"):
        fit_guidance_from_track(track)


def test_too_few_points_is_refused():
    with pytest.raises(ValueError, match="at least two track points"):
        fit_guidance_from_track([TrackPoint(lat=-27.845, lon=-54.477)])


def test_fitted_line_geometry_lands_on_the_driven_passes():
    """The reference line must sit on a pass the machine really drove.

    Every other swath is generated by offsetting the reference at the machine
    width, so a reference sitting between two passes puts the whole grid half a
    swath off the existing tramlines. The synthetic passes are at 0, 12, 24 ...
    metres from the origin, so the fitted line must be a whole number of swaths
    away from the origin -- which one does not matter.
    """
    width = 12.0
    track = synth_track(heading_deg=45.0, width_m=width, passes=6, length_m=700.0, noise_m=0.02)
    result = fit_guidance_from_track(track)

    frame = LocalFrame(ORIGIN)
    a, b = result.line.points
    ax, ay = frame.to_xy(a)
    bx, by = frame.to_xy(b)
    dx, dy = bx - ax, by - ay
    norm = math.hypot(dx, dy)
    perpendicular = abs((-dy * (0 - ax) + dx * (0 - ay)) / norm)

    swaths_away = perpendicular / width
    assert swaths_away == pytest.approx(round(swaths_away), abs=0.02), (
        f"the reference line sits {perpendicular:.2f} m from the origin, which "
        f"is {swaths_away:.2f} swaths -- it is between passes, not on one"
    )
    assert geodesic_distance(a, b) > 300
