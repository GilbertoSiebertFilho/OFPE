"""The HTTP surface, including the producer flow end to end."""

from __future__ import annotations

import io
import zipfile

import pytest

RECTANGLE = [[
    [-27.8400, -54.4850],
    [-27.8400, -54.4700],
    [-27.8490, -54.4700],
    [-27.8490, -54.4850],
]]


def make_machine(client, **overrides):
    payload = {
        "name": "S780 combine",
        "brand": "John Deere",
        "category": "combine",
        "working_width_m": 12.0,
        "monitor_key": "john_deere.gen4",
    }
    payload.update(overrides)
    response = client.post("/api/machines", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def make_field(client, **overrides):
    payload = {"name": "Talhao Norte", "farm": "Fazenda", "boundary": RECTANGLE}
    payload.update(overrides)
    response = client.post("/api/fields", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_health_reports_counts(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["machines"] == 0 and body["fields"] == 0


def test_catalog_lists_monitors_and_formats(client):
    body = client.get("/api/catalog/monitors").json()
    assert len(body["monitors"]) >= 15
    assert "John Deere" in body["brands"]
    keys = {m["key"] for m in body["monitors"]}
    assert {"john_deere.gen4", "case_ih.afs_pro_700", "generic.isobus"} <= keys
    for monitor in body["monitors"]:
        assert monitor["support_headline"]
        assert isinstance(monitor["downloadable"], bool)


def test_unknown_monitor_is_a_404(client):
    assert client.get("/api/catalog/monitors/acme.nope").status_code == 404


def test_machine_crud(client):
    machine = make_machine(client)
    assert machine["effective_width_m"] == pytest.approx(12.0)

    listing = client.get("/api/machines").json()
    assert len(listing) == 1

    assert client.delete(f"/api/machines/{machine['id']}").status_code == 204
    assert client.get("/api/machines").json() == []
    assert client.delete(f"/api/machines/{machine['id']}").status_code == 404


def test_machine_rejects_overlap_wider_than_the_header(client):
    response = client.post("/api/machines", json={
        "name": "Bad", "working_width_m": 6.0, "overlap_m": 6.0,
    })
    assert response.status_code == 422
    assert "smaller than the working width" in response.json()["detail"]


def test_machine_rejects_an_unknown_display(client):
    response = client.post("/api/machines", json={
        "name": "Bad", "working_width_m": 6.0, "monitor_key": "acme.nope",
    })
    assert response.status_code == 422
    assert "unknown monitor" in response.json()["detail"]


def test_field_rejects_an_out_of_range_latitude(client):
    """A longitude past +/-90 in the latitude slot is caught, not stored.

    This is the detectable half of coordinate swapping. A swap where both
    values happen to fall inside +/-90 -- which is the case for most of Europe
    and much of Brazil -- is indistinguishable from a real position and cannot
    be rejected here; the map preview is what catches those.
    """
    response = client.post("/api/fields", json={
        "name": "Swapped",
        "boundary": [[[-154.48, -27.84], [-154.47, -27.84], [-154.47, -27.85]]],
    })
    assert response.status_code == 422
    assert "out of range" in response.json()["detail"]
    assert "swapped" in response.json()["detail"]


def test_field_rejects_a_two_point_ring(client):
    response = client.post("/api/fields", json={
        "name": "Sliver", "boundary": [[[-27.84, -54.48], [-27.85, -54.47]]],
    })
    assert response.status_code == 422
    assert "at least 3 points" in response.json()["detail"]


def test_generate_from_boundary_returns_the_heading_it_chose(client):
    machine = make_machine(client)
    field = make_field(client)

    response = client.post("/api/lines/from-boundary", json={
        "field_id": field["id"], "machine_id": machine["id"], "headland_passes": 2,
    })
    assert response.status_code == 201, response.text
    body = response.json()
    assert len(body["lines"]) == 2  # the AB line plus the headland
    assert body["heading"]["pass_count"] > 50
    assert body["heading"]["heading_deg"] % 180 == pytest.approx(90.0, abs=2.0)
    assert body["heading"]["headings_considered"] > 100


def test_generate_needs_a_boundary(client):
    machine = make_machine(client)
    field = make_field(client, name="No boundary", boundary=[])
    response = client.post("/api/lines/from-boundary", json={
        "field_id": field["id"], "machine_id": machine["id"],
    })
    assert response.status_code == 422
    assert "has no boundary" in response.json()["detail"]


def test_heading_endpoint_scores_without_saving(client):
    machine = make_machine(client)
    field = make_field(client)
    response = client.get(
        f"/api/fields/{field['id']}/heading",
        params={"machine_id": machine["id"], "strategy": "longest_edge"},
    )
    assert response.status_code == 200
    assert response.json()["strategy"] == "longest_edge"
    assert client.get(f"/api/lines?field_id={field['id']}").json() == []


def test_manual_ab_line_and_preview(client):
    machine = make_machine(client)
    field = make_field(client)

    response = client.post("/api/lines", json={
        "field_id": field["id"],
        "machine_id": machine["id"],
        "name": "Hand drawn",
        "pattern": "AB",
        "points": [[-27.8410, -54.4840], [-27.8410, -54.4710]],
    })
    assert response.status_code == 201, response.text
    line = response.json()
    assert line["heading_deg"] == pytest.approx(90.0, abs=0.5)

    preview = client.get(f"/api/lines/{line['id']}/preview").json()
    assert preview["swaths"]["swath_count"] > 50
    assert preview["swaths"]["covered_ha"] > 100


def test_manual_line_rejects_two_identical_points(client):
    machine = make_machine(client)
    field = make_field(client)
    response = client.post("/api/lines", json={
        "field_id": field["id"], "machine_id": machine["id"], "pattern": "AB",
        "points": [[-27.8410, -54.4840], [-27.8410, -54.4840]],
    })
    assert response.status_code == 422
    assert "GNSS noise" in response.json()["detail"]


def test_manual_line_without_machine_or_width_is_refused(client):
    field = make_field(client)
    response = client.post("/api/lines", json={
        "field_id": field["id"], "pattern": "AB",
        "points": [[-27.8410, -54.4840], [-27.8410, -54.4710]],
    })
    assert response.status_code == 422
    assert "swath width" in response.json()["detail"]


def test_pivot_needs_a_radius(client):
    machine = make_machine(client)
    field = make_field(client)
    response = client.post("/api/lines", json={
        "field_id": field["id"], "machine_id": machine["id"], "pattern": "PIVOT",
        "points": [[-27.8445, -54.4775]],
    })
    assert response.status_code == 422


def test_import_geojson_and_persist(client):
    machine = make_machine(client)
    payload = (
        '{"type":"FeatureCollection","features":[{"type":"Feature",'
        '"properties":{"name":"Imported field"},"geometry":{"type":"Polygon",'
        '"coordinates":[[[-54.485,-27.840],[-54.470,-27.840],'
        '[-54.470,-27.849],[-54.485,-27.849],[-54.485,-27.840]]]}},'
        '{"type":"Feature","properties":{"name":"Imported AB","pattern":"AB"},'
        '"geometry":{"type":"LineString","coordinates":'
        '[[-54.484,-27.841],[-54.471,-27.841]]}}]}'
    )
    response = client.post(
        "/api/import",
        files={"file": ("field.geojson", payload.encode(), "application/geo+json")},
        data={"persist": "true", "machine_id": machine["id"]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["detected_format"] == "geojson"
    assert body["persisted"] == {"fields": 1, "lines": 1}

    # The line carried no width, so it must have taken the machine's.
    lines = client.get("/api/lines").json()
    assert lines[0]["swath_width_m"] == pytest.approx(12.0)


def test_import_rejects_an_empty_upload(client):
    response = client.post("/api/import", files={"file": ("empty.csv", b"")})
    assert response.status_code == 422
    assert "empty" in response.json()["detail"]


def test_import_rejects_a_file_it_cannot_read(client):
    response = client.post(
        "/api/import", files={"file": ("junk.bin", b"\x00\x01\x02notafile\xff")}
    )
    assert response.status_code == 422
    assert "unrecognised file" in response.json()["detail"]


def test_fit_endpoint_from_a_csv_track(client):
    import math

    from ofpe.geo import LatLon, LocalFrame

    machine = make_machine(client)
    field = make_field(client)

    frame = LocalFrame(LatLon(-27.845, -54.477))
    rows = ["latitude,longitude,recording"]
    for pass_index in range(6):
        for step in range(101):
            x = step * 6.0
            y = pass_index * 12.0
            point = frame.to_latlon(x, y)
            rows.append(f"{point.lat:.8f},{point.lon:.8f},1")
    csv_bytes = "\n".join(rows).encode()

    response = client.post(
        "/api/fit",
        files={"file": ("aslogged.csv", csv_bytes, "text/csv")},
        data={
            "machine_id": machine["id"],
            "field_id": field["id"],
            "name": "Fitted",
            "persist": "true",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["pass_count"] == 6
    assert body["estimated_width_m"] == pytest.approx(12.0, abs=0.2)
    assert body["confidence"] == "high"
    assert body["persisted"] is True
    # The passes run due east, so the heading modulo 180 is 90.
    assert body["diagnostics"]["dominant_heading_deg"] % 180 == pytest.approx(90.0, abs=0.5)
    assert math.isclose(body["line"]["swath_width_m"], 12.0)


def test_fit_rejects_a_file_with_no_track(client):
    machine = make_machine(client)
    payload = b'{"type":"FeatureCollection","features":[]}'
    response = client.post(
        "/api/fit",
        files={"file": ("nothing.geojson", payload)},
        data={"machine_id": machine["id"]},
    )
    assert response.status_code == 422
    assert "no track points" in response.json()["detail"]


# ------------------------------------------------------------ producer flow


def test_producer_catalog_joins_the_monitor_profile(client):
    machine = make_machine(client)
    field = make_field(client)
    client.post("/api/lines/from-boundary", json={
        "field_id": field["id"], "machine_id": machine["id"],
    })

    body = client.get("/api/producer/catalog").json()
    assert len(body["machines"]) == 1
    entry = body["machines"][0]
    assert entry["machine_name"] == "S780 combine"
    assert entry["monitor"]["key"] == "john_deere.gen4"
    assert entry["monitor"]["support"] == "desktop_bridge"
    assert entry["monitor"]["steps"]
    assert len(entry["fields"]) == 1
    assert len(entry["fields"][0]["lines"]) == 1


def test_producer_catalog_hides_unpublished_lines(client):
    machine = make_machine(client)
    field = make_field(client)
    created = client.post("/api/lines/from-boundary", json={
        "field_id": field["id"], "machine_id": machine["id"], "publish": False,
    }).json()

    assert client.get("/api/producer/catalog").json()["machines"] == []

    line_id = created["lines"][0]["id"]
    client.post(f"/api/lines/{line_id}/publish", params={"published": True})
    assert len(client.get("/api/producer/catalog").json()["machines"]) == 1


def test_producer_catalog_flags_a_machine_with_no_display(client):
    machine = make_machine(client, monitor_key="")
    field = make_field(client)
    client.post("/api/lines/from-boundary", json={
        "field_id": field["id"], "machine_id": machine["id"],
    })
    entry = client.get("/api/producer/catalog").json()["machines"][0]
    assert entry["monitor"] is None
    assert "no display" in entry["monitor_warning"].lower()


def test_download_end_to_end_for_an_isobus_machine(client):
    machine = make_machine(client, name="Drill", monitor_key="generic.isobus",
                           working_width_m=6.0, brand="Generic")
    field = make_field(client)
    created = client.post("/api/lines/from-boundary", json={
        "field_id": field["id"], "machine_id": machine["id"],
    }).json()

    response = client.post("/api/download", json={
        "monitor_key": "generic.isobus",
        "line_ids": [created["lines"][0]["id"]],
        "machine_id": machine["id"],
    })
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "attachment" in response.headers["content-disposition"]

    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = archive.namelist()
        assert "TASKDATA/TASKDATA.XML" in names
        assert "HOW-TO-IMPORT.txt" in names
        sheet = archive.read("HOW-TO-IMPORT.txt").decode()
        assert "Drill" in sheet
        assert "6 m" in sheet


def test_download_surfaces_the_two_step_warning_in_a_header(client):
    machine = make_machine(client)  # John Deere Gen 4 -> desktop bridge
    field = make_field(client)
    created = client.post("/api/lines/from-boundary", json={
        "field_id": field["id"], "machine_id": machine["id"],
    }).json()

    response = client.post("/api/download", json={
        "monitor_key": "john_deere.gen4",
        "line_ids": [created["lines"][0]["id"]],
        "machine_id": machine["id"],
    })
    assert response.status_code == 200
    assert "closed" in response.headers["x-ofpe-notes"]


def test_download_refuses_lines_from_two_different_fields(client):
    machine = make_machine(client)
    field_a = make_field(client, name="A")
    field_b = make_field(client, name="B")
    line_a = client.post("/api/lines/from-boundary", json={
        "field_id": field_a["id"], "machine_id": machine["id"],
    }).json()["lines"][0]
    line_b = client.post("/api/lines/from-boundary", json={
        "field_id": field_b["id"], "machine_id": machine["id"],
    }).json()["lines"][0]

    response = client.post("/api/download", json={
        "monitor_key": "generic.isobus",
        "line_ids": [line_a["id"], line_b["id"]],
    })
    assert response.status_code == 422
    assert "one field" in response.json()["detail"]


def test_download_reports_a_missing_line(client):
    response = client.post("/api/download", json={
        "monitor_key": "generic.isobus", "line_ids": ["does-not-exist"],
    })
    assert response.status_code == 404


def test_deleting_a_field_removes_its_lines(client):
    machine = make_machine(client)
    field = make_field(client)
    client.post("/api/lines/from-boundary", json={
        "field_id": field["id"], "machine_id": machine["id"],
    })
    assert len(client.get("/api/lines").json()) == 1

    assert client.delete(f"/api/fields/{field['id']}").status_code == 204
    assert client.get("/api/lines").json() == []


def test_deleting_a_machine_keeps_its_lines(client):
    """The geometry is still good; it just loses the machine label."""
    machine = make_machine(client)
    field = make_field(client)
    client.post("/api/lines/from-boundary", json={
        "field_id": field["id"], "machine_id": machine["id"],
    })

    client.delete(f"/api/machines/{machine['id']}")
    lines = client.get("/api/lines").json()
    assert len(lines) == 1
    assert lines[0]["machine_id"] == ""


def test_the_version_walkthrough_reaches_the_browser(client):
    """The photos are useless if the API keeps them to itself."""
    response = client.get(
        "/api/guide/procedure",
        params={
            "monitor_key": "john_deere.gs3_2630",
            "objective": "import_prescription",
            "transport": "usb",
        },
    )
    assert response.status_code == 200
    walkthrough = response.json()["version_walkthrough"]
    assert walkthrough, "the 2630 has a photographed walk-through and did not send it"
    assert walkthrough["field"] == "Application Software Build"

    # And every image it points at must actually be served.
    for step in walkthrough["steps"]:
        for url in (step["button"], step["screen"]):
            if url:
                assert client.get(url).status_code == 200, url


def test_a_display_with_no_photos_says_so_rather_than_faking_it(client):
    response = client.get(
        "/api/guide/procedure",
        params={
            "monitor_key": "trimble.precision_iq",
            "objective": "import_prescription",
            "transport": "usb",
        },
    )
    assert response.json()["version_walkthrough"] is None
