"""Domain model: machines, fields, guidance lines.

One canonical representation sits in the middle of this platform. Every reader
turns a vendor file into these objects; every writer turns these objects back
into a vendor file. Nothing in here knows about a specific brand -- that lives
in :mod:`abline.catalog` and :mod:`abline.writers`.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field as dc_field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Sequence

from .geo import LatLon, LocalFrame, geodesic_distance, initial_bearing

__all__ = [
    "PatternType",
    "MachineCategory",
    "PropagationDirection",
    "LineExtension",
    "LineSource",
    "Machine",
    "FieldRecord",
    "GuidanceLine",
    "new_id",
    "utc_now",
]


def new_id() -> str:
    return uuid.uuid4().hex[:16]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class PatternType(str, Enum):
    """Guidance pattern kinds.

    The names and semantics follow ISO 11783-10's guidance pattern type
    enumeration, because that is the one definition every ISOBUS terminal
    already agrees on. Brand-specific vocabulary ("Straight Track", "AB Curve",
    "Adaptive Curve") maps onto these in the catalog.
    """

    AB = "AB"
    """Two points define an infinite straight line, repeated at swath width."""

    A_PLUS = "A_PLUS"
    """One point plus a heading. Same geometry as AB, different authoring."""

    CURVE = "CURVE"
    """A recorded or imported polyline, repeated by parallel offset."""

    PIVOT = "PIVOT"
    """Concentric circles about a centre -- centre pivot irrigation."""

    SPIRAL = "SPIRAL"
    """A continuous spiral about a centre."""

    HEADLAND = "HEADLAND"
    """Boundary-parallel passes around the field edge."""

    @property
    def isoxml_code(self) -> int:
        """ISO 11783-10 GuidancePatternType (GPNC) value.

        ISOXML has no dedicated headland pattern, so headland rings are written
        as curves -- geometrically identical, and every terminal renders them.
        """
        return {
            PatternType.AB: 1,
            PatternType.A_PLUS: 2,
            PatternType.CURVE: 3,
            PatternType.PIVOT: 4,
            PatternType.SPIRAL: 5,
            PatternType.HEADLAND: 3,
        }[self]

    @property
    def needs_two_points(self) -> bool:
        return self in (PatternType.AB,)

    @property
    def is_closed(self) -> bool:
        return self in (PatternType.PIVOT, PatternType.HEADLAND)


class MachineCategory(str, Enum):
    COMBINE = "combine"
    PLANTER = "planter"
    SEEDER = "seeder"
    SPRAYER = "sprayer"
    SPREADER = "spreader"
    TILLAGE = "tillage"
    TRACTOR = "tractor"
    SWATHER = "swather"
    OTHER = "other"


class PropagationDirection(str, Enum):
    """Which side of the reference line the swaths repeat on (ISOXML GPNE)."""

    BOTH = "both"
    LEFT = "left"
    RIGHT = "right"
    NONE = "none"

    @property
    def isoxml_code(self) -> int:
        return {
            PropagationDirection.BOTH: 1,
            PropagationDirection.LEFT: 2,
            PropagationDirection.RIGHT: 3,
            PropagationDirection.NONE: 4,
        }[self]


class LineExtension(str, Enum):
    """Whether the line runs on past its endpoints (ISOXML GPNF)."""

    BOTH = "both"
    FIRST_ONLY = "first_only"
    LAST_ONLY = "last_only"
    NONE = "none"

    @property
    def isoxml_code(self) -> int:
        return {
            LineExtension.BOTH: 1,
            LineExtension.FIRST_ONLY: 2,
            LineExtension.LAST_ONLY: 3,
            LineExtension.NONE: 4,
        }[self]


class LineSource(str, Enum):
    """How a line came to exist. Shown to the producer, because provenance
    changes how much you should trust a line."""

    MANUAL = "manual"
    """Typed or clicked A/B coordinates."""

    BOUNDARY = "boundary"
    """Derived from a field boundary by the heading optimiser."""

    MACHINE_DATA = "machine_data"
    """Fitted to passes a machine actually drove."""

    IMPORTED = "imported"
    """Read out of another brand's file."""


