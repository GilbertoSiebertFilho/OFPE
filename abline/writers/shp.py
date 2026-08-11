"""A shapefile writer, to match the reader.

Same reasoning as :mod:`abline.readers.shp`: the format is a documented binary
layout, and writing it directly avoids a GDAL dependency that would otherwise
dominate the install.

A shapefile is really four files that must travel together. :func:`write_lines`
returns all of them (plus ``.prj`` and ``.cpg``) as a dict, because handing a
producer a lone ``.shp`` is the single most common way a shapefile import fails.

Reference: ESRI Shapefile Technical Description 98-126, July 1998.
"""

from __future__ import annotations

import struct
from datetime import date
from typing import Any, Sequence

from ..geo import LatLon

__all__ = ["write_lines", "write_polygons", "WGS84_WKT"]

SHAPE_POLYLINE = 3
SHAPE_POLYGON = 5

WGS84_WKT = (
    'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",'
    'SPHEROID["WGS_1984",6378137.0,298.257223563]],'
    'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
)


def _bbox(parts: Sequence[Sequence[tuple[float, float]]]) -> tuple[float, float, float, float]:
    xs = [x for part in parts for x, _ in part]
    ys = [y for part in parts for _, y in part]
    if not xs:
        return (0.0, 0.0, 0.0, 0.0)
    return (min(xs), min(ys), max(xs), max(ys))


def _pack_record(shape_type: int, parts: Sequence[Sequence[tuple[float, float]]]) -> bytes:
    """One polyline/polygon record body, without the record header."""
    minx, miny, maxx, maxy = _bbox(parts)
    num_parts = len(parts)
    num_points = sum(len(p) for p in parts)

    body = struct.pack("<i", shape_type)
    body += struct.pack("<4d", minx, miny, maxx, maxy)
    body += struct.pack("<ii", num_parts, num_points)

    offset = 0
    for part in parts:
        body += struct.pack("<i", offset)
        offset += len(part)
    for part in parts:
        for x, y in part:
            body += struct.pack("<2d", x, y)
    return body


