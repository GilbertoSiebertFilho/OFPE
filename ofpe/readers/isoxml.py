"""Read guidance and boundaries back out of an ISOXML TASKDATA set.

This is the other half of :mod:`ofpe.writers.isoxml`, and it is what makes the
cross-brand translator work: an ISOBUS terminal exports its lines as ISOXML, we
read them here, and every other exporter can then write them out again.

Element and attribute codes are as verified in the writer; see that module for
the provenance note.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from ..geo import LatLon
from ..models import (
    FieldRecord,
    GuidanceLine,
    LineExtension,
    LineSource,
    PatternType,
    PropagationDirection,
)

__all__ = ["parse_taskdata"]

_PATTERN_BY_CODE = {
    1: PatternType.AB,
    2: PatternType.A_PLUS,
    3: PatternType.CURVE,
    4: PatternType.PIVOT,
    5: PatternType.SPIRAL,
}

_PROPAGATION_BY_CODE = {
    1: PropagationDirection.BOTH,
    2: PropagationDirection.LEFT,
    3: PropagationDirection.RIGHT,
    4: PropagationDirection.NONE,
}

_EXTENSION_BY_CODE = {
    1: LineExtension.BOTH,
    2: LineExtension.FIRST_ONLY,
    3: LineExtension.LAST_ONLY,
    4: LineExtension.NONE,
}

# PNTA point types that mark a guidance reference rather than a flag or an
# obstacle. A pivot centre arrives as 8; A and B arrive as 6 and 7.
_GUIDANCE_POINT_TYPES = {6, 7, 8, 9}


def _num(el: ET.Element, attr: str) -> float | None:
    raw = el.get(attr)
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _int(el: ET.Element, attr: str) -> int | None:
    value = _num(el, attr)
    return int(value) if value is not None else None


def _points_of(parent: ET.Element) -> list[LatLon]:
    """Every PNT under ``parent``, in document order.

    PNTC is north (latitude) and PNTD is east (longitude) -- the opposite order
    from most JSON APIs, and a classic place to end up with a field in the
    Indian Ocean.
    """
    out: list[LatLon] = []
    for pnt in parent.findall("PNT"):
        lat = _num(pnt, "C")
        lon = _num(pnt, "D")
        if lat is None or lon is None:
            continue
        out.append(LatLon(lat, lon))
    return out


def parse_taskdata(xml_bytes: bytes) -> tuple[list[FieldRecord], list[GuidanceLine], list[str]]:
    """Parse TASKDATA.XML into fields and guidance lines.

    Returns ``(fields, lines, warnings)``. Anything unparseable is reported as a
    warning rather than raised, so one malformed partfield does not cost you the
    rest of the file.
    """
    warnings: list[str] = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError(f"TASKDATA.XML is not well-formed XML: {exc}") from exc

    if root.tag != "ISO11783_TaskData":
        warnings.append(
            f"root element is <{root.tag}>, expected <ISO11783_TaskData>. "
            "Parsing anyway."
        )

    # Customer and farm names live in separate top-level records, referenced by
    # id from each partfield.
    customers = {c.get("A"): c.get("B", "") for c in root.findall("CTR")}
    farms = {f.get("A"): f.get("B", "") for f in root.findall("FRM")}

    fields: list[FieldRecord] = []
    lines: list[GuidanceLine] = []

    for pfd in root.findall("PFD"):
        field = FieldRecord(
            name=pfd.get("C") or pfd.get("B") or "Imported field",
            farm=farms.get(pfd.get("F", ""), ""),
            grower=customers.get(pfd.get("E", ""), ""),
        )

        for pln in pfd.findall("PLN"):
            # PLNA 1 is the partfield boundary; other polygon types are
            # treatment zones, buildings, obstacles and so on.
            if _int(pln, "A") not in (None, 1):
                continue
            rings: list[list[LatLon]] = []
            for lsg in pln.findall("LSG"):
                pts = _points_of(lsg)
                if len(pts) >= 3:
                    rings.append(pts)
            if rings:
                field.boundary = rings
        fields.append(field)

        for ggp in pfd.findall("GGP"):
            group_name = ggp.get("B") or ""
            for gpn in ggp.findall("GPN"):
                line, problem = _parse_pattern(gpn, field, group_name)
                if problem:
                    warnings.append(problem)
                if line is not None:
                    lines.append(line)

    if not fields and not lines:
        warnings.append("no partfields or guidance patterns found in this file")
    return fields, lines, warnings


def _parse_pattern(
    gpn: ET.Element, field: FieldRecord, group_name: str
) -> tuple[GuidanceLine | None, str | None]:
    name = gpn.get("B") or group_name or "Imported line"
    type_code = _int(gpn, "C")
    pattern = _PATTERN_BY_CODE.get(type_code) if type_code is not None else None
    if pattern is None:
        return None, f"guidance pattern {name!r} has unsupported type code {type_code}"

    # Geometry hangs off an LSG child; a pattern with none is a reference to
    # something not in this file.
    points: list[LatLon] = []
    for lsg in gpn.findall("LSG"):
        points.extend(_points_of(lsg))
    if not points:
        points = _points_of(gpn)
    if not points:
        return None, f"guidance pattern {name!r} carries no coordinates"

    heading = _num(gpn, "G")
    # GPNH is an unsigned integer of millimetres, matching how ISOXML carries
    # every other length. Our model works in metres throughout.
    raw_radius = _num(gpn, "H")
    radius = raw_radius / 1000.0 if raw_radius is not None else None

    if pattern is PatternType.AB and len(points) > 2:
        # Some writers densify an AB line into many vertices. Endpoints are all
        # an AB line means, so keep those and drop the rest.
        points = [points[0], points[-1]]
    if pattern is PatternType.A_PLUS:
        points = points[:1]
    if pattern is PatternType.PIVOT:
        points = points[:1]
        if radius is None:
            return None, f"pivot pattern {name!r} has no radius (GPNH)"

    propagation = _PROPAGATION_BY_CODE.get(
        _int(gpn, "E") or 0, PropagationDirection.BOTH
    )
    extension = _EXTENSION_BY_CODE.get(_int(gpn, "F") or 0, LineExtension.BOTH)

    # ISOXML records swath spacing on the guidance group, not the pattern, and
    # not every writer sets it. Zero here means "ask the operator", and the
    # caller substitutes the selected machine's width.
    width = 0.0
    for lsg in gpn.findall("LSG"):
        lsg_width = _num(lsg, "C")
        if lsg_width:
            width = lsg_width / 1000.0  # LSGC is millimetres
            break

    line = GuidanceLine(
        field_id=field.id,
        name=name,
        pattern=pattern,
        points=points,
        heading_deg=heading,
        radius_m=radius,
        swath_width_m=width,
        propagation=propagation,
        extension=extension,
        swaths_left=_int(gpn, "N"),
        swaths_right=_int(gpn, "O"),
        source=LineSource.IMPORTED,
        source_detail=f"ISOXML GPN type {type_code}"
        + (f", group {group_name!r}" if group_name else ""),
    )
    return line, None


def summarize(fields: list[FieldRecord], lines: list[GuidanceLine]) -> dict[str, Any]:
    return {
        "fields": len(fields),
        "lines": len(lines),
        "patterns": sorted({line.pattern.value for line in lines}),
    }
