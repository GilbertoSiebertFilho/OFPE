"""A shapefile reader, written out rather than pulled in.

Reading a shapefile normally means GDAL, which is a large native dependency to
carry for what is, in the end, a documented binary layout with a fixed header
and length-prefixed records. Everything this platform needs -- points, lines,
polygons and their attribute table -- is a couple of hundred lines of
:mod:`struct`, so it lives here and the deployment stays a `pip install` away
from working anywhere.

Reference: ESRI Shapefile Technical Description 98-126, July 1998.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Any, Iterator

__all__ = ["Shape", "read_shp", "read_dbf", "SHAPE_TYPE_NAMES"]

SHAPE_TYPE_NAMES = {
    0: "Null",
    1: "Point",
    3: "PolyLine",
    5: "Polygon",
    8: "MultiPoint",
    11: "PointZ",
    13: "PolyLineZ",
    15: "PolygonZ",
    18: "MultiPointZ",
    21: "PointM",
    23: "PolyLineM",
    25: "PolygonM",
    28: "MultiPointM",
}

_POINT_TYPES = {1, 11, 21}
_POLY_TYPES = {3, 5, 13, 15, 23, 25}
_MULTIPOINT_TYPES = {8, 18, 28}


@dataclass
class Shape:
    """One geometry record.

    ``parts`` is a list of coordinate rings/paths as ``(x, y)`` pairs, where x
    is longitude and y is latitude for the WGS84 files this platform writes and
    expects. A point shape has one part of one coordinate.
    """

    index: int
    shape_type: int
    parts: list[list[tuple[float, float]]]
    attributes: dict[str, Any]

    @property
    def type_name(self) -> str:
        return SHAPE_TYPE_NAMES.get(self.shape_type, f"Unknown({self.shape_type})")

    @property
    def is_polygon(self) -> bool:
        return self.shape_type in {5, 15, 25}

    @property
    def is_line(self) -> bool:
        return self.shape_type in {3, 13, 23}

    @property
    def is_point(self) -> bool:
        return self.shape_type in _POINT_TYPES or self.shape_type in _MULTIPOINT_TYPES

    def all_coords(self) -> list[tuple[float, float]]:
        return [c for part in self.parts for c in part]


def read_shp(data: bytes) -> Iterator[tuple[int, int, list[list[tuple[float, float]]]]]:
    """Yield ``(record_number, shape_type, parts)`` for each record.

    The 100-byte header is checked but otherwise skipped -- record lengths are
    self-describing, so walking the records is more robust than trusting the
    header's total length, which some writers get wrong.
    """
    if len(data) < 100:
        raise ValueError("file is too short to be a shapefile (.shp)")
    (file_code,) = struct.unpack_from(">i", data, 0)
    if file_code != 9994:
        raise ValueError(
            f"not a shapefile: expected file code 9994 at offset 0, found {file_code}"
        )

    offset = 100
    total = len(data)
    while offset + 8 <= total:
        record_number, content_len_words = struct.unpack_from(">ii", data, offset)
        content_len = content_len_words * 2
        body = offset + 8
        if content_len <= 0 or body + content_len > total:
            break
        (shape_type,) = struct.unpack_from("<i", data, body)
        parts = _parse_geometry(data, body, content_len, shape_type)
        yield record_number, shape_type, parts
        offset = body + content_len


def _parse_geometry(
    data: bytes, body: int, content_len: int, shape_type: int
) -> list[list[tuple[float, float]]]:
    if shape_type == 0:
        return []

    if shape_type in _POINT_TYPES:
        x, y = struct.unpack_from("<dd", data, body + 4)
        return [[(x, y)]]

    if shape_type in _MULTIPOINT_TYPES:
        (num_points,) = struct.unpack_from("<i", data, body + 36)
        start = body + 40
        coords = struct.unpack_from(f"<{num_points * 2}d", data, start)
        return [[(coords[i], coords[i + 1]) for i in range(0, len(coords), 2)]]

    if shape_type in _POLY_TYPES:
        num_parts, num_points = struct.unpack_from("<ii", data, body + 36)
        part_start = body + 44
        part_index = struct.unpack_from(f"<{num_parts}i", data, part_start)
        point_start = part_start + num_parts * 4
        flat = struct.unpack_from(f"<{num_points * 2}d", data, point_start)
        points = [(flat[i], flat[i + 1]) for i in range(0, len(flat), 2)]
        out: list[list[tuple[float, float]]] = []
        for i, begin in enumerate(part_index):
            end = part_index[i + 1] if i + 1 < num_parts else num_points
            if end > begin:
                out.append(points[begin:end])
        return out

    raise ValueError(
        f"shape type {shape_type} ({SHAPE_TYPE_NAMES.get(shape_type, '?')}) is not "
        "supported"
    )


def read_dbf(data: bytes) -> list[dict[str, Any]]:
    """Read the attribute table beside a shapefile.

    dBase III fields are fixed-width text; the type byte says how to interpret
    them. Anything that will not parse as its declared type comes back as the
    raw trimmed string rather than raising, because a malformed attribute should
    never stop a geometry from importing.
    """
    if len(data) < 32:
        return []
    num_records, header_len, record_len = struct.unpack_from("<IHH", data, 4)

    fields: list[tuple[str, str, int, int]] = []
    pos = 32
    while pos < header_len - 1 and pos + 32 <= len(data):
        if data[pos] == 0x0D:  # field descriptor terminator
            break
        raw_name = data[pos : pos + 11].split(b"\x00")[0]
        name = raw_name.decode("latin-1", errors="replace").strip()
        field_type = chr(data[pos + 11])
        length = data[pos + 16]
        decimals = data[pos + 17]
        fields.append((name, field_type, length, decimals))
        pos += 32

    records: list[dict[str, Any]] = []
    start = header_len
    for r in range(num_records):
        base = start + r * record_len
        if base + record_len > len(data):
            break
        if data[base : base + 1] == b"*":
            continue  # tombstoned record
        row: dict[str, Any] = {}
        cursor = base + 1
        for name, field_type, length, decimals in fields:
            raw = data[cursor : cursor + length]
            cursor += length
            row[name] = _coerce(raw, field_type, decimals)
        records.append(row)
    return records


def _coerce(raw: bytes, field_type: str, decimals: int) -> Any:
    text = raw.decode("latin-1", errors="replace").strip()
    if not text:
        return None
    try:
        if field_type == "N":
            return float(text) if decimals else int(text)
        if field_type == "F":
            return float(text)
        if field_type == "L":
            return text.upper() in ("Y", "T")
        if field_type == "D" and len(text) == 8:
            return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    except ValueError:
        pass
    return text