def _write_geometry(
    shape_type: int, shapes: Sequence[Sequence[Sequence[tuple[float, float]]]]
) -> tuple[bytes, bytes]:
    """Build the .shp and .shx byte strings together.

    They share a record layout -- .shx is just the offset table -- so building
    them in one pass keeps them from drifting apart.
    """
    records: list[bytes] = []
    index: list[tuple[int, int]] = []
    offset_words = 50  # the 100-byte header, measured in 16-bit words

    for parts in shapes:
        body = _pack_record(shape_type, parts)
        content_words = len(body) // 2
        records.append(
            struct.pack(">ii", len(records) + 1, content_words) + body
        )
        index.append((offset_words, content_words))
        offset_words += 4 + content_words  # 8-byte record header = 4 words

    all_parts = [part for parts in shapes for part in parts]
    minx, miny, maxx, maxy = _bbox(all_parts)

    def header(length_words: int) -> bytes:
        head = struct.pack(">i", 9994) + b"\x00" * 20
        head += struct.pack(">i", length_words)
        head += struct.pack("<ii", 1000, shape_type)
        head += struct.pack("<4d", minx, miny, maxx, maxy)
        head += struct.pack("<4d", 0.0, 0.0, 0.0, 0.0)  # Z and M ranges, unused
        return head

    shp_body = b"".join(records)
    shp = header(50 + len(shp_body) // 2) + shp_body

    shx_body = b"".join(struct.pack(">ii", off, length) for off, length in index)
    shx = header(50 + len(shx_body) // 2) + shx_body
    return shp, shx


def _write_dbf(
    columns: Sequence[tuple[str, str, int, int]], rows: Sequence[dict[str, Any]]
) -> bytes:
    """dBase III attribute table.

    ``columns`` are ``(name, type, length, decimals)``. Names are truncated to
    the format's 10-character limit, which is why the column names used by this
    platform are short to begin with.
    """
    header_len = 32 + 32 * len(columns) + 1
    record_len = 1 + sum(c[2] for c in columns)
    today = date.today()

    out = bytearray()
    out += struct.pack(
        "<BBBBIHH20x",
        0x03,
        today.year - 1900,
        today.month,
        today.day,
        len(rows),
        header_len,
        record_len,
    )
    for name, ftype, length, decimals in columns:
        field = name[:10].encode("ascii", "replace")
        out += field.ljust(11, b"\x00")
        out += ftype.encode("ascii")
        out += b"\x00" * 4
        out += bytes([length, decimals])
        out += b"\x00" * 14
    out += b"\x0d"

    for row in rows:
        out += b" "  # not-deleted flag
        for name, ftype, length, decimals in columns:
            value = row.get(name)
            out += _format_field(value, ftype, length, decimals)
    out += b"\x1a"
    return bytes(out)


def _format_field(value: Any, ftype: str, length: int, decimals: int) -> bytes:
    if value is None:
        return b" " * length
    if ftype == "N" or ftype == "F":
        try:
            text = f"{float(value):.{decimals}f}" if decimals else f"{int(value):d}"
        except (TypeError, ValueError):
            text = ""
        # Numerics are right-aligned; a value too wide for the column is
        # blanked rather than silently truncated into a different number.
        return text.rjust(length)[-length:].encode("ascii", "replace") if len(
            text
        ) <= length else b" " * length
    if ftype == "L":
        return (b"T" if value else b"F").ljust(length)
    text = str(value)
    return text.encode("utf-8", "replace")[:length].ljust(length, b" ")


def write_lines(
    lines: Sequence[tuple[str, list[list[LatLon]], dict[str, Any]]],
) -> dict[str, bytes]:
    """Write polyline features.

    Each entry is ``(name, parts, attributes)`` where ``parts`` is a list of
    paths -- more than one when a pattern has several rings, as a headland does.
    """
    shapes: list[list[list[tuple[float, float]]]] = []
    rows: list[dict[str, Any]] = []
    for name, parts, attrs in lines:
        coords = [[(p.lon, p.lat) for p in part] for part in parts if len(part) >= 2]
        if not coords:
            continue
        shapes.append(coords)
        row = {"NAME": name}
        row.update(attrs)
        rows.append(row)

    columns = [
        ("NAME", "C", 32, 0),
        ("PATTERN", "C", 12, 0),
        ("WIDTH_M", "N", 12, 3),
        ("HEADING", "N", 10, 3),
        ("SOURCE", "C", 16, 0),
        ("MACHINE", "C", 32, 0),
        ("LENGTH_M", "N", 14, 2),
    ]
    shp, shx = _write_geometry(SHAPE_POLYLINE, shapes)
    return {
        ".shp": shp,
        ".shx": shx,
        ".dbf": _write_dbf(columns, rows),
        ".prj": WGS84_WKT.encode("ascii"),
        ".cpg": b"UTF-8",
    }


def write_polygons(
    polygons: Sequence[tuple[str, list[list[LatLon]], dict[str, Any]]],
) -> dict[str, bytes]:
    """Write polygon features.

    Shapefile polygons require closed rings, and the outer ring must wind
    clockwise while holes wind counter-clockwise. Both are enforced here rather
    than trusted, since imported boundaries routinely arrive either way round.
    """
    shapes: list[list[list[tuple[float, float]]]] = []
    rows: list[dict[str, Any]] = []
    for name, rings, attrs in polygons:
        coords: list[list[tuple[float, float]]] = []
        for i, ring in enumerate(rings):
            if len(ring) < 3:
                continue
            pts = [(p.lon, p.lat) for p in ring]
            if pts[0] != pts[-1]:
                pts.append(pts[0])
            clockwise = _signed_area(pts) < 0
            want_clockwise = i == 0
            if clockwise != want_clockwise:
                pts.reverse()
            coords.append(pts)
        if not coords:
            continue
        shapes.append(coords)
        row = {"NAME": name}
        row.update(attrs)
        rows.append(row)

    columns = [
        ("NAME", "C", 32, 0),
        ("FARM", "C", 32, 0),
        ("GROWER", "C", 32, 0),
        ("AREA_HA", "N", 14, 4),
    ]
    shp, shx = _write_geometry(SHAPE_POLYGON, shapes)
    return {
        ".shp": shp,
        ".shx": shx,
        ".dbf": _write_dbf(columns, rows),
        ".prj": WGS84_WKT.encode("ascii"),
        ".cpg": b"UTF-8",
    }


def _signed_area(points: Sequence[tuple[float, float]]) -> float:
    """Shoelace area. Positive is counter-clockwise in a y-up frame."""
    return (
        sum(
            x0 * y1 - x1 * y0
            for (x0, y0), (x1, y1) in zip(points, points[1:])
        )
        / 2.0
    )
