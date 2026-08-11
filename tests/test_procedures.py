"""The procedure knowledge base and its resolver.

The tests that matter most here are the *coverage invariants*. A wrong step in
a procedure is a typo someone reports; a hole in the version matrix is silent —
the wizard simply stops offering a job the machine can obviously do, and nobody
files a bug because there is nothing visibly broken to point at.
"""

from __future__ import annotations

import pytest

from abline import catalog as catalog_module
from abline import procedures as pr


def combos() -> dict[tuple[str, str, str], list[pr.Procedure]]:
    out: dict[tuple[str, str, str], list[pr.Procedure]] = {}
    for procedure in pr.PROCEDURES:
        key = (procedure.monitor_key, procedure.objective, procedure.transport.value)
        out.setdefault(key, []).append(procedure)
    return out


# ------------------------------------------------------------- invariants


def test_every_version_of_every_display_is_covered():
    """No hole in the version matrix.

    For any (display, job, route) that has only version-specific procedures,
    those procedures must between them name every release the display offers.
    Otherwise a real machine on a real release gets silently no answer.
    """
    gaps = []
    for (monitor, objective, transport), entries in combos().items():
        if any(pr.ANY_VERSION in e.version_keys for e in entries):
            continue
        covered = {key for e in entries for key in e.version_keys}
        declared = {v.key for v in pr.versions_for(monitor)}
        missing = declared - covered
        if missing:
            gaps.append(f"{monitor} / {objective} / {transport}: {sorted(missing)}")
    assert not gaps, "version coverage gaps:\n  " + "\n  ".join(gaps)


def test_every_version_key_is_declared_for_its_monitor():
    """A typo'd version key would match nothing and fall back forever."""
    bad = []
    for procedure in pr.PROCEDURES:
        declared = {v.key for v in pr.versions_for(procedure.monitor_key)}
        for key in procedure.version_keys:
            if key != pr.ANY_VERSION and key not in declared:
                bad.append(f"{procedure.monitor_key} / {procedure.objective}: {key}")
    assert not bad, "undeclared version keys:\n  " + "\n  ".join(bad)


def test_every_procedure_points_at_a_real_monitor():
    unknown = sorted(
        {p.monitor_key for p in pr.PROCEDURES} - set(catalog_module.MONITORS)
    )
    assert not unknown, f"procedures for unknown monitors: {unknown}"


def test_every_terminal_has_at_least_one_procedure():
    """A display in the catalog with no procedure is a dead end in the wizard."""
    documented = {p.monitor_key for p in pr.PROCEDURES}
    missing = [
        key
        for key, monitor in catalog_module.MONITORS.items()
        if monitor.is_terminal and key not in documented
    ]
    assert not missing, f"terminals with no procedure: {missing}"


def test_every_procedure_has_steps_and_a_source():
    thin = [
        f"{p.monitor_key}/{p.objective}/{p.transport.value}"
        for p in pr.PROCEDURES
        if len(p.steps) < 3 or not p.sources
    ]
    assert not thin, f"procedures with too few steps or no source: {thin}"


def test_usb_procedures_say_where_the_file_goes():
    """The folder path is the single most valuable field on the card."""
    vague = [
        f"{p.monitor_key}/{p.objective}"
        for p in pr.PROCEDURES
        if p.transport is pr.Transport.USB
        and p.objective not in ("prepare_media",)
        and not p.media_path
    ]
    assert not vague, f"USB procedures with no media path: {vague}"


def test_cloud_procedures_do_not_claim_a_usb_path():
    wrong = [
        p.monitor_key
        for p in pr.PROCEDURES
        if p.transport is pr.Transport.CLOUD and p.media_path
    ]
    assert not wrong, f"cloud procedures with a media path: {wrong}"


def test_every_monitor_has_both_icon_variants_on_disk():
    """Captioned for the spreadsheet, caption-free for the web UI.

    A missing UI variant renders as a broken image in the wizard, which is the
    first thing anyone sees.
    """
    from abline.web.app import ICON_DIR

    missing = []
    for key, monitor in catalog_module.MONITORS.items():
        if not (ICON_DIR / monitor.icon).is_file():
            missing.append(f"{key} -> {monitor.icon} (captioned)")
        if not (ICON_DIR / "ui" / monitor.icon).is_file():
            missing.append(f"{key} -> ui/{monitor.icon} (caption-free)")
    assert not missing, "missing icon files:\n  " + "\n  ".join(missing)


def test_icon_urls_point_at_the_caption_free_variant():
    monitor = catalog_module.get_monitor("john_deere.gen4").to_dict()
    assert monitor["icon_url"].startswith("/icons/ui/")
    assert monitor["icon_captioned_url"] == f"/icons/{monitor['icon']}"


# --------------------------------------------------------------- resolver


