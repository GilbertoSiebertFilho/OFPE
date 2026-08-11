"""ISOXML (ISO 11783-10) writer -- the format that covers the most terminals.

Guidance in ISOXML nests like this::

    ISO11783_TaskData
      CTR                       customer / grower
      FRM                       farm
      PFD                       partfield -- the field itself
        PLN > LSG > PNT         the boundary
        GGP                     guidance group: one swath spacing
          GPN                   guidance pattern: one line
            LSG > PNT           the line's geometry

**Provenance of the codes below.** Element and attribute letter codes (PFDA,
GGPA, GPNA-GPNO, LSGA-LSGF, PNTA-PNTK) were checked against the AgGateway ADAPT
ISOv4Plugin reference implementation. The *enumeration integers* -- pattern type
1-5, point type 6/7/8/9, line string type 5 -- are the values used consistently
across ADAPT, CNH's published plugin and the wider ISOBUS tooling, but the ISO
standard itself is paywalled and isobus.net was not reachable to confirm them
first-hand. They are constants at the top of this module for exactly that
reason: if a real terminal export disagrees, one edit here fixes every export.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from xml.dom import minidom

from ..geo import LatLon
from ..models import FieldRecord, GuidanceLine, Machine, PatternType

__all__ = ["build_taskdata", "PATTERN_CODE", "POINT_TYPE"]

# GPNC -- GuidancePatternType
PATTERN_CODE = {
    PatternType.AB: 1,
    PatternType.A_PLUS: 2,
    PatternType.CURVE: 3,
    PatternType.PIVOT: 4,
    PatternType.SPIRAL: 5,
    PatternType.HEADLAND: 3,  # no dedicated code; a headland ring is a curve
}

# PNTA -- PointType
POINT_TYPE = {
    "other": 2,
    "guidance_a": 6,
    "guidance_b": 7,
    "guidance_center": 8,
    "guidance_point": 9,
}

# LSGA -- LineStringType
LINE_STRING_TYPE = {
    "polygon_exterior": 1,
    "polygon_interior": 2,
    "guidance_pattern": 5,
}

# PLNA -- PolygonType
POLYGON_TYPE_BOUNDARY = 1

SOFTWARE_NAME = "OFPE Field Data Platform"
"""Written into every TASKDATA.XML as ManagementSoftwareManufacturer.

