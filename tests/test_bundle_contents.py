"""What actually lands in the producer's download.

These assert on the shipped artefact rather than on the writers in isolation.
A bundle that is technically correct but arrives with three copies of every
file, or without the instruction sheet, has still failed the person holding the
USB stick.
"""

from __future__ import annotations

import io
import zipfile

import pytest

from ofpe.catalog import MONITORS
from ofpe.generate import line_from_boundary, make_headland
from ofpe.writers import build_download


def contents(result) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(result.data)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


# Two shapefile sets in one bundle share an identical projection and encoding
# sidecar by design -- that is not duplication, it is what makes each set
# complete.
_SHARED_SIDECARS = (".prj", ".cpg")


def test_no_bundle_ships_duplicate_payloads(rectangle_field, combine):
    """Formats overlap; the producer must not receive the same bytes twice."""
    line, _ = line_from_boundary(rectangle_field, combine)
    for key, monitor in MONITORS.items():
        if not monitor.support.is_downloadable:
            continue
        files = contents(build_download(key, rectangle_field, [line], machine=combine))
        digests: dict[bytes, str] = {}
        for name, blob in files.items():
            if name.endswith(_SHARED_SIDECARS):
                continue
            assert blob not in digests, (
                f"{key}: {name} is byte-identical to {digests[blob]}"
            )
            digests[blob] = name


def test_reference_bundle_is_not_padded_with_its_own_parts(rectangle_field, combine):
    """A John Deere bundle already contains shapefile, KML and GeoJSON."""
    line, _ = line_from_boundary(rectangle_field, combine)
    files = contents(
        build_download("john_deere.gen4", rectangle_field, [line], machine=combine)
    )
    assert not any(name.startswith("alternative_formats/") for name in files)
    assert any(name.endswith(".shp") for name in files)
    assert any(name.endswith(".kml") for name in files)
    assert any(name.endswith(".geojson") for name in files)


def test_shapefile_sets_are_always_complete(rectangle_field, combine):
    """A lone .shp is the single most common reason an import shows nothing."""
    line, _ = line_from_boundary(rectangle_field, combine)
    for key, monitor in MONITORS.items():
        if not monitor.support.is_downloadable:
            continue
        files = contents(build_download(key, rectangle_field, [line], machine=combine))
        for name in files:
            if not name.endswith(".shp"):
                continue
            base = name[:-4]
            for sidecar in (".shx", ".dbf", ".prj"):
                assert base + sidecar in files, f"{key}: {name} is missing {sidecar}"


def test_instruction_sheet_names_every_file_it_ships(rectangle_field, combine):
    line, _ = line_from_boundary(rectangle_field, combine)
    files = contents(
        build_download("case_ih.afs_pro_700", rectangle_field, [line], machine=combine)
    )
    sheet = files["HOW-TO-IMPORT.txt"].decode()
    for name in files:
        if name == "HOW-TO-IMPORT.txt":
            continue
        assert name in sheet, f"{name} is in the zip but not listed in the sheet"


def test_instruction_sheet_carries_the_numbers_that_matter(rectangle_field, combine):
    line, _ = line_from_boundary(rectangle_field, combine)
    files = contents(
        build_download("generic.isobus", rectangle_field, [line], machine=combine)
    )
    sheet = files["HOW-TO-IMPORT.txt"].decode()
    assert "Talhao" in sheet or rectangle_field.name in sheet
    assert combine.name in sheet
    assert "12 m" in sheet                       # the swath the lines are spaced at
    assert "147" in sheet                        # field area
    assert "AB" in sheet                         # the pattern
    assert "before you engage" in sheet.lower()  # the pre-drive check


def test_headland_survives_the_whole_export_path(rectangle_field, combine):
    """Multi-ring geometry is the easiest thing for an exporter to flatten."""
    headland = make_headland(
        rectangle_field, width_m=combine.effective_width_m, passes=3,
        name="Headland", machine_id=combine.id,
    )
    files = contents(
        build_download("generic.isobus", rectangle_field, [headland], machine=combine)
    )
    from ofpe.readers.isoxml import parse_taskdata

    _fields, lines, warnings = parse_taskdata(files["TASKDATA/TASKDATA.XML"])
    assert warnings == []
    assert len(lines) == 3, "each headland ring must survive as its own pattern"
    for restored in lines:
        assert len(restored.points) > 3
        assert restored.swath_width_m == pytest.approx(combine.effective_width_m, abs=0.001)


def test_agopengps_bundle_has_the_files_aog_looks_for(rectangle_field, combine):
    line, _ = line_from_boundary(rectangle_field, combine)
    files = contents(
        build_download("agopengps.aog", rectangle_field, [line], machine=combine)
    )
    names = "\n".join(files)
    for expected in ("Field.txt", "Boundary.txt", "ABLines.txt", "Field.kml"):
        assert expected in names, f"AgOpenGPS bundle is missing {expected}"


def test_agopengps_coordinates_are_easting_then_northing(rectangle_field, combine):
    """The AB line's stored origin must match projecting point A ourselves.

    This pins the writer to its own stated convention. It cannot prove
    AgOpenGPS agrees -- that is why the catalog marks the format unverified --
    but it does catch a transposition creeping in later.
    """
    from ofpe.geo import LocalFrame
    from ofpe.writers.simple import build_agopengps

    line, _ = line_from_boundary(rectangle_field, combine)
    written = build_agopengps(rectangle_field, [line])

    _header, record = written["ABLines.txt"].decode().strip().split("\r\n")
    _name, heading_rad, easting, northing = record.rsplit(",", 3)

    frame = LocalFrame(rectangle_field.centroid())
    expected_x, expected_y = frame.to_xy(line.points[0])
    assert float(easting) == pytest.approx(expected_x, abs=0.01)
    assert float(northing) == pytest.approx(expected_y, abs=0.01)

    import math

    assert math.degrees(float(heading_rad)) == pytest.approx(
        line.computed_heading(), abs=0.01
    )
    # An east-west line must have a large easting offset and a small northing
    # one; a transposition would show up here as the reverse.
    assert abs(float(easting)) > abs(float(northing))


def test_every_bundle_stays_small_enough_to_email(rectangle_field, combine):
    """A bundle a producer cannot email is a bundle that does not get used."""
    line, _ = line_from_boundary(rectangle_field, combine)
    for key, monitor in MONITORS.items():
        if not monitor.support.is_downloadable:
            continue
        result = build_download(key, rectangle_field, [line], machine=combine)
        assert result.size < 2_000_000, f"{key} produced {result.size} bytes"
