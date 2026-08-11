"""Export and import: everything that crosses the boundary to another system.

The round-trip tests are the important ones. A writer that produces a plausible
file and a reader that accepts a plausible file can both be wrong in the same
direction; making the pair agree on real geometry catches that.
"""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile

import pytest

from ofpe.catalog import MONITORS, SupportLevel
from ofpe.generate import line_from_boundary, make_headland, make_pivot_line
from ofpe.geo import LatLon, geodesic_distance
from ofpe.models import FieldRecord, GuidanceLine, PatternType
from ofpe.readers import read_any
from ofpe.readers.isoxml import parse_taskdata
from ofpe.readers.shp import read_dbf, read_shp
from ofpe.writers import build_download, build_format
from ofpe.writers.isoxml import build_taskdata
from ofpe.writers.shp import write_lines, write_polygons
from ofpe.writers.simple import build_geojson, build_kml


# ------------------------------------------------------------------- ISOXML


def test_isoxml_structure_nests_correctly(rectangle_field, combine):
    line, _ = line_from_boundary(rectangle_field, combine)
    xml = build_taskdata(rectangle_field, [line], machine=combine)
    root = ET.fromstring(xml)

    assert root.tag == "ISO11783_TaskData"
    assert root.get("VersionMajor") == "4"
    assert root.get("DataTransferOrigin") == "1"

    pfd = root.find("PFD")
    assert pfd is not None and pfd.get("C") == "Test Rectangle"

    # The boundary is a PLN of type 1 holding an exterior LSG of type 1.
    pln = pfd.find("PLN")
    assert pln.get("A") == "1"
    assert pln.find("LSG").get("A") == "1"

    ggp = pfd.find("GGP")
    assert ggp is not None
    gpn = ggp.find("GPN")
    assert gpn.get("C") == "1"  # AB pattern
    lsg = gpn.find("LSG")
    assert lsg.get("A") == "5"  # guidance pattern line string
    assert int(lsg.get("C")) == round(combine.effective_width_m * 1000)

    points = lsg.findall("PNT")
    assert len(points) == 2
    assert points[0].get("A") == "6"  # guidance reference A
    assert points[1].get("A") == "7"  # guidance reference B


def test_isoxml_puts_latitude_in_c_and_longitude_in_d(rectangle_field, combine):
    """The classic way to end up with a field in the wrong hemisphere."""
    line, _ = line_from_boundary(rectangle_field, combine)
    root = ET.fromstring(build_taskdata(rectangle_field, [line]))
    point = root.find(".//GGP/GPN/LSG/PNT")
    assert float(point.get("C")) == pytest.approx(-27.84, abs=0.02)  # latitude
    assert float(point.get("D")) == pytest.approx(-54.478, abs=0.02)  # longitude


def test_isoxml_groups_lines_by_swath_width(rectangle_field, combine, isobus_machine):
    """Two machines of different widths need two guidance groups, not one."""
    wide, _ = line_from_boundary(rectangle_field, combine)
    narrow, _ = line_from_boundary(rectangle_field, isobus_machine)
    root = ET.fromstring(build_taskdata(rectangle_field, [wide, narrow]))
    groups = root.findall("PFD/GGP")
    assert len(groups) == 2


def test_isoxml_round_trips_an_ab_line(rectangle_field, combine):
    original, _ = line_from_boundary(rectangle_field, combine)
    xml = build_taskdata(rectangle_field, [original], machine=combine)

    fields, lines, warnings = parse_taskdata(xml)
    assert warnings == []
    assert len(fields) == 1 and len(lines) == 1

    restored = lines[0]
    assert restored.pattern is PatternType.AB
    assert restored.swath_width_m == pytest.approx(combine.effective_width_m, abs=0.001)
    for before, after in zip(original.points, restored.points):
        assert geodesic_distance(before, after) < 0.01

    assert fields[0].name == rectangle_field.name
    assert fields[0].area_ha() == pytest.approx(rectangle_field.area_ha(), rel=0.01)


