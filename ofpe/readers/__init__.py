"""Import: turn somebody else's file into our canonical objects.

:func:`read_any` is the single entry point. Hand it a filename and the bytes and
it works out what it is looking at -- by peeking inside archives, by extension,
and by content sniffing when the extension lies, which it often does when a file
has been round-tripped through email.

Every reader returns an :class:`ImportedData`, so the caller never has to know
which one ran.
"""

from __future__ import annotations

import csv
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field as dc_field

from ..geo import LatLon
from ..fitting import TrackPoint
from ..models import FieldRecord, GuidanceLine, LineSource, PatternType
from . import isoxml as isoxml_reader
from .shp import Shape, read_dbf, read_shp

__all__ = ["ImportedData", "read_any", "read_zip"]


@dataclass
class ImportedData:
    """Whatever a file turned out to contain."""

    fields: list[FieldRecord] = dc_field(default_factory=list)
    lines: list[GuidanceLine] = dc_field(default_factory=list)
    track: list[TrackPoint] = dc_field(default_factory=list)
    warnings: list[str] = dc_field(default_factory=list)
    detected_format: str = "unknown"

    def extend(self, other: "ImportedData") -> None:
        self.fields.extend(other.fields)
        self.lines.extend(other.lines)
        self.track.extend(other.track)
        self.warnings.extend(other.warnings)
        if self.detected_format in ("unknown", "") and other.detected_format:
            self.detected_format = other.detected_format

    @property
    def is_empty(self) -> bool:
        return not (self.fields or self.lines or self.track)

    def to_dict(self) -> dict:
        return {
            "detected_format": self.detected_format,
            "fields": [f.to_dict() for f in self.fields],
            "lines": [line.to_dict() for line in self.lines],
            "track_points": len(self.track),
            "warnings": self.warnings,
        }


def read_any(filename: str, data: bytes) -> ImportedData:
    """Read any supported file. Dispatches on content first, name second."""
    name = (filename or "").lower()

    if data[:4] == b"PK\x03\x04":
        return read_zip(data, source_name=filename)
    if data[:4] == b"\x00\x00\x27\x0a" or data[:4] == b"\x00\x00\x27\x0b":
        raise ValueError(
            f"{filename}: this looks like a shapefile index (.shx) or similar "
            "sidecar. Upload the .shp, or better, a zip of the whole set."
        )
    if len(data) >= 4 and int.from_bytes(data[:4], "big") == 9994:
        return _read_loose_shapefile(filename, data)

    stripped = data.lstrip()[:512]
    if stripped[:1] == b"<":
        return _read_xml(filename, data)
    if stripped[:1] in (b"{", b"["):
        return _read_geojson(filename, data)
    if name.endswith((".csv", ".txt", ".tsv")):
        return _read_delimited(filename, data)

    # Fall back to a delimited-text attempt: many monitor exports have no
    # extension at all once they have been through a file manager.
    try:
        return _read_delimited(filename, data)
    except ValueError:
        raise ValueError(
            f"{filename}: unrecognised file. Supported: shapefile (.shp or a "
            "zip of the set), ISOXML TASKDATA, KML/KMZ, GeoJSON, and delimited "
            "text track logs."
        ) from None


def read_zip(data: bytes, *, source_name: str = "archive.zip") -> ImportedData:
    """Read an archive: shapefile sets, TASKDATA folders, KMZ, or a mixture."""
    out = ImportedData(detected_format="zip")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ValueError(f"{source_name}: not a readable zip archive ({exc})") from exc

    names = [n for n in archive.namelist() if not n.endswith("/")]
    lowered = {n.lower(): n for n in names}

    # TASKDATA.XML anywhere in the tree, at any depth.
    taskdata = [n for n in names if n.lower().endswith("taskdata.xml")]
    for entry in taskdata:
        fields, lines, warnings = isoxml_reader.parse_taskdata(archive.read(entry))
        out.fields.extend(fields)
        out.lines.extend(lines)
        out.warnings.extend(f"{entry}: {w}" for w in warnings)
        out.detected_format = "isoxml"

    # Shapefile sets: group by base name so .shp finds its .dbf.
    shp_entries = [n for n in names if n.lower().endswith(".shp")]
    for entry in shp_entries:
        base = entry[:-4]
        dbf = lowered.get((base + ".dbf").lower())
        try:
            result = _shapes_to_data(
                entry,
                archive.read(entry),
                archive.read(dbf) if dbf else None,
            )
        except ValueError as exc:
            out.warnings.append(str(exc))
            continue
        out.extend(result)
        out.detected_format = "shapefile"

    for entry in names:
        low = entry.lower()
        if low.endswith((".kml",)):
            out.extend(_read_kml(entry, archive.read(entry)))
            out.detected_format = "kml"
        elif low.endswith((".geojson", ".json")):
            try:
                out.extend(_read_geojson(entry, archive.read(entry)))
                out.detected_format = "geojson"
            except ValueError as exc:
                out.warnings.append(str(exc))

    if out.is_empty and not taskdata and not shp_entries:
        out.warnings.append(
            f"{source_name}: nothing readable in the archive. Looked for "
            "TASKDATA.XML, .shp, .kml and .geojson."
        )
    return out


