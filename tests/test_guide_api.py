"""The guide's HTTP surface: wizard, coverage, handbook, deep links.

The wizard's contract is that it never offers a choice that leads nowhere. Most
of these tests are about that promise rather than about response shapes.
"""

from __future__ import annotations

import pytest

from ofpe import procedures as pr


def test_start_returns_everything_step_one_needs(client):
    body = client.get("/api/guide/start").json()
    assert body["equipment_types"], "no equipment types to choose from"
    for kind in body["equipment_types"]:
        assert kind["monitor_count"] > 0, f"{kind['key']} listed with no displays"
    assert body["objectives"]
    assert len(body["directions"]) == 3
    assert body["coverage"]["total"] > 200


def test_monitors_filter_by_equipment_and_brand(client):
    planters = client.get("/api/guide/monitors", params={"equipment": "planter"}).json()
    assert planters
    assert all("planter" in m["equipment"] for m in planters)

    deere = client.get("/api/guide/monitors", params={"brand": "John Deere"}).json()
    assert deere and all(m["brand"] == "John Deere" for m in deere)

    both = client.get(
        "/api/guide/monitors", params={"equipment": "planter", "brand": "Ag Leader"}
    ).json()
    assert all(m["brand"] == "Ag Leader" for m in both)


def test_office_software_is_not_offered_as_a_display(client):
    """QGIS is a legitimate export target but has no menus to walk through."""
    everything = client.get("/api/guide/monitors").json()
    assert "generic.gis" not in {m["key"] for m in everything}


def test_every_monitor_card_carries_an_icon(client):
    for monitor in client.get("/api/guide/monitors").json():
        assert monitor["icon_url"].startswith("/icons/ui/")
        assert client.get(monitor["icon_url"]).status_code == 200


def test_objectives_are_grouped_by_direction(client):
    body = client.get(
        "/api/guide/monitors/case_ih.afs_pro_1200/objectives"
    ).json()
    directions = [g["direction"] for g in body["groups"]]
    assert "to_monitor" in directions and "from_monitor" in directions
    for group in body["groups"]:
        for objective in group["objectives"]:
            assert objective["transports"], (
                f"{objective['key']} offered with no route"
            )


def test_nothing_offered_by_the_api_leads_to_a_dead_end(client):
    """The promise the wizard makes, checked over the whole catalog."""
    for monitor in client.get("/api/guide/monitors").json():
        versions = [v["key"] for v in monitor["versions"]] or [None]
        for version in versions:
            params = {"version": version} if version else {}
            body = client.get(
                f"/api/guide/monitors/{monitor['key']}/objectives", params=params
            ).json()
            for group in body["groups"]:
                for objective in group["objectives"]:
                    for transport in objective["transports"]:
                        query = {
                            "monitor_key": monitor["key"],
                            "objective": objective["key"],
                            "transport": transport["key"],
                        }
                        if version:
                            query["version"] = version
                        result = client.get("/api/guide/procedure", params=query).json()
                        assert result["found"], (
                            f"{monitor['key']}/{version}/{objective['key']}/"
                            f"{transport['key']} was offered but resolves to nothing"
                        )


def test_procedure_reports_an_exact_version_match(client):
    body = client.get("/api/guide/procedure", params={
        "monitor_key": "john_deere.gen4",
        "objective": "import_guidance",
        "transport": "usb",
        "version": "gen4_2025_3",
    }).json()
    assert body["found"] and body["matched_version"]
    assert body["version_label"] == "2025-3 update or newer"
    assert any("Apex" in step for step in body["procedure"]["steps"])


def test_procedure_offers_related_next_steps(client):
    body = client.get("/api/guide/procedure", params={
        "monitor_key": "case_ih.afs_pro_1200",
        "objective": "import_prescription",
        "transport": "usb",
    }).json()
    assert body["related"], "a procedure with no suggested next step"
    assert all(r["objective"] != "import_prescription" for r in body["related"])
    # Ordered as a workflow: preparation before the job, records after it.
    from ofpe.procedures._core import _RELATED_ORDER

    keys = [r["objective"] for r in body["related"]]
    assert keys == sorted(keys, key=_RELATED_ORDER.index)