def test_isoxml_round_trips_a_pivot():
    centre = LatLon(-27.845, -54.477)
    field = FieldRecord(name="Pivot field")
    line = make_pivot_line(centre, 350.0, width_m=18.0, name="Centre pivot")

    fields, lines, warnings = parse_taskdata(build_taskdata(field, [line]))
    assert warnings == []
    restored = lines[0]
    assert restored.pattern is PatternType.PIVOT
    assert restored.radius_m == pytest.approx(350.0, abs=0.01)
    assert geodesic_distance(restored.points[0], centre) < 0.01


def test_isoxml_writes_each_headland_ring_as_its_own_pattern(rectangle_field):
    headland = make_headland(rectangle_field, width_m=12.0, passes=3)
    root = ET.fromstring(build_taskdata(rectangle_field, [headland]))
    patterns = root.findall("PFD/GGP/GPN")
    assert len(patterns) == 3
    assert all(p.get("C") == "3" for p in patterns)  # written as curves


def test_isoxml_reader_reports_a_bad_document():
    with pytest.raises(ValueError, match="not well-formed"):
        parse_taskdata(b"<ISO11783_TaskData><PFD></ISO11783")


# ---------------------------------------------------------------- shapefile


def test_shapefile_round_trips_line_geometry():
    parts = [[LatLon(-27.840, -54.485), LatLon(-27.849, -54.470)]]
    files = write_lines([("North AB", parts, {"PATTERN": "AB", "WIDTH_M": 12.0})])

    assert set(files) == {".shp", ".shx", ".dbf", ".prj", ".cpg"}
    assert b"WGS_1984" in files[".prj"]

    records = list(read_shp(files[".shp"]))
    assert len(records) == 1
    _, shape_type, geometry = records[0]
    assert shape_type == 3  # PolyLine
    (x0, y0), (x1, y1) = geometry[0]
    # Shapefiles store x=longitude, y=latitude.
    assert x0 == pytest.approx(-54.485) and y0 == pytest.approx(-27.840)
    assert x1 == pytest.approx(-54.470) and y1 == pytest.approx(-27.849)

    attributes = read_dbf(files[".dbf"])
    assert attributes[0]["NAME"] == "North AB"
    assert attributes[0]["PATTERN"] == "AB"
    assert attributes[0]["WIDTH_M"] == pytest.approx(12.0)


def test_shapefile_index_offsets_line_up_with_the_records():
    """A wrong .shx is the classic way a shapefile opens as an empty layer."""
    parts_a = [[LatLon(-27.84, -54.48), LatLon(-27.85, -54.47)]]
    parts_b = [[LatLon(-27.84, -54.46), LatLon(-27.85, -54.45), LatLon(-27.86, -54.44)]]
    files = write_lines([("A", parts_a, {}), ("B", parts_b, {})])

    import struct

    shx, shp = files[".shx"], files[".shp"]
    entries = (len(shx) - 100) // 8
    assert entries == 2
    for i in range(entries):
        offset_words, length_words = struct.unpack_from(">ii", shx, 100 + i * 8)
        byte_offset = offset_words * 2
        record_number, content_words = struct.unpack_from(">ii", shp, byte_offset)
        assert record_number == i + 1
        assert content_words == length_words


def test_polygon_writer_closes_and_winds_rings_clockwise(rectangle_field):
    files = write_polygons([("Field", rectangle_field.boundary, {"AREA_HA": 147.0})])
    _, shape_type, rings = next(iter(read_shp(files[".shp"])))
    assert shape_type == 5  # Polygon
    ring = rings[0]
    assert ring[0] == ring[-1], "a shapefile polygon ring must be closed"
    area2 = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:]))
    assert area2 < 0, "the outer ring must wind clockwise"


def test_shapefile_reader_rejects_a_non_shapefile():
    """Long enough to have a header, but the wrong magic number."""
    with pytest.raises(ValueError, match="not a shapefile"):
        list(read_shp(b"NOT-A-SHAPEFILE" + b"\x00" * 200))


def test_shapefile_reader_rejects_a_truncated_file():
    with pytest.raises(ValueError, match="too short"):
        list(read_shp(b"\x00\x00\x27\x0a"))


# --------------------------------------------------------------- KML / JSON