def _read_loose_shapefile(filename: str, data: bytes) -> ImportedData:
    result = _shapes_to_data(filename, data, None)
    result.warnings.append(
        f"{filename}: read without its .dbf, so line names and widths are "
        "missing. Upload a zip of the whole shapefile set to keep attributes."
    )
    return result


def _shapes_to_data(
    filename: str, shp_bytes: bytes, dbf_bytes: bytes | None
) -> ImportedData:
    out = ImportedData(detected_format="shapefile")
    attributes = read_dbf(dbf_bytes) if dbf_bytes else []

    shapes: list[Shape] = []
    for i, (record_number, shape_type, parts) in enumerate(read_shp(shp_bytes)):
        attrs = attributes[i] if i < len(attributes) else {}
        shapes.append(Shape(record_number, shape_type, parts, attrs))

    for shape in shapes:
        if not shape.parts:
            continue
        if shape.is_polygon:
            rings = [[LatLon(y, x) for x, y in part] for part in shape.parts]
            name = _first_attr(shape.attributes, ("name", "field", "fieldname", "id"))
            out.fields.append(
                FieldRecord(
                    name=str(name) if name else f"{_stem(filename)} boundary",
                    boundary=rings,
                    notes=f"imported from {filename}",
                )
            )
        elif shape.is_line:
            for part in shape.parts:
                pts = [LatLon(y, x) for x, y in part]
                if len(pts) < 2:
                    continue
                name = _first_attr(shape.attributes, ("name", "line", "track", "id"))
                width = _first_attr(
                    shape.attributes, ("width", "swath", "swath_m", "width_m")
                )
                pattern_raw = _first_attr(shape.attributes, ("pattern", "type"))
                pattern = _pattern_from_text(pattern_raw)
                if pattern is PatternType.AB and len(pts) > 2:
                    pts = [pts[0], pts[-1]]
                out.lines.append(
                    GuidanceLine(
                        name=str(name) if name else f"{_stem(filename)} line",
                        pattern=pattern,
                        points=pts,
                        swath_width_m=float(width) if _is_number(width) else 0.0,
                        source=LineSource.IMPORTED,
                        source_detail=f"shapefile {filename}",
                    )
                )

    if not out.fields and not out.lines:
        types = sorted({s.type_name for s in shapes})
        raise ValueError(
            f"{filename}: no usable geometry. Found {len(shapes)} record(s) of "
            f"type {', '.join(types) or 'none'}; we read polylines and polygons."
        )
    return out


def _read_xml(filename: str, data: bytes) -> ImportedData:
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError(f"{filename}: malformed XML ({exc})") from exc

    tag = root.tag.split("}")[-1]
    if tag == "ISO11783_TaskData" or filename.lower().endswith("taskdata.xml"):
        fields, lines, warnings = isoxml_reader.parse_taskdata(data)
        return ImportedData(
            fields=fields, lines=lines, warnings=warnings, detected_format="isoxml"
        )
    if tag == "kml":
        return _read_kml(filename, data)
    raise ValueError(
        f"{filename}: XML root <{tag}> is not something we read. Expected "
        "ISO11783_TaskData (ISOXML) or kml."
    )