This lands on customers' terminals, so it is the product's name and not an
internal one. ISO 11783-10 caps the field at 32 characters.
"""
SOFTWARE_VERSION = "1.0"


def _pnt(parent: ET.Element, point: LatLon, point_type: int) -> None:
    """Append a PNT. C is north (latitude), D is east (longitude)."""
    ET.SubElement(
        parent,
        "PNT",
        {
            "A": str(point_type),
            "C": f"{point.lat:.9f}",
            "D": f"{point.lon:.9f}",
        },
    )


def _add_boundary(pfd: ET.Element, field: FieldRecord) -> None:
    if not field.has_boundary:
        return
    pln = ET.SubElement(
        pfd,
        "PLN",
        {"A": str(POLYGON_TYPE_BOUNDARY), "B": (field.name or "Boundary")[:32]},
    )
    for i, ring in enumerate(field.boundary):
        if len(ring) < 3:
            continue
        lsg = ET.SubElement(
            pln,
            "LSG",
            {
                "A": str(
                    LINE_STRING_TYPE["polygon_exterior"]
                    if i == 0
                    else LINE_STRING_TYPE["polygon_interior"]
                )
            },
        )
        pts = list(ring)
        # ISOXML rings are implicitly closed; a repeated last vertex is
        # tolerated by most terminals but a few draw a zero-length segment.
        if len(pts) > 1 and pts[0].lat == pts[-1].lat and pts[0].lon == pts[-1].lon:
            pts = pts[:-1]
        for point in pts:
            _pnt(lsg, point, POINT_TYPE["other"])


def _add_pattern(
    ggp: ET.Element, line: GuidanceLine, index: int, densify_curves: bool
) -> None:
    attrs = {
        "A": f"GPN{index}",
        "B": (line.name or f"Line {index}")[:32],
        "C": str(PATTERN_CODE[line.pattern]),
        "E": str(line.propagation.isoxml_code),
        "F": str(line.extension.isoxml_code),
    }
    heading = line.computed_heading()
    if heading is not None:
        attrs["G"] = f"{heading:.4f}"
    if line.radius_m:
        # GPNH is an unsigned integer; ISOXML carries lengths in millimetres.
        attrs["H"] = str(int(round(line.radius_m * 1000)))
    if line.swaths_left is not None:
        attrs["N"] = str(max(0, int(line.swaths_left)))
    if line.swaths_right is not None:
        attrs["O"] = str(max(0, int(line.swaths_right)))

    gpn = ET.SubElement(ggp, "GPN", attrs)

    lsg_attrs = {"A": str(LINE_STRING_TYPE["guidance_pattern"])}
    if line.swath_width_m > 0:
        lsg_attrs["C"] = str(int(round(line.swath_width_m * 1000)))
    lsg = ET.SubElement(gpn, "LSG", lsg_attrs)

    if line.pattern is PatternType.AB and len(line.points) >= 2:
        _pnt(lsg, line.points[0], POINT_TYPE["guidance_a"])
        _pnt(lsg, line.points[-1], POINT_TYPE["guidance_b"])
    elif line.pattern is PatternType.A_PLUS and line.points:
        _pnt(lsg, line.points[0], POINT_TYPE["guidance_a"])
    elif line.pattern is PatternType.PIVOT and line.points:
        _pnt(lsg, line.points[0], POINT_TYPE["guidance_center"])
    else:
        points = line.points
        if densify_curves and line.pattern is PatternType.CURVE:
            from ..generate import curve_vertices_for_export

            points = curve_vertices_for_export(points)
        for point in points:
            _pnt(lsg, point, POINT_TYPE["guidance_point"])


def build_taskdata(
    field: FieldRecord,
    lines: list[GuidanceLine],
    *,
    machine: Machine | None = None,
    densify_curves: bool = True,
    version_minor: int = 3,
) -> bytes:
    """Build a complete TASKDATA.XML.

    Lines are grouped into one GGP per distinct swath width, because a guidance
    group is defined by its spacing: putting a 12 m combine line and a 36 m
    sprayer line in the same group would make one of them wrong.
    """
    root = ET.Element(
        "ISO11783_TaskData",
        {
            "VersionMajor": "4",
            "VersionMinor": str(version_minor),
            "ManagementSoftwareManufacturer": SOFTWARE_NAME,
            "ManagementSoftwareVersion": SOFTWARE_VERSION,
            "DataTransferOrigin": "1",  # 1 = FMIS, i.e. written by office software
        },
    )

    if field.grower:
        ET.SubElement(root, "CTR", {"A": "CTR1", "B": field.grower[:32]})
    if field.farm:
        farm_attrs = {"A": "FRM1", "B": field.farm[:32]}
        if field.grower:
            farm_attrs["I"] = "CTR1"
        ET.SubElement(root, "FRM", farm_attrs)

    pfd_attrs = {
        "A": "PFD1",
        "C": (field.name or "Field")[:32],
        "D": str(int(round(field.area_ha() * 10_000))),  # PFDD is square metres
    }
    if field.grower:
        pfd_attrs["E"] = "CTR1"
    if field.farm:
        pfd_attrs["F"] = "FRM1"
    pfd = ET.SubElement(root, "PFD", pfd_attrs)

    _add_boundary(pfd, field)

    by_width: dict[int, list[GuidanceLine]] = {}
    for line in lines:
        key = int(round(line.swath_width_m * 1000))
        by_width.setdefault(key, []).append(line)

    pattern_index = 1
    for group_index, (width_mm, group_lines) in enumerate(sorted(by_width.items()), 1):
        label = f"{width_mm / 1000:g} m"
        if machine and machine.name:
            label = f"{machine.name} ({label})"
        ggp = ET.SubElement(pfd, "GGP", {"A": f"GGP{group_index}", "B": label[:32]})
        for line in group_lines:
            if line.pattern is PatternType.HEADLAND:
                # Each headland ring is its own pattern; a GPN holds one line.
                for ring_no, ring in enumerate(line.rings(), 1):
                    ring_line = GuidanceLine(
                        name=f"{line.name} {ring_no}",
                        pattern=PatternType.CURVE,
                        points=ring,
                        swath_width_m=line.swath_width_m,
                        propagation=line.propagation,
                        extension=line.extension,
                    )
                    _add_pattern(ggp, ring_line, pattern_index, densify_curves)
                    pattern_index += 1
            else:
                _add_pattern(ggp, line, pattern_index, densify_curves)
                pattern_index += 1

    raw = ET.tostring(root, encoding="utf-8")
    # Terminals do not care about whitespace, but a human debugging an import
    # failure very much does.
    pretty = minidom.parseString(raw).toprettyxml(indent="  ", encoding="UTF-8")
    return pretty