def test_kml_puts_longitude_first(rectangle_field, combine):
    line, _ = line_from_boundary(rectangle_field, combine)
    kml = build_kml(rectangle_field, [line], machine=combine).decode()
    root = ET.fromstring(kml)
    ns = {"k": "http://www.opengis.net/kml/2.2"}
    coords = root.find(".//k:LineString/k:coordinates", ns).text.split()
    lon, lat, _alt = coords[0].split(",")
    assert float(lon) == pytest.approx(-54.478, abs=0.02)
    assert float(lat) == pytest.approx(-27.845, abs=0.02)


def test_geojson_carries_the_attributes_a_reader_needs(rectangle_field, combine):
    import json

    line, _ = line_from_boundary(rectangle_field, combine)
    doc = json.loads(build_geojson(rectangle_field, [line], machine=combine))
    assert doc["type"] == "FeatureCollection"

    guidance = [f for f in doc["features"] if f["properties"]["kind"] == "guidance"]
    assert len(guidance) == 1
    props = guidance[0]["properties"]
    assert props["pattern"] == "AB"
    assert props["swath_width_m"] == pytest.approx(combine.effective_width_m)
    assert props["machine"] == combine.name

    boundary = [f for f in doc["features"] if f["properties"]["kind"] == "boundary"]
    assert boundary[0]["geometry"]["coordinates"][0][0] == \
        boundary[0]["geometry"]["coordinates"][0][-1]


# ------------------------------------------------------------------ bundles


def test_every_monitor_can_build_a_download(rectangle_field, combine):
    """The catalog and the writers must not drift apart.

    A monitor profile naming a format no writer implements would only surface
    when a producer clicked download, which is the worst time to find out.
    """
    line, _ = line_from_boundary(rectangle_field, combine)
    for key, monitor in MONITORS.items():
        if not monitor.support.is_downloadable:
            continue
        result = build_download(key, rectangle_field, [line], machine=combine)
        assert result.data[:2] == b"PK", f"{key} did not produce a zip"
        with zipfile.ZipFile(io.BytesIO(result.data)) as archive:
            names = archive.namelist()
            assert "HOW-TO-IMPORT.txt" in names, f"{key} has no instruction sheet"
            assert len(names) > 1, f"{key} produced instructions and nothing else"


def test_isoxml_bundle_has_taskdata_at_the_expected_path(rectangle_field, combine):
    line, _ = line_from_boundary(rectangle_field, combine)
    result = build_download("generic.isobus", rectangle_field, [line], machine=combine)
    with zipfile.ZipFile(io.BytesIO(result.data)) as archive:
        assert "TASKDATA/TASKDATA.XML" in archive.namelist()
        # And it must survive a trip back through the reader.
        fields, lines, _ = parse_taskdata(archive.read("TASKDATA/TASKDATA.XML"))
        assert len(lines) == 1


def test_raven_bundle_uses_the_documented_folder_tree(rectangle_field, combine):
    line, _ = line_from_boundary(rectangle_field, combine)
    result = build_download("raven.viper4", rectangle_field, [line], machine=combine)
    with zipfile.ZipFile(io.BytesIO(result.data)) as archive:
        names = archive.namelist()
        assert any(n.startswith("Raven/GFF/") for n in names)
        assert any("/abLines/" in n for n in names)
    # The unverified support level must be surfaced, not buried.
    assert any("unverified" in note for note in result.notes)


def test_precision_planting_bundle_uses_sendto2020(rectangle_field, combine):
    line, _ = line_from_boundary(rectangle_field, combine)
    result = build_download(
        "precision_planting.2020", rectangle_field, [line], machine=combine
    )
    with zipfile.ZipFile(io.BytesIO(result.data)) as archive:
        assert any(n.startswith("SendTo2020/") for n in archive.namelist())


def test_desktop_bridge_download_says_so_plainly(rectangle_field, combine):
    line, _ = line_from_boundary(rectangle_field, combine)
    result = build_download("john_deere.gen4", rectangle_field, [line], machine=combine)
    assert any("closed" in note for note in result.notes)
    with zipfile.ZipFile(io.BytesIO(result.data)) as archive:
        sheet = archive.read("HOW-TO-IMPORT.txt").decode()
    assert "TWO-STEP" in sheet
    assert "Operations Center" in sheet