def _read_kml(filename: str, data: bytes) -> ImportedData:
    out = ImportedData(detected_format="kml")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError(f"{filename}: malformed KML ({exc})") from exc

    ns = {"k": "http://www.opengis.net/kml/2.2"}

    def find_all(el, path):
        # KML in the wild is inconsistent about declaring the namespace, so try
        # the namespaced path and fall back to a bare one.
        found = el.findall(path.replace("k:", "k:"), ns)
        return found or el.findall(path.replace("k:", ""))

    for placemark in find_all(root, ".//k:Placemark"):
        name_el = placemark.find("k:name", ns)
        if name_el is None:
            name_el = placemark.find("name")
        name = (name_el.text or "").strip() if name_el is not None else ""

        for poly in find_all(placemark, ".//k:Polygon"):
            rings: list[list[LatLon]] = []
            for coords_el in find_all(poly, ".//k:coordinates"):
                pts = _parse_kml_coords(coords_el.text or "")
                if len(pts) >= 3:
                    rings.append(pts)
            if rings:
                out.fields.append(
                    FieldRecord(
                        name=name or f"{_stem(filename)} boundary",
                        boundary=rings,
                        notes=f"imported from {filename}",
                    )
                )

        for line in find_all(placemark, ".//k:LineString"):
            coords_el = line.find("k:coordinates", ns)
            if coords_el is None:
                coords_el = line.find("coordinates")
            if coords_el is None:
                continue
            pts = _parse_kml_coords(coords_el.text or "")
            if len(pts) < 2:
                continue
            out.lines.append(
                GuidanceLine(
                    name=name or f"{_stem(filename)} line",
                    pattern=PatternType.CURVE if len(pts) > 2 else PatternType.AB,
                    points=pts,
                    source=LineSource.IMPORTED,
                    source_detail=f"KML {filename}",
                )
            )

    if out.is_empty:
        out.warnings.append(f"{filename}: no polygons or line strings found")
    return out


def _parse_kml_coords(text: str) -> list[LatLon]:
    """KML coordinates are ``lon,lat[,alt]`` triples, whitespace separated."""
    out: list[LatLon] = []
    for token in text.replace("\n", " ").split():
        bits = token.split(",")
        if len(bits) < 2:
            continue
        try:
            lon, lat = float(bits[0]), float(bits[1])
        except ValueError:
            continue
        out.append(LatLon(lat, lon))
    return out