@dataclass
class Machine:
    """A machine and the working width that its guidance lines are spaced by.

    ``working_width_m`` is the number that matters: header width on a combine,
    toolbar width on a planter, boom width on a sprayer. ``overlap_m`` is
    subtracted from it to get the *effective* spacing, which is what actually
    goes into a file -- an operator who runs 30 cm of overlap on a 12 m header
    is really driving an 11.7 m swath, and lines generated at 12 m will leave
    strips.
    """

    id: str = dc_field(default_factory=new_id)
    name: str = ""
    brand: str = ""
    model: str = ""
    category: MachineCategory = MachineCategory.OTHER
    working_width_m: float = 0.0
    overlap_m: float = 0.0
    section_count: int = 1
    lateral_offset_m: float = 0.0
    """Implement centre offset from the GNSS antenna, positive to the right.

    A drawn implement that tracks off to one side needs its lines shifted by the
    same amount, or every pass inherits the offset as a skip or an overlap.
    """

    inline_offset_m: float = 0.0
    """Implement offset fore/aft of the antenna, positive forward. Recorded for
    completeness and for machine-data fitting; it does not move a line."""

    monitor_key: str = ""
    """Key into :mod:`abline.catalog`, e.g. ``john_deere.gen4``."""

    notes: str = ""
    created_at: str = dc_field(default_factory=utc_now)

    def __post_init__(self):
        if isinstance(self.category, str):
            self.category = MachineCategory(self.category)

    @property
    def effective_width_m(self) -> float:
        """Swath spacing after overlap. Never returns a non-positive number."""
        width = self.working_width_m - self.overlap_m
        if width <= 0:
            raise ValueError(
                f"machine {self.name!r}: overlap {self.overlap_m} m is not smaller "
                f"than working width {self.working_width_m} m, so swath spacing "
                f"would be {width} m"
            )
        return width

    @property
    def display_width(self) -> str:
        return f"{self.working_width_m:g} m"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "brand": self.brand,
            "model": self.model,
            "category": self.category.value,
            "working_width_m": self.working_width_m,
            "overlap_m": self.overlap_m,
            "effective_width_m": (
                self.effective_width_m if self.working_width_m > self.overlap_m else None
            ),
            "section_count": self.section_count,
            "lateral_offset_m": self.lateral_offset_m,
            "inline_offset_m": self.inline_offset_m,
            "monitor_key": self.monitor_key,
            "notes": self.notes,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Machine":
        return cls(
            id=d.get("id") or new_id(),
            name=d.get("name", ""),
            brand=d.get("brand", ""),
            model=d.get("model", ""),
            category=MachineCategory(d.get("category", "other")),
            working_width_m=float(d.get("working_width_m") or 0.0),
            overlap_m=float(d.get("overlap_m") or 0.0),
            section_count=int(d.get("section_count") or 1),
            lateral_offset_m=float(d.get("lateral_offset_m") or 0.0),
            inline_offset_m=float(d.get("inline_offset_m") or 0.0),
            monitor_key=d.get("monitor_key", ""),
            notes=d.get("notes", ""),
            created_at=d.get("created_at") or utc_now(),
        )


