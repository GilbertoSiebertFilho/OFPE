"""The guide's HTTP surface: wizard, coverage, handbook, deep links.

The wizard's contract is that it never offers a choice that leads nowhere. Most
of these tests are about that promise rather than about response shapes.
"""

from __future__ import annotations

import pytest

from abline import procedures as pr


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
    from abline.procedures._core import _RELATED_ORDER

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
    assert "Software 30.x or newer" in html

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