def test_cloud_procedures_name_the_platform(client):
    body = client.get("/api/guide/procedure", params={
        "monitor_key": "ag_leader.incommand",
        "objective": "export_work_data",
        "transport": "cloud",
    }).json()
    assert body["found"]
    assert body["procedure"]["platform"] == "AgFiniti"
    assert not body["procedure"]["media_path"], "a cloud route has no folder"


def test_unknown_monitor_is_a_404(client):
    assert client.get("/api/guide/monitors/nope/objectives").status_code == 404
    assert client.get("/api/guide/procedure", params={
        "monitor_key": "nope", "objective": "import_guidance", "transport": "usb",
    }).status_code == 404


def test_unknown_objective_is_a_422(client):
    response = client.get("/api/guide/procedure", params={
        "monitor_key": "john_deere.gen4",
        "objective": "make_coffee",
        "transport": "usb",
    })
    assert response.status_code == 422
    assert "unknown objective" in response.json()["detail"]


def test_search_finds_displays_by_the_names_people_use(client):
    for needle, expected in [
        ("2630", "john_deere.gs3_2630"),
        ("Pro 700", "case_ih.afs_pro_700"),
        ("CEMIS", "claas.cemis_1200"),
        ("Viper", "raven.viper4"),
        ("TRACK-Leader", "mueller.track_leader"),
    ]:
        hits = client.get("/api/guide/search", params={"q": needle}).json()
        assert expected in {m["key"] for m in hits}, f"{needle!r} did not find it"


def test_search_ignores_a_too_short_query(client):
    assert client.get("/api/guide/search", params={"q": "a"}).json() == []


# ----------------------------------------------------------------- coverage


def test_coverage_reports_the_work_queue(client):
    body = client.get("/api/guide/coverage").json()
    assert body["summary"]["total"] > 200
    assert body["monitors"]
    assert len(body["cloud_platforms"]) >= 10

    for monitor in body["monitors"]:
        documented = {o for o in monitor["missing"]}
        assert monitor["objectives"] + len(documented) == monitor["objectives_possible"]
        assert monitor["transports"], f"{monitor['key']} has no route at all"


def test_coverage_is_sorted_most_complete_first(client):
    counts = [m["objectives"] for m in client.get("/api/guide/coverage").json()["monitors"]]
    assert counts == sorted(counts, reverse=True)


# ----------------------------------------------------------------- handbook


def test_handbook_renders_every_procedure_for_a_display(client):
    response = client.get("/handbook", params={
        "monitor_key": "case_ih.afs_pro_700", "version": "pro700_30",
    })
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    html = response.text
    assert "Case IH AFS Pro 700" in html
    assert "Version 30.x or newer" in html

    expected = sum(
        len(pr.available_transports(
            "case_ih.afs_pro_700", objective.key, "pro700_30"))
        for objective in pr.available_objectives("case_ih.afs_pro_700", "pro700_30")
    )
    assert html.count("procsteps") == expected


def test_handbook_escapes_content_rather_than_injecting_it(client):
    """Procedure text is ours, but it still goes through escaping."""
    html = client.get("/handbook", params={"monitor_key": "raven.viper4"}).text
    # Backslashes in Windows paths must survive; angle brackets must not appear
    # unescaped from data.
    assert "Raven\\GFF" in html
    assert "<script" not in html.lower().replace('<script src="/static', "")


def test_handbook_for_an_unknown_display_is_a_404(client):
    assert client.get("/handbook", params={"monitor_key": "nope"}).status_code == 404


def test_handbook_without_a_version_says_so(client):
    html = client.get("/handbook", params={"monitor_key": "generic.isobus"}).text
    assert "All software versions" in html


# -------------------------------------------------------------- corrections


def test_report_kinds_are_offered(client):
    kinds = client.get("/api/guide/report-kinds").json()
    assert {k["key"] for k in kinds} >= {"menu_name", "folder", "did_not_work"}
    assert all(k["label"] for k in kinds)