@dataclass
class FieldRecord:
    """A field, optionally with a boundary.

    ``boundary`` is a list of rings; ring 0 is the outer edge and any further
    rings are holes (a slough, a yard, a tower base). Rings are stored as
    lat/lon and are not required to be closed -- the first vertex is repeated on
    export where a format demands it.
    """

    id: str = dc_field(default_factory=new_id)
    name: str = ""
    farm: str = ""
    grower: str = ""
    boundary: list[list[LatLon]] = dc_field(default_factory=list)
    notes: str = ""
    created_at: str = dc_field(default_factory=utc_now)

    def __post_init__(self):
        self.boundary = [
            [LatLon.from_any(p) for p in ring] for ring in (self.boundary or [])
        ]

    @property
    def has_boundary(self) -> bool:
        return bool(self.boundary and len(self.boundary[0]) >= 3)

    def all_points(self) -> list[LatLon]:
        return [p for ring in self.boundary for p in ring]

    def centroid(self) -> LatLon | None:
        """Area-weighted centroid of the outer ring, or None without a boundary."""
        if not self.has_boundary:
            return None
        frame = LocalFrame.around(self.boundary[0])
        pts = frame.many_to_xy(self.boundary[0])
        area2 = 0.0
        cx = cy = 0.0
        for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
            cross = x0 * y1 - x1 * y0
            area2 += cross
            cx += (x0 + x1) * cross
            cy += (y0 + y1) * cross
        if abs(area2) < 1e-9:
            # Degenerate ring (collinear points): fall back to the vertex mean
            # so callers still get a usable anchor instead of a divide by zero.
            mx = sum(p[0] for p in pts) / len(pts)
            my = sum(p[1] for p in pts) / len(pts)
            return frame.to_latlon(mx, my)
        return frame.to_latlon(cx / (3 * area2), cy / (3 * area2))

    def area_ha(self) -> float:
        """Boundary area in hectares, outer ring minus holes."""
        if not self.has_boundary:
            return 0.0
        frame = LocalFrame.around(self.boundary[0])
        total = 0.0
        for i, ring in enumerate(self.boundary):
            if len(ring) < 3:
                continue
            pts = frame.many_to_xy(ring)
            a2 = sum(
                x0 * y1 - x1 * y0
                for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1])
            )
            ring_area = abs(a2) / 2.0
            total += ring_area if i == 0 else -ring_area
        return max(0.0, total) / 10_000.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "farm": self.farm,
            "grower": self.grower,
            "boundary": [[[p.lat, p.lon] for p in ring] for ring in self.boundary],
            "area_ha": round(self.area_ha(), 4),
            "centroid": (
                [self.centroid().lat, self.centroid().lon] if self.has_boundary else None
            ),
            "notes": self.notes,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "FieldRecord":
        return cls(
            id=d.get("id") or new_id(),
            name=d.get("name", ""),
            farm=d.get("farm", ""),
            grower=d.get("grower", ""),
            boundary=[
                [LatLon.from_any(p) for p in ring] for ring in (d.get("boundary") or [])
            ],
            notes=d.get("notes", ""),
            created_at=d.get("created_at") or utc_now(),
        )