def _read_geojson(filename: str, data: bytes) -> ImportedData:
    out = ImportedData(detected_format="geojson")
    try:
        doc = json.loads(data.decode("utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"{filename}: not valid JSON ({exc})") from exc

    features = (
        doc.get("features", [])
        if isinstance(doc, dict) and doc.get("type") == "FeatureCollection"
        else [doc]
        if isinstance(doc, dict)
        else list(doc)
    )

    for feature in features:
        if not isinstance(feature, dict):
            continue
        geom = feature.get("geometry") or feature
        props = feature.get("properties") or {}
        gtype = geom.get("type")
        coords = geom.get("coordinates")
        if not gtype or coords is None:
            continue
        name = props.get("name") or props.get("Name") or ""

        if gtype in ("Polygon", "MultiPolygon"):
            polys = [coords] if gtype == "Polygon" else coords
            for poly in polys:
                rings = [[LatLon(c[1], c[0]) for c in ring] for ring in poly]
                if rings and len(rings[0]) >= 3:
                    out.fields.append(
                        FieldRecord(
                            name=str(name) or f"{_stem(filename)} boundary",
                            boundary=rings,
                            notes=f"imported from {filename}",
                        )
                    )
        elif gtype in ("LineString", "MultiLineString"):
            paths = [coords] if gtype == "LineString" else coords
            for path in paths:
                pts = [LatLon(c[1], c[0]) for c in path]
                if len(pts) < 2:
                    continue
                width = props.get("swath_width_m") or props.get("width")
                pattern = _pattern_from_text(props.get("pattern"))
                if pattern is PatternType.AB and len(pts) > 2:
                    pts = [pts[0], pts[-1]]
                out.lines.append(
                    GuidanceLine(
                        name=str(name) or f"{_stem(filename)} line",
                        pattern=pattern,
                        points=pts,
                        swath_width_m=float(width) if _is_number(width) else 0.0,
                        source=LineSource.IMPORTED,
                        source_detail=f"GeoJSON {filename}",
                    )
                )

    if out.is_empty:
        out.warnings.append(f"{filename}: no polygons or line strings found")
    return out


# Column names monitors actually use, lowercased. Order matters: the first
# match wins, so the most specific spellings come first.
_LAT_KEYS = ("latitude", "lat", "gps_lat", "y", "northing")
_LON_KEYS = ("longitude", "long", "lon", "lng", "gps_lon", "x", "easting")
_HEADING_KEYS = ("heading", "track_deg", "course", "bearing", "direction")
_SPEED_KEYS = ("speed", "speed_ms", "velocity", "ground_speed")
_TIME_KEYS = ("timestamp", "time", "datetime", "gps_time", "utc")
_RECORDING_KEYS = ("recording", "logging", "master", "section_on", "implement_on")


def _read_delimited(filename: str, data: bytes) -> ImportedData:
    """Read a monitor track log: any delimited text with a lat and a lon column."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("latin-1")

    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel  # a single-column file still parses as CSV

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise ValueError(f"{filename}: no header row found")

    lookup = {_norm(h): h for h in reader.fieldnames if h}
    lat_key = _pick(lookup, _LAT_KEYS)
    lon_key = _pick(lookup, _LON_KEYS)
    if not lat_key or not lon_key:
        raise ValueError(
            f"{filename}: could not find latitude and longitude columns. "
            f"Saw: {', '.join(reader.fieldnames[:20])}"
        )

    heading_key = _pick(lookup, _HEADING_KEYS)
    speed_key = _pick(lookup, _SPEED_KEYS)
    time_key = _pick(lookup, _TIME_KEYS)
    rec_key = _pick(lookup, _RECORDING_KEYS)

    track: list[TrackPoint] = []
    skipped = 0
    for row in reader:
        try:
            lat = float(str(row.get(lat_key, "")).replace(",", "."))
            lon = float(str(row.get(lon_key, "")).replace(",", "."))
        except (TypeError, ValueError):
            skipped += 1
            continue
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            skipped += 1
            continue
        track.append(
            TrackPoint(
                lat=lat,
                lon=lon,
                timestamp=str(row.get(time_key)) if time_key else None,
                heading_deg=_maybe_float(row.get(heading_key)) if heading_key else None,
                speed_ms=_maybe_float(row.get(speed_key)) if speed_key else None,
                recording=_maybe_bool(row.get(rec_key)) if rec_key else None,
            )
        )

    out = ImportedData(track=track, detected_format="track_log")
    if not track:
        raise ValueError(
            f"{filename}: found latitude/longitude columns but no rows parsed "
            "into valid coordinates."
        )
    if skipped:
        out.warnings.append(
            f"{filename}: skipped {skipped} row(s) with missing or out-of-range "
            "coordinates."
        )
    out.warnings.append(
        f"{filename}: read {len(track)} track points from columns "
        f"{lat_key!r}/{lon_key!r}."
    )
    return out


def _norm(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", header.lower())


def _pick(lookup: dict[str, str], candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        key = _norm(candidate)
        if key in lookup:
            return lookup[key]
    # Second pass: allow a candidate to appear as a substring, which catches
    # headers like "GPS Latitude (deg)".
    for candidate in candidates:
        key = _norm(candidate)
        for norm_header, original in lookup.items():
            if key and key in norm_header:
                return original
    return None


def _maybe_float(value) -> float | None:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _maybe_bool(value) -> bool | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "y", "on", "recording"):
        return True
    if text in ("0", "false", "no", "n", "off"):
        return False
    return None


def _is_number(value) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _first_attr(attrs: dict, keys: tuple[str, ...]):
    normalized = {_norm(k): v for k, v in attrs.items()}
    for key in keys:
        value = normalized.get(_norm(key))
        if value not in (None, ""):
            return value
    return None


def _pattern_from_text(value) -> PatternType:
    text = str(value or "").strip().upper().replace(" ", "_")
    for pattern in PatternType:
        if text == pattern.value:
            return pattern
    if text in ("CURVE", "AB_CURVE", "ADAPTIVE_CURVE", "CONTOUR"):
        return PatternType.CURVE
    if text in ("PIVOT", "CIRCLE", "CIRCLE_TRACK"):
        return PatternType.PIVOT
    if text in ("HEADLAND", "BOUNDARY"):
        return PatternType.HEADLAND
    return PatternType.AB


def _stem(filename: str) -> str:
    return filename.rsplit("/", 1)[-1].rsplit(".", 1)[0] or "import"
