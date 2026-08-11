"""The text-based writers: KML, AGCO KML, GeoJSON, AgOpenGPS.

These share enough shape that keeping them together makes the differences
visible. The important one to read carefully is :func:`build_agco_kml` -- AGCO's
Field Data Converter is fussier about structure than Google Earth is, so the
plain KML and the AGCO KML are deliberately not the same document.
"""

from __future__ import annotations

import json
import math
from xml.sax.saxutils import escape

from ..geo import LatLon, LocalFrame
from ..models import FieldRecord, GuidanceLine, Machine, PatternType

__all__ = [
    "build_kml",
    "build_agco_kml",
    "build_geojson",
    "build_agopengps",
    "expand_for_export",
]


def _coords(points: list[LatLon]) -> str:
    """KML coordinate text: lon,lat,alt -- longitude first, unlike everything else."""
    return " ".join(f"{p.lon:.9f},{p.lat:.9f},0" for p in points)


def expand_for_export(line: GuidanceLine) -> list[list[LatLon]]:
    """Turn a line into drawable paths.

    A pivot is stored as a centre and a radius, which no line-based format can
    represent, so it is expanded into a ring here. Everything else already has
    explicit geometry.
    """
    if line.pattern is PatternType.PIVOT and line.points and line.radius_m:
        frame = LocalFrame(line.points[0])
        cx, cy = frame.to_xy(line.points[0])
        steps = max(64, min(720, int(line.radius_m)))
        ring = [
            (
                cx + line.radius_m * math.sin(2 * math.pi * i / steps),
                cy + line.radius_m * math.cos(2 * math.pi * i / steps),
            )
            for i in range(steps + 1)
        ]
        return [frame.many_to_latlon(ring)]
    if line.pattern is PatternType.A_PLUS and len(line.points) == 1:
        # A+ has no second point; draw a kilometre each way so the heading is
        # visible in anything that renders geometry.
        from ..geo import destination

        heading = line.heading_deg or 0.0
        a = line.points[0]
        return [[destination(a, heading + 180, 1000.0), destination(a, heading, 1000.0)]]
    return [r for r in line.rings() if len(r) >= 2]


def _placemark(name: str, description: str, paths: list[list[LatLon]], style: str) -> str:
    if len(paths) == 1:
        geometry = f"<LineString><tessellate>1</tessellate><coordinates>{_coords(paths[0])}</coordinates></LineString>"
    else:
        inner = "".join(
            f"<LineString><tessellate>1</tessellate><coordinates>{_coords(p)}</coordinates></LineString>"
            for p in paths
        )
        geometry = f"<MultiGeometry>{inner}</MultiGeometry>"
    return (
        f"<Placemark><name>{escape(name)}</name>"
        f"<description>{escape(description)}</description>"
        f"<styleUrl>#{style}</styleUrl>{geometry}</Placemark>"
    )


def _line_description(line: GuidanceLine, machine: Machine | None) -> str:
    bits = [f"Pattern: {line.pattern.value}", f"Swath: {line.swath_width_m:g} m"]
    heading = line.computed_heading()
    if heading is not None:
        bits.append(f"Heading: {heading:.2f}° true")
    if machine:
        bits.append(f"Machine: {machine.name}")
    bits.append(f"Source: {line.source.value}")
    if line.source_detail:
        bits.append(line.source_detail)
    return " | ".join(bits)


def build_kml(
    field: FieldRecord,
    lines: list[GuidanceLine],
    *,
    machine: Machine | None = None,
    document_name: str | None = None,
) -> bytes:
    """A KML with the boundary and every guidance line."""
    name = document_name or field.name or "Guidance lines"
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
        f"<name>{escape(name)}</name>",
        '<Style id="ab"><LineStyle><color>ff00a5ff</color><width>3</width></LineStyle></Style>',
        '<Style id="boundary"><LineStyle><color>ff20c020</color><width>2</width></LineStyle>'
        "<PolyStyle><fill>0</fill></PolyStyle></Style>",
    ]

    if field.has_boundary:
        outer = field.boundary[0]
        ring = outer + ([outer[0]] if outer[0] != outer[-1] else [])
        holes = "".join(
            f"<innerBoundaryIs><LinearRing><coordinates>{_coords(h + [h[0]])}"
            "</coordinates></LinearRing></innerBoundaryIs>"
            for h in field.boundary[1:]
            if len(h) >= 3
        )
        parts.append(
            f"<Placemark><name>{escape(field.name or 'Boundary')}</name>"
            '<styleUrl>#boundary</styleUrl><Polygon>'
            f"<outerBoundaryIs><LinearRing><coordinates>{_coords(ring)}"
            f"</coordinates></LinearRing></outerBoundaryIs>{holes}</Polygon></Placemark>"
        )

    for line in lines:
        paths = expand_for_export(line)
        if paths:
            parts.append(
                _placemark(
                    line.name or "Line", _line_description(line, machine), paths, "ab"
                )
            )

    parts.append("</Document></kml>")
    return "".join(parts).encode("utf-8")