def test_download_refuses_an_invalid_line(rectangle_field, combine):
    broken = GuidanceLine(
        name="Broken", pattern=PatternType.AB, points=[], swath_width_m=12.0
    )
    with pytest.raises(ValueError, match="cannot export"):
        build_download("generic.isobus", rectangle_field, [broken], machine=combine)


def test_download_refuses_an_empty_selection(rectangle_field, combine):
    with pytest.raises(ValueError, match="no guidance lines selected"):
        build_download("generic.isobus", rectangle_field, [], machine=combine)


def test_download_rejects_a_format_the_monitor_does_not_offer(rectangle_field, combine):
    line, _ = line_from_boundary(rectangle_field, combine)
    with pytest.raises(ValueError, match="not offered"):
        build_download(
            "generic.isobus", rectangle_field, [line],
            machine=combine, format_key="raven_gff",
        )


def test_unknown_monitor_key_is_a_clear_error(rectangle_field, combine):
    line, _ = line_from_boundary(rectangle_field, combine)
    with pytest.raises(KeyError, match="unknown monitor"):
        build_download("acme.tractotron", rectangle_field, [line], machine=combine)


# ------------------------------------------------------------- reader entry


def test_read_any_detects_a_zipped_shapefile(rectangle_field, combine):
    line, _ = line_from_boundary(rectangle_field, combine)
    files = build_format("shapefile", rectangle_field, [line], machine=combine)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, blob in files.items():
            archive.writestr(name, blob)

    result = read_any("export.zip", buffer.getvalue())
    assert result.detected_format == "shapefile"
    assert len(result.lines) == 1
    assert len(result.fields) == 1
    assert result.lines[0].swath_width_m == pytest.approx(combine.effective_width_m)


def test_read_any_detects_isoxml_in_a_zip(rectangle_field, combine):
    line, _ = line_from_boundary(rectangle_field, combine)
    result_zip = build_download(
        "generic.isobus", rectangle_field, [line], machine=combine,
        include_fallbacks=False,
    )
    result = read_any("TASKDATA.zip", result_zip.data)
    assert result.detected_format == "isoxml"
    assert len(result.lines) == 1


def test_read_any_reads_a_track_log():
    csv_text = "Latitude,Longitude,Heading,Recording\n"
    csv_text += "".join(
        f"-27.84{i:02d},-54.4800,90.0,1\n" for i in range(10)
    )
    result = read_any("aslogged.csv", csv_text.encode())
    assert result.detected_format == "track_log"
    assert len(result.track) == 10
    assert result.track[0].recording is True


def test_read_any_rejects_something_unreadable():
    with pytest.raises(ValueError, match="unrecognised file"):
        read_any("mystery.bin", b"\x00\x01\x02\x03binary nonsense\xff\xfe")


def test_read_any_reads_geojson_we_wrote(rectangle_field, combine):
    line, _ = line_from_boundary(rectangle_field, combine)
    blob = build_geojson(rectangle_field, [line], machine=combine)
    result = read_any("lines.geojson", blob)
    assert len(result.lines) == 1
    assert len(result.fields) == 1
    assert result.lines[0].swath_width_m == pytest.approx(combine.effective_width_m)


def test_read_any_reads_kml_we_wrote(rectangle_field, combine):
    line, _ = line_from_boundary(rectangle_field, combine)
    blob = build_kml(rectangle_field, [line], machine=combine)
    result = read_any("lines.kml", blob)
    assert len(result.lines) == 1
    assert len(result.fields) == 1


def test_catalog_support_levels_are_consistent():
    """Downloadable monitors need a real format; API-only ones must not claim one."""
    from ofpe.catalog import FORMATS

    for key, monitor in MONITORS.items():
        assert monitor.primary_format in FORMATS, f"{key} names an unknown format"
        for extra in monitor.also_offer:
            assert extra in FORMATS, f"{key} offers unknown format {extra}"
        if monitor.support is not SupportLevel.API_ONLY:
            assert monitor.steps, f"{key} is downloadable but has no import steps"
            assert monitor.sources or monitor.brand == "Generic", (
                f"{key} makes claims with no source recorded"
            )