@dataclass
class GuidanceLine:
    """One guidance pattern.

    ``points`` carries the reference geometry and its meaning depends on
    ``pattern``:

    ==================  ====================================================
    ``AB``              exactly two points: A then B
    ``A_PLUS``          one point (A); direction comes from ``heading_deg``
    ``CURVE``           the recorded polyline, two or more points
    ``PIVOT``           one point: the pivot centre, with ``radius_m`` set
    ``SPIRAL``          the full spiral polyline
    ``HEADLAND``        one closed ring per pass, flattened into ``points``
                        with ``ring_sizes`` recording where each ring ends
    ==================  ====================================================
    """

    id: str = dc_field(default_factory=new_id)
    field_id: str = ""
    name: str = ""
    pattern: PatternType = PatternType.AB
    points: list[LatLon] = dc_field(default_factory=list)
    ring_sizes: list[int] = dc_field(default_factory=list)
    heading_deg: float | None = None
    radius_m: float | None = None
    swath_width_m: float = 0.0
    propagation: PropagationDirection = PropagationDirection.BOTH
    extension: LineExtension = LineExtension.BOTH
    swaths_left: int | None = None
    swaths_right: int | None = None
    source: LineSource = LineSource.MANUAL
    source_detail: str = ""
    machine_id: str = ""
    confidence: str = "ok"
    created_at: str = dc_field(default_factory=utc_now)

    def __post_init__(self):
        self.points = [LatLon.from_any(p) for p in (self.points or [])]
        if isinstance(self.pattern, str):
            self.pattern = PatternType(self.pattern)
        if isinstance(self.propagation, str):
            self.propagation = PropagationDirection(self.propagation)
        if isinstance(self.extension, str):
            self.extension = LineExtension(self.extension)
        if isinstance(self.source, str):
            self.source = LineSource(self.source)

    def validate(self) -> list[str]:
        """Return human-readable problems. Empty list means the line is sane.

        Called before export rather than raising at construction time, so a
        half-built line can round-trip through the UI and be fixed there.
        """
        problems: list[str] = []
        n = len(self.points)
        if self.pattern is PatternType.AB and n != 2:
            problems.append(f"an AB line needs exactly 2 points, got {n}")
        if self.pattern is PatternType.AB and n == 2:
            span = geodesic_distance(self.points[0], self.points[1])
            if span < 1.0:
                problems.append(
                    f"A and B are {span:.2f} m apart; the heading they define is "
                    "dominated by GNSS noise. Move B further away."
                )
        if self.pattern is PatternType.A_PLUS:
            if n != 1:
                problems.append(f"an A+ line needs exactly 1 point, got {n}")
            if self.heading_deg is None:
                problems.append("an A+ line needs a heading")
        if self.pattern is PatternType.CURVE and n < 2:
            problems.append(f"a curve needs at least 2 points, got {n}")
        if self.pattern is PatternType.PIVOT:
            if n != 1:
                problems.append(f"a pivot needs exactly 1 centre point, got {n}")
            if not self.radius_m or self.radius_m <= 0:
                problems.append("a pivot needs a positive radius")
        if self.pattern is PatternType.HEADLAND and not self.ring_sizes:
            problems.append("headland passes need ring_sizes to delimit each ring")
        if self.swath_width_m <= 0:
            problems.append(f"swath width must be positive, got {self.swath_width_m}")
        return problems

    def rings(self) -> list[list[LatLon]]:
        """Split ``points`` back into rings using ``ring_sizes``.

        Without ring sizes the whole point list is one ring, which is the right
        answer for every pattern except HEADLAND.
        """
        if not self.ring_sizes:
            return [self.points] if self.points else []
        out: list[list[LatLon]] = []
        i = 0
        for size in self.ring_sizes:
            out.append(self.points[i : i + size])
            i += size
        if i < len(self.points):
            out.append(self.points[i:])
        return [r for r in out if r]

    def computed_heading(self) -> float | None:
        """Heading of the line as a true azimuth, if the pattern has one."""
        if self.heading_deg is not None:
            return self.heading_deg
        if self.pattern in (PatternType.AB,) and len(self.points) >= 2:
            return initial_bearing(self.points[0], self.points[1])
        if self.pattern is PatternType.CURVE and len(self.points) >= 2:
            return initial_bearing(self.points[0], self.points[-1])
        return None

    def length_m(self) -> float:
        if len(self.points) < 2:
            if self.pattern is PatternType.PIVOT and self.radius_m:
                return 2 * math.pi * self.radius_m
            return 0.0
        return sum(
            geodesic_distance(a, b) for a, b in zip(self.points, self.points[1:])
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "field_id": self.field_id,
            "name": self.name,
            "pattern": self.pattern.value,
            "points": [[p.lat, p.lon] for p in self.points],
            "ring_sizes": self.ring_sizes,
            "heading_deg": self.computed_heading(),
            "radius_m": self.radius_m,
            "swath_width_m": self.swath_width_m,
            "propagation": self.propagation.value,
            "extension": self.extension.value,
            "swaths_left": self.swaths_left,
            "swaths_right": self.swaths_right,
            "source": self.source.value,
            "source_detail": self.source_detail,
            "machine_id": self.machine_id,
            "confidence": self.confidence,
            "length_m": round(self.length_m(), 2),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "GuidanceLine":
        return cls(
            id=d.get("id") or new_id(),
            field_id=d.get("field_id", ""),
            name=d.get("name", ""),
            pattern=PatternType(d.get("pattern", "AB")),
            points=[LatLon.from_any(p) for p in (d.get("points") or [])],
            ring_sizes=list(d.get("ring_sizes") or []),
            heading_deg=d.get("heading_deg"),
            radius_m=d.get("radius_m"),
            swath_width_m=float(d.get("swath_width_m") or 0.0),
            propagation=PropagationDirection(d.get("propagation", "both")),
            extension=LineExtension(d.get("extension", "both")),
            swaths_left=d.get("swaths_left"),
            swaths_right=d.get("swaths_right"),
            source=LineSource(d.get("source", "manual")),
            source_detail=d.get("source_detail", ""),
            machine_id=d.get("machine_id", ""),
            confidence=d.get("confidence", "ok"),
            created_at=d.get("created_at") or utc_now(),
        )


def bounding_box(points: Sequence[LatLon]) -> tuple[float, float, float, float]:
    """``(min_lon, min_lat, max_lon, max_lat)`` -- the order shapefiles want."""
    pts = [LatLon.from_any(p) for p in points]
    if not pts:
        return (0.0, 0.0, 0.0, 0.0)
    lats = [p.lat for p in pts]
    lons = [p.lon for p in pts]
    return (min(lons), min(lats), max(lons), max(lats))