def build_agco_kml(
    field: FieldRecord,
    lines: list[GuidanceLine],
    *,
    machine: Machine | None = None,
) -> bytes:
    """KML arranged the way the AGCO Field Data Converter expects.

    The converter keys off folder structure rather than styles: boundaries in
    one folder, guidance in another, each placemark named plainly. Plain KML
    with everything in a flat document imports as unclassified geometry.
    """
    name = field.name or "Field"
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
        f"<name>{escape(name)}</name>",
    ]

    if field.has_boundary:
        outer = field.boundary[0]
        ring = outer + ([outer[0]] if outer[0] != outer[-1] else [])
        parts.append(
            "<Folder><name>Boundaries</name>"
            f"<Placemark><name>{escape(name)}</name><Polygon><outerBoundaryIs>"
            f"<LinearRing><coordinates>{_coords(ring)}</coordinates></LinearRing>"
            "</outerBoundaryIs></Polygon></Placemark></Folder>"
        )

    parts.append("<Folder><name>Guidance</name>")
    for line in lines:
        for i, path in enumerate(expand_for_export(line)):
            suffix = f" {i + 1}" if i else ""
            parts.append(
                f"<Placemark><name>{escape((line.name or 'Line') + suffix)}</name>"
                f"<description>{escape(_line_description(line, machine))}</description>"
                f"<LineString><tessellate>1</tessellate>"
                f"<coordinates>{_coords(path)}</coordinates></LineString></Placemark>"
            )
    parts.append("</Folder></Document></kml>")
    return "".join(parts).encode("utf-8")


def build_geojson(
    field: FieldRecord,
    lines: list[GuidanceLine],
    *,
    machine: Machine | None = None,
) -> bytes:
    """A FeatureCollection carrying the boundary and every line with attributes."""
    features: list[dict] = []

    if field.has_boundary:
        rings = []
        for ring in field.boundary:
            coords = [[p.lon, p.lat] for p in ring]
            if coords and coords[0] != coords[-1]:
                coords.append(coords[0])
            rings.append(coords)
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "kind": "boundary",
                    "name": field.name,
                    "farm": field.farm,
                    "grower": field.grower,
                    "area_ha": round(field.area_ha(), 4),
                },
                "geometry": {"type": "Polygon", "coordinates": rings},
            }
        )

    for line in lines:
        paths = expand_for_export(line)
        if not paths:
            continue
        properties = {
            "kind": "guidance",
            "name": line.name,
            "pattern": line.pattern.value,
            "swath_width_m": line.swath_width_m,
            "heading_deg": line.computed_heading(),
            "source": line.source.value,
            "source_detail": line.source_detail,
            "confidence": line.confidence,
        }
        if machine:
            properties["machine"] = machine.name
            properties["machine_width_m"] = machine.working_width_m
        geometry = (
            {"type": "LineString", "coordinates": [[p.lon, p.lat] for p in paths[0]]}
            if len(paths) == 1
            else {
                "type": "MultiLineString",
                "coordinates": [[[p.lon, p.lat] for p in path] for path in paths],
            }
        )
        features.append(
            {"type": "Feature", "properties": properties, "geometry": geometry}
        )

    doc = {
        "type": "FeatureCollection",
        "name": field.name or "guidance",
        # RFC 7946 fixes the CRS as WGS84, but naming it explicitly saves an
        # argument with GIS software that still looks for the old member.
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": features,
    }
    return json.dumps(doc, indent=2).encode("utf-8")


def build_agopengps(
    field: FieldRecord, lines: list[GuidanceLine]
) -> dict[str, bytes]:
    """AgOpenGPS field directory files.

    AgOpenGPS works in a local metric frame anchored on a per-field origin
    recorded in Field.txt, so the geometry is written as easting/northing
    relative to that origin, not as lat/lon.
    """
    anchor = field.centroid() or (lines[0].points[0] if lines and lines[0].points else None)
    if anchor is None:
        raise ValueError("cannot write an AgOpenGPS field without any geometry")
    frame = LocalFrame(anchor)

    files: dict[str, bytes] = {}
    files["Field.txt"] = (
        "$FieldDir\r\n"
        f"{field.name or 'Field'}\r\n"
        "$Offsets\r\n"
        "0,0\r\n"
        "$Convergence\r\n"
        "0\r\n"
        "$StartFix\r\n"
        f"{anchor.lat:.9f},{anchor.lon:.9f}\r\n"
    ).encode("utf-8")

    # AgOpenGPS names its axes easting then northing, so that is the order used
    # throughout here. The field order *within* a line is the part we have not
    # been able to confirm against the AgOpenGPS source, which is why the
    # catalog marks this format as unverified and ships Field.kml alongside --
    # the KML is unambiguous and imports cleanly whatever these text files do.
    if field.has_boundary:
        chunks = ["$Boundary"]
        for ring in field.boundary:
            xy = frame.many_to_xy(ring)
            chunks.append("False")  # not a drive-through boundary
            chunks.append(str(len(xy)))
            chunks.extend(f"{x:.3f},{y:.3f},0" for x, y in xy)
        files["Boundary.txt"] = ("\r\n".join(chunks) + "\r\n").encode("utf-8")

    ab_lines = [
        line for line in lines if line.pattern in (PatternType.AB, PatternType.A_PLUS)
    ]
    if ab_lines:
        chunks = ["$ABLines"]
        for line in ab_lines:
            heading = line.computed_heading() or 0.0
            x, y = frame.to_xy(line.points[0])
            chunks.append(
                f"{line.name or 'AB'},{math.radians(heading):.6f},{x:.3f},{y:.3f}"
            )
        files["ABLines.txt"] = ("\r\n".join(chunks) + "\r\n").encode("utf-8")

    curves = [line for line in lines if line.pattern is PatternType.CURVE]
    if curves:
        chunks = ["$CurveLines"]
        for line in curves:
            heading = math.radians(line.computed_heading() or 0.0)
            chunks.append(line.name or "Curve")
            chunks.append(f"{heading:.6f}")
            xy = frame.many_to_xy(line.points)
            chunks.append(str(len(xy)))
            chunks.extend(f"{x:.3f},{y:.3f},{heading:.6f}" for x, y in xy)
        files["CurveLines.txt"] = ("\r\n".join(chunks) + "\r\n").encode("utf-8")

    files["Field.kml"] = build_kml(field, lines)
    return files
