"""Recovering guidance lines from data a machine already logged.

The premise: a producer who has been farming a field for years has already told
you the right AB line -- it is sitting in last season's as-applied or yield log.
This module reads that track back out.

The pipeline is:

1. Project the track into a metric plane and derive a heading per point.
2. Find the **dominant heading** by length-weighted histogram, modulo 180. The
   productive passes are long and parallel; headland turns are short and point
   everywhere, so weighting by distance rather than by point count keeps the
   turns from voting.
3. Split the track into **passes** -- runs of consecutive points travelling
   within a tolerance of that heading.
4. Measure each pass's perpendicular offset from a common reference, and infer
   the **swath width** from the spacing between them.
5. Fit a line to the passes and return it as an AB line -- or, if the track was
   never straight in the first place, return the longest pass as a curve.

Everything is reported with a confidence and a diagnostics dictionary, because
a fitted line is an inference and the operator deserves to see the working.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field as dc_field
from typing import Sequence

import numpy as np

from .geo import LatLon, LocalFrame, circular_mean_180, normalize_heading_180
from .generate import make_ab_line, make_curve_line
from .models import GuidanceLine, LineSource

__all__ = [
    "TrackPoint",
    "PassSegment",
    "FitResult",
    "detect_passes",
    "dominant_heading",
    "estimate_swath_width",
    "fit_guidance_from_track",
]

# Below this, a "pass" is a wobble in a headland turn rather than a run.
_MIN_PASS_LENGTH_M = 20.0

# How far off the dominant heading a point may travel and still count as
# being on a pass. Generous enough for hand steering, tight enough to exclude
# the turn itself.
_HEADING_TOLERANCE_DEG = 12.0

# Two passes closer together than this are treated as one pass sampled twice
# (an overlap, a re-drive), not as evidence of a very narrow machine.
_MIN_DISTINCT_SPACING_M = 0.75

# A single step this much longer than the typical one is a discontinuity in the
# log -- the machine was on the road, the logger was off, or the file stitches
# two runs together. Crucially it is NOT a pass, however conveniently its
# heading may line up: a straight hop from the end of one pass to the start of
# the next can be hundreds of metres long and point exactly along the dominant
# heading, and without this it would be mistaken for the longest pass in the job.
_GAP_MULTIPLE = 8.0
_MIN_GAP_M = 20.0


@dataclass
class TrackPoint:
    """One logged position.

    ``recording`` mirrors the section/master-switch state that most monitors
    log. When it is present, points logged with the implement lifted are
    dropped, which removes road travel and most headland turns for free.
    """

    lat: float
    lon: float
    timestamp: str | None = None
    heading_deg: float | None = None
    speed_ms: float | None = None
    recording: bool | None = None

    def as_latlon(self) -> LatLon:
        return LatLon(self.lat, self.lon)


@dataclass
class PassSegment:
    """A run of travel in a consistent direction."""

    indices: tuple[int, int]
    """Half-open ``[start, end)`` index range into the projected track."""

    points_xy: list[tuple[float, float]]
    length_m: float
    heading_deg: float
    """Undirected, in ``[0, 180)``."""

    offset_m: float
    """Signed perpendicular distance from the reference axis."""

    @property
    def point_count(self) -> int:
        return len(self.points_xy)


@dataclass
class FitResult:
    """What the fitter concluded, and how sure it is."""

    line: GuidanceLine
    estimated_width_m: float | None
    pass_count: int
    confidence: str
    """``high``, ``medium`` or ``low``."""

    warnings: list[str] = dc_field(default_factory=list)
    diagnostics: dict = dc_field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "line": self.line.to_dict(),
            "estimated_width_m": self.estimated_width_m,
            "pass_count": self.pass_count,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "diagnostics": self.diagnostics,
        }


def _project(points: Sequence[TrackPoint]) -> tuple[LocalFrame, np.ndarray]:
    frame = LocalFrame.around([p.as_latlon() for p in points])
    xy = np.asarray(frame.many_to_xy([p.as_latlon() for p in points]), dtype=float)
    return frame, xy


def _segment_headings(xy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per-segment heading (degrees, ``[0, 180)``) and length."""
    deltas = np.diff(xy, axis=0)
    lengths = np.hypot(deltas[:, 0], deltas[:, 1])
    # atan2(east, north) gives a compass bearing rather than a maths angle.
    headings = np.degrees(np.arctan2(deltas[:, 0], deltas[:, 1])) % 180.0
    return headings, lengths


