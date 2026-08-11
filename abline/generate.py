"""Building guidance lines, and filling a field with the passes they imply.

Two separate jobs live here and it is worth keeping them apart:

* **Authoring** a reference line -- from two clicked points, from a point and a
  heading, from a recorded curve, from a pivot centre, or by asking the
  boundary what the best heading would be.
* **Expanding** that reference into the actual swaths, clipped to the boundary,
  which is what gets previewed and what a producer looks at to sanity-check the
  line before driving it.

All the arithmetic happens in a :class:`~abline.geo.LocalFrame` -- a metric
plane centred on the field -- and results come back as lat/lon.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from shapely import affinity
from shapely.geometry import (
    LineString,
    MultiLineString,
    MultiPolygon,
    Point,
    Polygon,
)
from shapely.ops import unary_union

from .geo import LatLon, LocalFrame, densify, initial_bearing
from .models import (
    FieldRecord,
    GuidanceLine,
    LineExtension,
    LineSource,
    Machine,
    PatternType,
    PropagationDirection,
)

__all__ = [
    "HeadingChoice",
    "SwathSet",
    "make_ab_line",
    "make_a_plus_line",
    "make_curve_line",
    "make_pivot_line",
    "make_headland",
    "optimize_heading",
    "line_from_boundary",
    "expand_swaths",
]

# How far an unbounded AB line is drawn when there is no boundary to clip it to.
_UNBOUNDED_HALF_LENGTH_M = 2_000.0

# Curved geometry is exported as vertices; this bounds the chord error a
# terminal introduces by drawing straight between them.
_CURVE_VERTEX_SPACING_M = 2.0


@dataclass
class HeadingChoice:
    """The result of asking a boundary which way to drive."""

    heading_deg: float
    """True azimuth of the driving direction, degrees clockwise from north."""

    pass_count: int
    segment_count: int
    """Number of separate driven segments. Higher than ``pass_count`` when a
    concave boundary chops passes into pieces, each of which costs a turn."""

    total_length_m: float
    strategy: str
    considered: int
    """How many candidate headings were scored, for transparency."""


@dataclass
class SwathSet:
    """A reference line expanded into every pass that covers the field."""

    reference: list[LatLon]
    swaths: list[list[LatLon]]
    """Each entry is one driven segment, already clipped to the boundary."""

    indices: list[int]
    """Swath number for each segment; 0 is the reference, negative is left."""

    width_m: float
    total_length_m: float
    covered_ha: float

    def to_dict(self) -> dict:
        return {
            "reference": [[p.lat, p.lon] for p in self.reference],
            "swaths": [[[p.lat, p.lon] for p in s] for s in self.swaths],
            "indices": self.indices,
            "width_m": self.width_m,
            "total_length_m": round(self.total_length_m, 1),
            "covered_ha": round(self.covered_ha, 3),
            "swath_count": len(self.swaths),
        }


# --------------------------------------------------------------------------- #
#  Shapely helpers                                                             #
# --------------------------------------------------------------------------- #


def _boundary_polygon(field: FieldRecord, frame: LocalFrame) -> Polygon | None:
    """The field boundary as a projected, validity-repaired polygon."""
    if not field.has_boundary:
        return None
    shell = frame.many_to_xy(field.boundary[0])
    holes = [
        frame.many_to_xy(ring) for ring in field.boundary[1:] if len(ring) >= 3
    ]
    poly = Polygon(shell, holes)
    if not poly.is_valid:
        # A boundary traced by hand or exported by a monitor often has a
        # bowtie or a duplicated vertex. buffer(0) is the standard repair; it
        # can return a MultiPolygon, in which case the largest piece is the
        # field and the rest are slivers.
        poly = poly.buffer(0)
        if isinstance(poly, MultiPolygon):
            poly = max(poly.geoms, key=lambda g: g.area)
    return poly if isinstance(poly, Polygon) and not poly.is_empty else None


def _as_linestrings(geom) -> list[LineString]:
    """Flatten whatever shapely handed back into a list of LineStrings."""
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, LineString):
        return [geom] if len(geom.coords) >= 2 else []
    if isinstance(geom, MultiLineString):
        return [g for g in geom.geoms if len(g.coords) >= 2]
    if hasattr(geom, "geoms"):
        out: list[LineString] = []
        for g in geom.geoms:
            out.extend(_as_linestrings(g))
        return out
    return []


def _infinite_line(
    origin: tuple[float, float], heading_deg: float, half_length: float
) -> LineString:
    """A straight line centred on ``origin``, long enough to cross any field."""
    rad = math.radians(heading_deg)
    dx, dy = math.sin(rad), math.cos(rad)  # compass heading: 0 = +y = north
    x, y = origin
    return LineString(
        [
            (x - dx * half_length, y - dy * half_length),
            (x + dx * half_length, y + dy * half_length),
        ]
    )


def _shift(geom: LineString, heading_deg: float, distance: float) -> LineString:
    """Translate ``geom`` perpendicular to ``heading_deg`` by ``distance``.

    Positive distance moves to the right of the direction of travel, which is
    the same convention as :attr:`Machine.lateral_offset_m`.
    """
    rad = math.radians(heading_deg)
    nx, ny = math.cos(rad), -math.sin(rad)  # right-hand normal of the heading
    return affinity.translate(geom, xoff=nx * distance, yoff=ny * distance)


def _clip(line: LineString, poly: Polygon | None) -> list[LineString]:
    if poly is None:
        return [line]
    return _as_linestrings(line.intersection(poly))


# --------------------------------------------------------------------------- #
#  Authoring                                                                   #
# --------------------------------------------------------------------------- #


def make_ab_line(
    a: LatLon,
    b: LatLon,
    *,
    width_m: float,
    name: str = "AB line",
    field_id: str = "",
    machine_id: str = "",
    source: LineSource = LineSource.MANUAL,
    source_detail: str = "",
    propagation: PropagationDirection = PropagationDirection.BOTH,
    extension: LineExtension = LineExtension.BOTH,
) -> GuidanceLine:
    """The plain two-point AB line."""
    a = LatLon.from_any(a)
    b = LatLon.from_any(b)
    return GuidanceLine(
        field_id=field_id,
        name=name,
        pattern=PatternType.AB,
        points=[a, b],
        heading_deg=initial_bearing(a, b),
        swath_width_m=width_m,
        propagation=propagation,
        extension=extension,
        source=source,
        source_detail=source_detail,
        machine_id=machine_id,
    )


def make_a_plus_line(
    a: LatLon,
    heading_deg: float,
    *,
    width_m: float,
    name: str = "A+ line",
    field_id: str = "",
    machine_id: str = "",
    source: LineSource = LineSource.MANUAL,
    source_detail: str = "",
) -> GuidanceLine:
    """A single point plus a heading.

    Useful when you know the direction you want (a fence line bearing, last
    year's heading) but have no second point to click.
    """
    return GuidanceLine(
        field_id=field_id,
        name=name,
        pattern=PatternType.A_PLUS,
        points=[LatLon.from_any(a)],
        heading_deg=heading_deg % 360.0,
        swath_width_m=width_m,
        source=source,
        source_detail=source_detail,
        machine_id=machine_id,
    )


def make_curve_line(
    points: list[LatLon],
    *,
    width_m: float,
    name: str = "Curve",
    field_id: str = "",
    machine_id: str = "",
    source: LineSource = LineSource.MANUAL,
    source_detail: str = "",
    simplify_tolerance_m: float = 0.15,
) -> GuidanceLine:
    """A recorded or imported polyline.

    Raw GPS traces carry a vertex every fraction of a second, which is far more
    detail than a guidance line needs and more than some terminals will accept.
    Douglas-Peucker at a tolerance well under a machine width removes the noise
    without visibly moving the line.
    """
    pts = [LatLon.from_any(p) for p in points]
    if len(pts) < 2:
        raise ValueError("a curve needs at least two points")
    if simplify_tolerance_m > 0 and len(pts) > 2:
        frame = LocalFrame.around(pts)
        xy = frame.many_to_xy(pts)
        simplified = LineString(xy).simplify(simplify_tolerance_m, preserve_topology=False)
        pts = frame.many_to_latlon(list(simplified.coords))
    return GuidanceLine(
        field_id=field_id,
        name=name,
        pattern=PatternType.CURVE,
        points=pts,
        swath_width_m=width_m,
        source=source,
        source_detail=source_detail,
        machine_id=machine_id,
    )


def make_pivot_line(
    center: LatLon,
    radius_m: float,
    *,
    width_m: float,
    name: str = "Pivot",
    field_id: str = "",
    machine_id: str = "",
    source: LineSource = LineSource.MANUAL,
    source_detail: str = "",
) -> GuidanceLine:
    """Concentric circles about a pivot point."""
    if radius_m <= 0:
        raise ValueError("pivot radius must be positive")
    return GuidanceLine(
        field_id=field_id,
        name=name,
        pattern=PatternType.PIVOT,
        points=[LatLon.from_any(center)],
        radius_m=radius_m,
        swath_width_m=width_m,
        source=source,
        source_detail=source_detail,
        machine_id=machine_id,
    )


def make_headland(
    field: FieldRecord,
    *,
    width_m: float,
    passes: int = 2,
    name: str = "Headland",
    machine_id: str = "",
) -> GuidanceLine:
    """Boundary-parallel rings, one per headland pass.

    Ring *k* sits ``(k + 0.5) * width`` inside the boundary, so the first pass
    runs with its outer edge on the fence rather than its centre.
    """
    if passes < 1:
        raise ValueError("need at least one headland pass")
    if not field.has_boundary:
        raise ValueError("headland passes need a field boundary")

    frame = LocalFrame.around(field.all_points())
    poly = _boundary_polygon(field, frame)
    if poly is None:
        raise ValueError("field boundary could not be interpreted as a polygon")

    rings: list[list[LatLon]] = []
    ring_sizes: list[int] = []
    for k in range(passes):
        inset = poly.buffer(-(k + 0.5) * width_m, join_style=2)
        if inset.is_empty:
            # The field is narrower than this many passes. Stop rather than
            # emitting empty rings the producer would have to notice themselves.
            break
        polys = (
            list(inset.geoms) if isinstance(inset, MultiPolygon) else [inset]
        )
        for piece in polys:
            coords = list(piece.exterior.coords)
            pts = frame.many_to_latlon(coords)
            rings.append(pts)
            ring_sizes.append(len(pts))

    if not rings:
        raise ValueError(
            f"a {width_m:g} m machine will not fit a headland pass inside this "
            "boundary"
        )

    return GuidanceLine(
        field_id=field.id,
        name=name,
        pattern=PatternType.HEADLAND,
        points=[p for ring in rings for p in ring],
        ring_sizes=ring_sizes,
        swath_width_m=width_m,
        propagation=PropagationDirection.NONE,
        extension=LineExtension.NONE,
        source=LineSource.BOUNDARY,
        source_detail=f"{len(rings)} headland ring(s) at {width_m:g} m",
        machine_id=machine_id,
    )


# --------------------------------------------------------------------------- #
#  Heading optimisation                                                        #
# --------------------------------------------------------------------------- #


def optimize_heading(
    field: FieldRecord,
    width_m: float,
    *,
    strategy: str = "min_passes",
    step_deg: float = 0.5,
) -> HeadingChoice:
    """Pick the driving direction for a field.

    ``min_passes``
        Scan every heading and keep the one needing the fewest passes -- fewest
        passes means fewest end-of-row turns, which is where the time goes. Ties
        (and there are usually many, since pass count is an integer) are broken
        by actually clipping the swaths and preferring the heading that produces
        the fewest separate driven segments, then the most total length. A
        concave boundary can slice one pass into three, and each piece costs its
        own turn, so that tie-break is not cosmetic.

    ``longest_edge``
        Align to the longest boundary edge. Less clever, but it is what most
        operators would draw by hand, and on a rectangular field it agrees with
        ``min_passes`` anyway.
    """
    if not field.has_boundary:
        raise ValueError("heading optimisation needs a field boundary")
    if width_m <= 0:
        raise ValueError("swath width must be positive")

    frame = LocalFrame.around(field.all_points())
    poly = _boundary_polygon(field, frame)
    if poly is None:
        raise ValueError("field boundary could not be interpreted as a polygon")

    if strategy == "longest_edge":
        coords = list(poly.exterior.coords)
        best_edge = max(
            zip(coords, coords[1:]),
            key=lambda e: math.hypot(e[1][0] - e[0][0], e[1][1] - e[0][1]),
        )
        (x0, y0), (x1, y1) = best_edge
        grid_heading = math.degrees(math.atan2(x1 - x0, y1 - y0)) % 180.0
        scored = _score_heading(poly, grid_heading, width_m)
        cx, cy = poly.centroid.x, poly.centroid.y
        return HeadingChoice(
            heading_deg=frame.true_azimuth_at(cx, cy, grid_heading),
            pass_count=scored[0],
            segment_count=scored[1],
            total_length_m=scored[2],
            strategy=strategy,
            considered=1,
        )

    if strategy != "min_passes":
        raise ValueError(
            f"unknown strategy {strategy!r}; use 'min_passes' or 'longest_edge'"
        )

    hull = poly.convex_hull
    hull_pts = list(hull.exterior.coords) if hasattr(hull, "exterior") else list(hull.coords)

    # Pass 1 is cheap: pass count needs only a projection of the hull, so scan
    # the whole half-circle and find which headings share the minimum.
    candidates: list[tuple[int, float]] = []
    best_count = None
    heading = 0.0
    considered = 0
    while heading < 180.0:
        count = _pass_count(hull_pts, heading, width_m)
        considered += 1
        if best_count is None or count < best_count:
            best_count = count
            candidates = [(count, heading)]
        elif count == best_count:
            candidates.append((count, heading))
        heading += step_deg

    # Pass 2 is expensive but runs only on the tied headings: clip for real and
    # count the driven segments.
    best: tuple[float, int, int, float] | None = None
    for _, cand in candidates:
        passes, segments, length = _score_heading(poly, cand, width_m)
        key = (segments, -length)
        if best is None or key < (best[2], -best[3]):
            best = (cand, passes, segments, length)

    assert best is not None  # candidates is never empty: the scan always runs
    grid_heading, passes, segments, length = best
    cx, cy = poly.centroid.x, poly.centroid.y
    return HeadingChoice(
        heading_deg=frame.true_azimuth_at(cx, cy, grid_heading),
        pass_count=passes,
        segment_count=segments,
        total_length_m=length,
        strategy=strategy,
        considered=considered,
    )


def _pass_count(
    points: list[tuple[float, float]], heading_deg: float, width_m: float
) -> int:
    """How many swaths of ``width_m`` it takes to span ``points`` crosswise."""
    rad = math.radians(heading_deg)
    nx, ny = math.cos(rad), -math.sin(rad)
    projected = [x * nx + y * ny for x, y in points]
    extent = max(projected) - min(projected)
    return max(1, math.ceil(extent / width_m))


def _score_heading(
    poly: Polygon, heading_deg: float, width_m: float
) -> tuple[int, int, float]:
    """``(pass_count, segment_count, total_length_m)`` for one heading."""
    segments = _swath_linestrings(poly, poly.centroid, heading_deg, width_m)
    count = _pass_count(list(poly.exterior.coords), heading_deg, width_m)
    return (count, len(segments), sum(s.length for s in segments))


def _swath_linestrings(
    poly: Polygon,
    origin: Point | tuple[float, float],
    heading_deg: float,
    width_m: float,
    max_swaths: int = 4000,
) -> list[LineString]:
    """Every swath of a straight pattern, clipped to ``poly``."""
    ox, oy = (origin.x, origin.y) if isinstance(origin, Point) else origin
    minx, miny, maxx, maxy = poly.bounds
    diagonal = math.hypot(maxx - minx, maxy - miny)
    half_length = diagonal + width_m
    base = _infinite_line((ox, oy), heading_deg, half_length)

    # The reference line rarely sits on the field edge, so the sweep has to
    # reach out far enough in both directions to cover the whole polygon.
    reach = math.ceil(diagonal / width_m) + 2
    reach = min(reach, max_swaths // 2)

    out: list[LineString] = []
    for k in range(-reach, reach + 1):
        candidate = _shift(base, heading_deg, k * width_m)
        out.extend(_clip(candidate, poly))
    return out


def line_from_boundary(
    field: FieldRecord,
    machine: Machine,
    *,
    strategy: str = "min_passes",
    name: str = "",
) -> tuple[GuidanceLine, HeadingChoice]:
    """Generate the AB line a field's own shape suggests.

    The line is anchored at the field centroid so it sits inside the field
    rather than off in a corner, which makes it far easier to eyeball.
    """
    choice = optimize_heading(field, machine.effective_width_m, strategy=strategy)
    centroid = field.centroid()
    if centroid is None:
        raise ValueError("field has no boundary to anchor a line to")

    frame = LocalFrame.around(field.all_points())
    cx, cy = frame.to_xy(centroid)
    poly = _boundary_polygon(field, frame)
    span = 0.0
    if poly is not None:
        minx, miny, maxx, maxy = poly.bounds
        span = math.hypot(maxx - minx, maxy - miny) / 2.0
    span = max(span, 100.0)

    # Anchor A and B on the centroid, one span apart, so the pair defines the
    # optimised heading and is long enough that its bearing is well conditioned.
    grid_heading = choice.heading_deg
    rad = math.radians(grid_heading)
    dx, dy = math.sin(rad), math.cos(rad)
    a = frame.to_latlon(cx - dx * span, cy - dy * span)
    b = frame.to_latlon(cx + dx * span, cy + dy * span)

    line = make_ab_line(
        a,
        b,
        width_m=machine.effective_width_m,
        name=name or f"{field.name or 'Field'} AB",
        field_id=field.id,
        machine_id=machine.id,
        source=LineSource.BOUNDARY,
        source_detail=(
            f"{strategy}: {choice.pass_count} passes at "
            f"{machine.effective_width_m:g} m, {choice.segment_count} segments"
        ),
    )
    return line, choice


# --------------------------------------------------------------------------- #
#  Expansion                                                                   #
# --------------------------------------------------------------------------- #


def expand_swaths(
    line: GuidanceLine,
    field: FieldRecord | None = None,
    *,
    machine: Machine | None = None,
    max_swaths: int = 600,
) -> SwathSet:
    """Expand a reference line into the passes it implies.

    With a boundary the passes are clipped to it and the covered area is
    reported. Without one, a fixed-length sample is drawn either side so there
    is still something to look at.

    ``machine.lateral_offset_m`` shifts the whole set sideways: an implement
    that tracks to the right of the tractor needs its lines shifted the same
    way, otherwise every pass inherits the offset as a skip or an overlap.
    """
    problems = line.validate()
    if problems:
        raise ValueError("; ".join(problems))

    anchor_points = list(line.points)
    if field is not None and field.has_boundary:
        anchor_points = anchor_points + field.all_points()
    frame = LocalFrame.around(anchor_points)
    poly = _boundary_polygon(field, frame) if field is not None else None

    offset = machine.lateral_offset_m if machine else 0.0
    width = line.swath_width_m

    if line.pattern in (PatternType.AB, PatternType.A_PLUS):
        segments, indices, reference = _expand_straight(
            line, frame, poly, offset, width, max_swaths
        )
    elif line.pattern is PatternType.CURVE:
        segments, indices, reference = _expand_curve(
            line, frame, poly, offset, width, max_swaths
        )
    elif line.pattern is PatternType.PIVOT:
        segments, indices, reference = _expand_pivot(
            line, frame, poly, offset, width, max_swaths
        )
    elif line.pattern in (PatternType.HEADLAND, PatternType.SPIRAL):
        # These already carry every pass explicitly; there is nothing to repeat.
        rings = line.rings()
        segments = [frame.many_to_xy(r) for r in rings]
        indices = list(range(len(rings)))
        reference = rings[0] if rings else []
        segments = [LineString(s) for s in segments if len(s) >= 2]
    else:
        raise ValueError(f"cannot expand pattern {line.pattern}")

    swaths = [frame.many_to_latlon(list(s.coords)) for s in segments]
    total_length = sum(s.length for s in segments)
    covered = 0.0
    if segments:
        strips = unary_union([s.buffer(width / 2.0, cap_style=2) for s in segments])
        if poly is not None:
            strips = strips.intersection(poly)
        covered = strips.area / 10_000.0

    return SwathSet(
        reference=reference,
        swaths=swaths,
        indices=indices,
        width_m=width,
        total_length_m=total_length,
        covered_ha=covered,
    )


def _expand_straight(line, frame, poly, offset, width, max_swaths):
    if line.pattern is PatternType.AB:
        ax, ay = frame.to_xy(line.points[0])
        bx, by = frame.to_xy(line.points[1])
        grid_heading = math.degrees(math.atan2(bx - ax, by - ay))
    else:
        ax, ay = frame.to_xy(line.points[0])
        grid_heading = line.heading_deg or 0.0

    if poly is not None:
        minx, miny, maxx, maxy = poly.bounds
        half_length = math.hypot(maxx - minx, maxy - miny) + width
        reach = min(math.ceil(half_length / width) + 2, max_swaths // 2)
    else:
        half_length = _UNBOUNDED_HALF_LENGTH_M
        reach = min(20, max_swaths // 2)

    base = _shift(_infinite_line((ax, ay), grid_heading, half_length), grid_heading, offset)
    reference = frame.many_to_latlon(list(base.coords))

    left_limit = reach if line.propagation in (
        PropagationDirection.BOTH, PropagationDirection.LEFT
    ) else 0
    right_limit = reach if line.propagation in (
        PropagationDirection.BOTH, PropagationDirection.RIGHT
    ) else 0
    if line.swaths_left is not None:
        left_limit = min(left_limit, line.swaths_left)
    if line.swaths_right is not None:
        right_limit = min(right_limit, line.swaths_right)

    segments: list[LineString] = []
    indices: list[int] = []
    for k in range(-left_limit, right_limit + 1):
        shifted = _shift(base, grid_heading, k * width)
        for piece in _clip(shifted, poly):
            segments.append(piece)
            indices.append(k)
    return segments, indices, reference


def _expand_curve(line, frame, poly, offset, width, max_swaths):
    xy = frame.many_to_xy(line.points)
    base = LineString(xy)
    if offset:
        base = _offset_curve(base, offset) or base
    reference = frame.many_to_latlon(list(base.coords))

    if poly is not None:
        minx, miny, maxx, maxy = poly.bounds
        reach = min(math.ceil(math.hypot(maxx - minx, maxy - miny) / width) + 2,
                    max_swaths // 2)
    else:
        reach = min(15, max_swaths // 2)

    segments: list[LineString] = []
    indices: list[int] = []
    for k in range(-reach, reach + 1):
        curve = base if k == 0 else _offset_curve(base, k * width)
        if curve is None:
            # Offsetting a curve inward past its radius of curvature collapses
            # it. That is a real geometric limit, not an error -- the passes on
            # that side simply run out.
            continue
        for piece in _clip(curve, poly):
            segments.append(piece)
            indices.append(k)
    return segments, indices, reference


def _offset_curve(line: LineString, distance: float) -> LineString | None:
    """Parallel offset of a polyline, or None if it collapses.

    Shapely returns a MultiLineString when the offset self-intersects (a curve
    offset toward its centre of curvature eats itself). Keeping the longest
    piece is the pragmatic answer: it is the part of the pass that is actually
    drivable.
    """
    try:
        offset = line.offset_curve(-distance, join_style=1)
    except Exception:
        return None
    parts = _as_linestrings(offset)
    if not parts:
        return None
    return max(parts, key=lambda p: p.length)


def _expand_pivot(line, frame, poly, offset, width, max_swaths):
    cx, cy = frame.to_xy(line.points[0])
    radius = float(line.radius_m or 0.0) + offset
    center = Point(cx, cy)

    reference_ring = center.buffer(max(radius, 0.1), quad_segs=256).exterior
    reference = frame.many_to_latlon(list(reference_ring.coords))

    if poly is not None:
        minx, miny, maxx, maxy = poly.bounds
        max_radius = math.hypot(maxx - minx, maxy - miny)
    else:
        max_radius = radius * 2

    segments: list[LineString] = []
    indices: list[int] = []
    k = 0
    while True:
        made_any = False
        for sign in ((0,) if k == 0 else (-1, 1)):
            r = radius + sign * k * width
            if r <= width / 4 or r > max_radius:
                continue
            ring = center.buffer(r, quad_segs=max(64, int(r / 2))).exterior
            ring_line = LineString(ring.coords)
            for piece in _clip(ring_line, poly):
                segments.append(piece)
                indices.append(sign * k)
                made_any = True
        if k and not made_any:
            break
        k += 1
        if k > max_swaths // 2:
            break
    return segments, indices, reference


def curve_vertices_for_export(points: list[LatLon]) -> list[LatLon]:
    """Densify a curve so a terminal drawing straight chords stays on the line."""
    if len(points) < 2:
        return points
    frame = LocalFrame.around(points)
    xy = densify(frame.many_to_xy(points), _CURVE_VERTEX_SPACING_M)
    return frame.many_to_latlon(xy)