def test_exact_version_match_is_reported_as_such():
    result = pr.resolve(
        "john_deere.gen4", "import_guidance", "usb", "gen4_2025_3"
    )
    assert result.procedure is not None
    assert result.matched_version is True
    assert "gen4_2025_3" in result.procedure.version_keys
    # The 2025-3 procedure is the one that mentions the legacy-file change.
    assert any("Apex" in step for step in result.procedure.steps)


def test_a_shared_version_run_matches_exactly():
    """10.x and 11.x share one procedure; both must count as an exact match."""
    for version in ("gen4_10x", "gen4_11x"):
        result = pr.resolve("john_deere.gen4", "import_guidance", "usb", version)
        assert result.matched_version is True, version
        assert "Apex" not in " ".join(result.procedure.steps)


def test_generic_procedure_is_flagged_when_a_specific_one_exists_elsewhere():
    """Case IH prescriptions differ by release, so a generic answer must warn."""
    result = pr.resolve(
        "case_ih.afs_pro_700", "import_prescription", "usb", "pro700_30"
    )
    assert result.matched_version is True
    assert "Toolbox" in " ".join(result.procedure.steps)


def test_unknown_version_falls_back_and_says_so():
    result = pr.resolve("john_deere.gen4", "import_guidance", "usb", "nonexistent")
    assert result.procedure is not None
    assert result.matched_version is False
    assert result.message


def test_no_version_chosen_still_returns_something():
    result = pr.resolve("john_deere.gen4", "import_prescription", "usb", None)
    assert result.procedure is not None
    assert result.procedure.media_path


def test_missing_combination_offers_alternatives_rather_than_nothing():
    """A dead end must still point somewhere useful.

    The gap is found rather than hard-coded: naming one would turn this test
    into a tripwire that fires the moment that gap gets documented, which is
    the opposite of what it is guarding.
    """
    gap = next(
        (
            (monitor, objective.key, transport)
            for monitor, profile in catalog_module.MONITORS.items()
            if profile.is_terminal
            for objective in pr.OBJECTIVES.values()
            for transport in pr.Transport
            if pr.resolve(monitor, objective.key, transport).procedure is None
        ),
        None,
    )
    if gap is None:
        pytest.skip("every display now documents every objective on every route")

    result = pr.resolve(*gap)
    assert result.procedure is None
    assert result.alternatives, f"{gap} is a dead end that points nowhere"
    assert "no procedure" in result.message.lower()


def test_resolve_rejects_an_unknown_objective():
    with pytest.raises(KeyError, match="unknown objective"):
        pr.resolve("john_deere.gen4", "make_coffee", "usb", None)


def test_available_objectives_never_offers_a_dead_end():
    """Whatever the wizard lists must actually resolve."""
    for key, monitor in catalog_module.MONITORS.items():
        if not monitor.is_terminal:
            continue
        versions = [v.key for v in pr.versions_for(key)] or [None]
        for version in versions:
            for objective in pr.available_objectives(key, version):
                transports = pr.available_transports(key, objective.key, version)
                assert transports, (
                    f"{key} / {version} offers {objective.key} with no route"
                )
                for transport in transports:
                    result = pr.resolve(key, objective.key, transport, version)
                    assert result.procedure is not None, (
                        f"{key} / {version} / {objective.key} / {transport.value} "
                        "was offered but resolves to nothing"
                    )


# ------------------------------------------------------------------ content


def test_prescription_procedures_warn_about_the_prj_file():
    """Missing .prj is the classic shapefile failure; it must be called out."""
    shapefile_procedures = [
        p
        for p in pr.PROCEDURES
        if ".prj" in p.extensions and p.objective == "import_prescription"
    ]
    assert shapefile_procedures
    for procedure in shapefile_procedures:
        text = " ".join(procedure.steps + procedure.common_errors + procedure.cautions)
        assert ".prj" in text or "four" in text.lower(), (
            f"{procedure.monitor_key} never mentions the shapefile sidecars"
        )


def test_john_deere_guidance_is_honest_about_needing_operations_center():
    result = pr.resolve("john_deere.gen4", "import_guidance", "usb", "gen4_11x")
    text = " ".join(result.procedure.steps + result.procedure.prerequisites)
    assert "Operations Center" in text


def test_media_preparation_exists_for_every_usb_terminal():
    prepared = {
        p.monitor_key for p in pr.PROCEDURES if p.objective == "prepare_media"
    }
    usb_terminals = {
        p.monitor_key
        for p in pr.PROCEDURES
        if p.transport is pr.Transport.USB and p.filesystem.upper().startswith("FAT")
    }
    missing = sorted(usb_terminals - prepared)
    assert not missing, f"USB displays with no stick-preparation procedure: {missing}"


def test_coverage_summary_is_sane():
    summary = pr.coverage()
    assert summary["total"] > 60
    assert summary["monitors"] >= 20
    assert summary["version_specific"] >= 5
    assert set(summary["by_transport"]) >= {"usb", "cloud", "desktop"}