def dominant_heading(
    headings_deg: np.ndarray, lengths_m: np.ndarray, *, bin_deg: float = 1.0
) -> tuple[float, float]:
    """Length-weighted modal heading, and how concentrated the track is.

    Returns ``(heading, concentration)`` where concentration runs 0 to 1. A
    field driven in straight parallel passes scores near 1; a contour-farmed
    field or a pivot scores low, which is the signal to fit a curve instead of
    an AB line.
    """
    if len(headings_deg) == 0:
        raise ValueError("no track segments to analyse")

    bins = int(round(180.0 / bin_deg))
    hist = np.zeros(bins)
    idx = np.floor(headings_deg / bin_deg).astype(int) % bins
    np.add.at(hist, idx, lengths_m)

    # Smooth circularly before taking the peak: a pass at 44.9 deg and one at
    # 45.1 deg belong to the same direction and should reinforce rather than
    # split across two bins.
    kernel = np.array([0.25, 0.5, 1.0, 0.5, 0.25])
    smoothed = np.convolve(np.r_[hist[-2:], hist, hist[:2]], kernel, mode="same")[
        2 : 2 + bins
    ]
    peak = int(np.argmax(smoothed))

    # Refine with a proper circular mean over the segments near the peak,
    # so the answer is not quantised to the bin width.
    peak_heading = (peak + 0.5) * bin_deg
    near = np.abs(((headings_deg - peak_heading + 90) % 180) - 90) <= 10.0
    if near.any():
        weights = lengths_m[near]
        picked = headings_deg[near]
        # Weight by repeating in proportion to length, capped so one very long
        # segment cannot swamp the estimate entirely.
        reps = np.maximum(1, np.round(weights / max(weights.mean(), 1e-9))).astype(int)
        reps = np.minimum(reps, 50)
        expanded = np.repeat(picked, reps)
        refined = circular_mean_180(expanded.tolist())
    else:
        refined = peak_heading

    total = lengths_m.sum()
    concentration = float(hist[max(0, peak - 5) : peak + 6].sum() / total) if total else 0.0
    # Wrap-around contribution for a peak sitting near 0 or 180.
    if peak < 5 or peak > bins - 6:
        window = np.r_[hist[-5:], hist[:6]] if peak < 5 else np.r_[hist[-6:], hist[:5]]
        concentration = float(window.sum() / total) if total else 0.0

    return normalize_heading_180(refined), min(1.0, concentration)


def detect_passes(
    points: Sequence[TrackPoint],
    *,
    heading_deg: float | None = None,
    tolerance_deg: float = _HEADING_TOLERANCE_DEG,
    min_length_m: float = _MIN_PASS_LENGTH_M,
    drop_non_recording: bool = True,
) -> tuple[LocalFrame, list[PassSegment], float, float]:
    """Split a track into productive passes.

    Returns ``(frame, passes, heading, concentration)``.
    """
    pts = list(points)
    if drop_non_recording and any(p.recording is not None for p in pts):
        kept = [p for p in pts if p.recording is not False]
        if len(kept) >= 2:
            pts = kept
    if len(pts) < 2:
        raise ValueError("need at least two track points")

    frame, xy = _project(pts)
    headings, lengths = _segment_headings(xy)

    # Zero-length segments (a machine parked with the logger running) carry no
    # direction; keeping them would inject arbitrary headings into the vote.
    moving = lengths > 1e-6
    if not moving.any():
        raise ValueError("the track never moves")

    typical = float(np.median(lengths[moving]))
    gap_threshold = max(_MIN_GAP_M, _GAP_MULTIPLE * typical)
    continuous = moving & (lengths <= gap_threshold)
    if not continuous.any():
        # Every step is a jump: the file is a list of waypoints, not a track.
        raise ValueError(
            "this file has no continuous travel in it -- every point is far "
            "from the last. It looks like a list of waypoints rather than a "
            "logged track."
        )

    if heading_deg is None:
        heading, concentration = dominant_heading(
            headings[continuous], lengths[continuous]
        )
    else:
        heading = normalize_heading_180(heading_deg)
        deviation = np.abs(((headings[continuous] - heading + 90) % 180) - 90)
        concentration = float(
            lengths[continuous][deviation <= 5.0].sum() / lengths[continuous].sum()
        )

    deviation = np.abs(((headings - heading + 90) % 180) - 90)
    on_line = continuous & (deviation <= tolerance_deg)

    # Reference axis through the centroid, used to give every pass a
    # comparable perpendicular offset.
    centroid = xy.mean(axis=0)
    rad = math.radians(heading)
    normal = np.array([math.cos(rad), -math.sin(rad)])

    passes: list[PassSegment] = []
    start: int | None = None
    for i, flag in enumerate(on_line):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            seg = _build_pass(xy, start, i + 1, lengths, centroid, normal, heading)
            if seg and seg.length_m >= min_length_m:
                passes.append(seg)
            start = None
    if start is not None:
        seg = _build_pass(xy, start, len(xy), lengths, centroid, normal, heading)
        if seg and seg.length_m >= min_length_m:
            passes.append(seg)

    return frame, passes, heading, concentration