def test_a_correction_can_be_filed_and_shows_up_in_the_queue(client):
    response = client.post("/api/guide/report", json={
        "monitor_key": "john_deere.gen4",
        "objective": "import_guidance",
        "transport": "usb",
        "version_key": "gen4_11x",
        "kind": "menu_name",
        "step_number": 5,
        "actual_text": 'The menu is called "Data Manager" on 11.x',
        "reporter": "Gilberto",
    })
    assert response.status_code == 201, response.text

    queue = client.get("/api/guide/reports").json()
    assert queue["counts"]["new"] == 1
    report = queue["reports"][0]
    # Enriched server-side so the operations list needs no second lookup.
    assert report["monitor_label"].startswith("John Deere")
    assert report["objective_label"] == "Load guidance lines (AB / curves)"
    assert report["version_label"] == "Gen 4 OS 11.x"
    assert report["kind_label"] == "The menu was called something else"
    assert report["step_number"] == 5


def test_a_report_with_no_detail_is_refused(client):
    """A report nobody can act on is worse than none: it looks like signal."""
    response = client.post("/api/guide/report", json={
        "monitor_key": "john_deere.gen4",
        "objective": "import_guidance",
        "transport": "usb",
        "kind": "menu_name",
    })
    assert response.status_code == 422
    assert "what actually happened" in response.json()["detail"]


def test_confirming_a_procedure_works_needs_no_detail(client):
    """'It worked' is valuable and must not be gated behind a text box."""
    response = client.post("/api/guide/report", json={
        "monitor_key": "case_ih.afs_pro_700",
        "objective": "import_prescription",
        "transport": "usb",
        "kind": "worked_fine",
    })
    assert response.status_code == 201


def test_reports_reject_unknown_targets(client):
    base = {
        "monitor_key": "john_deere.gen4",
        "objective": "import_guidance",
        "transport": "usb",
        "kind": "menu_name",
        "actual_text": "something",
    }
    assert client.post("/api/guide/report",
                       json={**base, "monitor_key": "nope"}).status_code == 404
    assert client.post("/api/guide/report",
                       json={**base, "objective": "nope"}).status_code == 422
    assert client.post("/api/guide/report",
                       json={**base, "kind": "nope"}).status_code == 422


def test_a_report_can_be_marked_fixed(client):
    client.post("/api/guide/report", json={
        "monitor_key": "raven.viper4", "objective": "import_guidance",
        "transport": "usb", "kind": "did_not_work", "actual_text": "nothing listed",
    })
    report_id = client.get("/api/guide/reports").json()["reports"][0]["id"]

    assert client.post(f"/api/guide/reports/{report_id}/status",
                       params={"status": "fixed"}).status_code == 200
    counts = client.get("/api/guide/reports").json()["counts"]
    assert counts.get("new", 0) == 0 and counts["fixed"] == 1

    assert client.post(f"/api/guide/reports/{report_id}/status",
                       params={"status": "banana"}).status_code == 422
    assert client.post("/api/guide/reports/nope/status",
                       params={"status": "fixed"}).status_code == 404


def test_open_reports_surface_in_health(client):
    assert client.get("/api/health").json()["open_reports"] == 0
    client.post("/api/guide/report", json={
        "monitor_key": "topcon.x_family", "objective": "export_work_data",
        "transport": "usb", "kind": "folder", "actual_text": "went elsewhere",
    })
    assert client.get("/api/health").json()["open_reports"] == 1


def test_reports_can_be_filtered_by_status(client):
    for kind in ("menu_name", "folder"):
        client.post("/api/guide/report", json={
            "monitor_key": "claas.cemis_1200", "objective": "import_guidance",
            "transport": "usb", "kind": kind, "actual_text": "detail",
        })
    reports = client.get("/api/guide/reports").json()["reports"]
    client.post(f"/api/guide/reports/{reports[0]['id']}/status",
                params={"status": "reviewed"})

    assert len(client.get("/api/guide/reports",
                          params={"status": "new"}).json()["reports"]) == 1
    assert len(client.get("/api/guide/reports",
                          params={"status": "reviewed"}).json()["reports"]) == 1