def _build_pass(
    xy: np.ndarray,
    start: int,
    end: int,
    lengths: np.ndarray,
    centroid: np.ndarray,
    normal: np.ndarray,
    heading: float,
) -> PassSegment | None:
    end = min(end, len(xy))
    if end - start < 2:
        return None
    chunk = xy[start:end]
    length = float(lengths[start : end - 1].sum())
    offsets = (chunk - centroid) @ normal
    return PassSegment(
        indices=(start, end),
        points_xy=[(float(x), float(y)) for x, y in chunk],
        length_m=length,
        heading_deg=heading,
        offset_m=float(np.median(offsets)),
    )


def estimate_swath_width(passes: Sequence[PassSegment]) -> tuple[float | None, dict]:
    """Infer machine width from how far apart the passes are.

    The gaps cannot simply be averaged. An operator who works back and forth,
    or who skips around a wet spot, leaves gaps that are whole multiples of the
    real width -- 12 m, 24 m, 36 m -- and the mean of those is 24.

    So this is really a one-dimensional greatest-common-divisor problem, solved
    by search rather than by arithmetic: every gap divided by every small
    integer is a candidate width, and the winner is the candidate that explains
    the most gaps as near-integer multiples of itself. Ties go to the largest
    candidate, because 12 and 6 both explain gaps of 12 and 24, and 12 is the
    one the machine actually is.
    """
    if len(passes) < 2:
        return None, {"reason": "fewer than two passes"}

    offsets = sorted(p.offset_m for p in passes)
    gaps = [
        b - a for a, b in zip(offsets, offsets[1:]) if b - a >= _MIN_DISTINCT_SPACING_M
    ]
    if not gaps:
        return None, {"reason": "all passes overlap; no distinct spacing"}

    tolerance = 0.12  # a gap must land within 12% of a whole multiple
    candidates = {
        gap / divisor
        for gap in gaps
        for divisor in (1, 2, 3, 4)
        if gap / divisor >= _MIN_DISTINCT_SPACING_M
    }

    best: tuple[int, float] | None = None
    best_unit_gaps: list[float] = []
    for candidate in sorted(candidates, reverse=True):
        unit_gaps: list[float] = []
        for gap in gaps:
            multiple = max(1, round(gap / candidate))
            if abs(gap / candidate - multiple) <= tolerance:
                unit_gaps.append(gap / multiple)
        score = (len(unit_gaps), candidate)
        if best is None or score > best:
            best = score
            best_unit_gaps = unit_gaps

    if best is None or not best_unit_gaps:
        seed = float(np.median(gaps))
        return seed, {"seed_m": round(seed, 3), "note": "irregular spacing"}

    width = float(np.median(best_unit_gaps))
    return width, {
        "candidate_m": round(best[1], 3),
        "gap_count": len(gaps),
        "unit_gap_count": len(best_unit_gaps),
        "spread_m": round(float(np.std(best_unit_gaps)), 3),
    }


def _fit_axis(points_xy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Total-least-squares line fit: returns ``(centroid, unit_direction)``.

    Ordinary least squares minimises vertical error and blows up on a
    north-south pass; the principal eigenvector of the covariance minimises
    perpendicular error, which is the right thing for a line in a plane and has
    no preferred axis.
    """
    centroid = points_xy.mean(axis=0)
    centred = points_xy - centroid
    _, _, vt = np.linalg.svd(centred, full_matrices=False)
    direction = vt[0]
    return centroid, direction / np.linalg.norm(direction)


def fit_guidance_from_track(
    points: Sequence[TrackPoint],
    *,
    name: str = "Fitted line",
    field_id: str = "",
    machine_id: str = "",
    declared_width_m: float | None = None,
    force_pattern: str | None = None,
    source_detail: str = "",
) -> FitResult:
    """Fit a guidance line to a recorded track.

    ``declared_width_m`` -- the width of the machine that made the track, if you
    know it -- is used for the output line, while the *measured* spacing is
    still reported. A disagreement between the two is worth surfacing: it
    usually means the operator was running deliberate overlap.
    """
    frame, passes, heading, concentration = detect_passes(points)
    warnings: list[str] = []

    curvy = concentration < 0.55
    want_curve = force_pattern == "CURVE" or (curvy and force_pattern != "AB")

    if not passes:
        raise ValueError(
            "no passes long enough to fit. The track may be all headland "
            "turning, or the machine never travelled a consistent heading."
        )

    measured_width, width_diag = estimate_swath_width(passes)
    width = declared_width_m or measured_width
    if width is None:
        raise ValueError(
            "cannot determine a swath width: only one pass was found and no "
            "machine width was supplied. Pick the machine and try again."
        )
    # A quarter of a metre of unexplained overlap on every pass is 2% of the
    # crop on a 12 m machine, so the threshold is deliberately tight in absolute
    # terms and only loosens on very wide machines.
    disagreement = (
        abs(declared_width_m - measured_width)
        if declared_width_m and measured_width
        else 0.0
    )
    if declared_width_m and measured_width and disagreement > max(
        0.25, 0.02 * declared_width_m
    ):
        warnings.append(
            f"the machine is set up as {declared_width_m:g} m but the passes "
            f"are {measured_width:.2f} m apart -- roughly "
            f"{declared_width_m - measured_width:+.2f} m of overlap per pass. "
            "The line uses the machine width; change it if the measured "
            "spacing is what you actually want."
        )

    longest = max(passes, key=lambda p: p.length_m)

    if want_curve:
        curve_pts = frame.many_to_latlon(longest.points_xy)
        line = make_curve_line(
            curve_pts,
            width_m=width,
            name=name,
            field_id=field_id,
            machine_id=machine_id,
            source=LineSource.MACHINE_DATA,
            source_detail=source_detail
            or f"fitted to the longest of {len(passes)} recorded passes",
        )
        confidence = "medium" if longest.length_m > 100 else "low"
        if concentration >= 0.55 and force_pattern == "CURVE":
            warnings.append(
                "this track is actually quite straight; an AB line would "
                "probably serve better than a curve."
            )
    else:
        # Direction comes from every pass at once, after sliding each onto a
        # common offset: averaging across the whole job cancels the GNSS drift
        # that would tilt a fit to any single pass.
        rad = math.radians(heading)
        normal = np.array([math.cos(rad), -math.sin(rad)])
        merged = np.vstack(
            [np.asarray(seg.points_xy) - normal * seg.offset_m for seg in passes]
        )
        _merged_centroid, direction = _fit_axis(merged)

        # Position, though, comes from one real pass -- the longest. The
        # reference line is what every other swath is measured from, so it has
        # to sit on ground the machine actually covered. Anchoring it on the
        # average of all passes would put it up to half a swath away from any of
        # them, and every generated pass would inherit that error.
        anchor = np.asarray(longest.points_xy).mean(axis=0)

        half = max(longest.length_m / 2.0, 50.0)
        a_xy = anchor - direction * half
        b_xy = anchor + direction * half
        a = frame.to_latlon(float(a_xy[0]), float(a_xy[1]))
        b = frame.to_latlon(float(b_xy[0]), float(b_xy[1]))
        line = make_ab_line(
            a,
            b,
            width_m=width,
            name=name,
            field_id=field_id,
            machine_id=machine_id,
            source=LineSource.MACHINE_DATA,
            source_detail=source_detail
            or f"fitted to {len(passes)} recorded passes, "
            f"{concentration:.0%} of travel on heading",
        )
        if len(passes) >= 4 and concentration >= 0.8:
            confidence = "high"
        elif len(passes) >= 2 and concentration >= 0.65:
            confidence = "medium"
        else:
            confidence = "low"

    if len(passes) < 3:
        warnings.append(
            f"only {len(passes)} usable pass(es) were found, so the fitted "
            "heading rests on very little evidence."
        )
    if concentration < 0.4:
        warnings.append(
            f"only {concentration:.0%} of the travel shares a heading. This "
            "track may be contour-farmed, a pivot, or several fields at once."
        )

    line.confidence = confidence
    return FitResult(
        line=line,
        estimated_width_m=round(measured_width, 3) if measured_width else None,
        pass_count=len(passes),
        confidence=confidence,
        warnings=warnings,
        diagnostics={
            "dominant_heading_deg": round(heading, 3),
            "heading_concentration": round(concentration, 3),
            "pass_lengths_m": [round(p.length_m, 1) for p in passes[:50]],
            "longest_pass_m": round(longest.length_m, 1),
            "width_estimate": width_diag,
            "pattern": line.pattern.value,
        },
    )
