"""The procedure knowledge base and its resolver.

The tests that matter most here are the *coverage invariants*. A wrong step in
a procedure is a typo someone reports; a hole in the version matrix is silent —
the wizard simply stops offering a job the machine can obviously do, and nobody
files a bug because there is nothing visibly broken to point at.
"""

from __future__ import annotations

import pathlib

import pytest

from ofpe import catalog as catalog_module
from ofpe import procedures as pr


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
    from ofpe.web.app import ICON_DIR

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


def test_every_pro_700_release_gets_the_two_stage_load():
    """The Pro 700's power-off load is the same across its software lines.

    This used to assert the opposite -- that 28.x and 30.x took different menu
    paths -- on the strength of a reconstruction rather than a source. Case IH's
    own import guide describes one procedure: stick in with the power off, files
    to internal storage, then assign them to fields on the Import2 tab. Splitting
    it by release invented a difference and sent half the fleet down a path that
    does not exist.
    """
    for version in ("pro700_28", "pro700_29", "pro700_30"):
        result = pr.resolve(
            "case_ih.afs_pro_700", "import_prescription", "usb", version
        )
        assert result.matched_version is True, version
        steps = " ".join(result.procedure.steps)
        assert "Shapefile" in steps, version
        assert "Import2" in steps, version


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


# ------------------------------------------------------- plain language


# Words a farmer standing at a machine cannot act on. They are fine in
# `cautions` and `common_errors`, where somebody debugging a problem goes
# looking -- but a step is an instruction, and an instruction you have to look
# up is not one.
#
# "FAT32" is deliberately absent: it is a word you pick out of a menu, so it is
# what the screen says rather than something to understand.
_JARGON_BANNED_IN_STEPS = [
    "MBR",
    "GPT",
    "NTFS",
    "exFAT",
    "WGS84",
    "UTM",
    "POLYGON",
    "NUMERIC",
    "partition table",
    "coordinate system",
]

# A step longer than this has stopped being an instruction and started being a
# paragraph. The explanation belongs in common_errors.
_MAX_STEP_CHARS = 180


def test_steps_avoid_words_a_producer_cannot_act_on():
    offenders = []
    for procedure in pr.PROCEDURES:
        for number, step in enumerate(procedure.steps, 1):
            for word in _JARGON_BANNED_IN_STEPS:
                if word in step:
                    offenders.append(
                        f"{procedure.monitor_key}/{procedure.objective} "
                        f"step {number}: {word!r} in {step[:70]!r}"
                    )
    assert not offenders, "jargon in steps:\n  " + "\n  ".join(sorted(set(offenders)))


def test_steps_stay_short_enough_to_follow():
    long_steps = sorted(
        {
            f"{len(step)} chars - {procedure.monitor_key}/{procedure.objective}: "
            f"{step[:60]}..."
            for procedure in pr.PROCEDURES
            for step in procedure.steps
            if len(step) > _MAX_STEP_CHARS
        }
    )
    assert not long_steps, (
        f"steps over {_MAX_STEP_CHARS} characters — move the explanation into "
        "cautions or common_errors:\n  " + "\n  ".join(long_steps)
    )


# "Toolbox > Data Management > Import" is how a technician writes a menu path
# and how a manual indexes one. It is not how you tell somebody what to do: it
# collapses three separate presses into a line that names none of them as a
# button, and it hides whether the middle one is a tab, a card or a screen. Each
# press gets its own step, and the label it carries gets marked as a label.
def test_steps_do_not_collapse_a_menu_path_into_one_line():
    offenders = sorted(
        {
            f"{procedure.monitor_key}/{procedure.objective}: {step[:80]}"
            for procedure in pr.PROCEDURES
            for step in procedure.steps
            if step.count(" > ") >= 1
        }
    )
    assert not offenders, (
        "menu paths written as A > B > C. Give each press its own step and mark "
        "the on-screen wording with « »:\n  " + "\n  ".join(offenders)
    )


# A marked label is a claim that those characters appear on the glass. Steps
# that name no button at all are the ones to be suspicious of on a display we
# claim to have verified -- that is usually a sign the steps were reasoned out
# rather than read off a manual.
def test_a_verified_usb_procedure_names_at_least_one_button():
    from ofpe.procedures._core import labels_in

    offenders = sorted(
        {
            f"{procedure.monitor_key}/{procedure.objective}"
            for procedure in pr.PROCEDURES
            if procedure.confidence is pr.Confidence.VERIFIED
            and procedure.transport is pr.Transport.USB
            and procedure.objective != "prepare_media"
            and not any(labels_in(step) for step in procedure.steps)
        }
    )
    assert not offenders, (
        "marked VERIFIED but no step names a button. _demote_unread_menu_paths "
        "should have caught this — check it still runs in _add:\n  "
        + "\n  ".join(offenders)
    )


def test_the_demotion_actually_fires():
    """The invariant above holds by construction, so prove the machinery works.

    Otherwise a broken demotion would make the test above pass for the wrong
    reason: nothing left to catch because nothing is being checked.
    """
    demoted = [
        p for p in pr.PROCEDURES if p.confidence is pr.Confidence.FILE_VERIFIED
    ]
    assert demoted, "no procedure sits at the middle confidence level"
    assert all(
        p.transport is pr.Transport.USB for p in demoted
    ), "only USB procedures are demoted by this rule"


def test_the_shared_instructions_carry_their_own_explanation():
    """A short step is only safe if the reason lives somewhere findable."""
    from ofpe.procedures._core import _FAT32, _SHP_SET, _STEP_EXPLANATIONS

    pairs = dict(_STEP_EXPLANATIONS)
    for procedure in pr.PROCEDURES:
        for instruction, why in pairs.items():
            if instruction in procedure.steps:
                assert why in procedure.common_errors, (
                    f"{procedure.monitor_key}/{procedure.objective} uses a "
                    "shared instruction but lost its explanation"
                )

    # And the two that matter most are actually in wide use.
    using_fat32 = [p for p in pr.PROCEDURES if _FAT32 in p.steps]
    using_shp = [p for p in pr.PROCEDURES if _SHP_SET in p.steps]
    assert len(using_fat32) > 100
    assert len(using_shp) > 5


def test_no_procedure_repeats_the_same_common_error():
    """Auto-attached explanations must not duplicate a hand-written one."""
    duplicated = [
        f"{p.monitor_key}/{p.objective}"
        for p in pr.PROCEDURES
        if len(p.common_errors) != len(set(p.common_errors))
    ]
    assert not duplicated, f"duplicate common_errors in: {duplicated}"


# --------------------------------------------------------------------------- #
#  On-screen application icons                                                 #
# --------------------------------------------------------------------------- #

def test_every_declared_icon_file_exists():
    """A missing file is a broken image on a page somebody is reading in a cab."""
    root = pathlib.Path(__file__).resolve().parent.parent / "assets" / "icons"
    missing = [
        f"{monitor_key}: {folder}/{icon.file}"
        for monitor_key, (folder, icons) in pr.SCREEN_ICONS.items()
        for icon in icons
        if not (root / folder / icon.file).is_file()
    ]
    assert not missing, "declared icons with no file:\n  " + "\n  ".join(missing)


def test_icons_are_credited_to_a_source():
    """Reproducing a manufacturer's glyph is only defensible if we say so."""
    for monitor_key in pr.SCREEN_ICONS:
        credit = pr.icon_credit(monitor_key)
        assert credit, f"{monitor_key} shows icons with no credit"
        assert "manual" in credit.lower(), monitor_key


def test_a_step_that_names_an_app_can_find_its_icon():
    """The label is the key, so a wording change must not silently drop the icon.

    Renaming «File Manager» to «File manager» in a step would leave the icon
    behind with nothing to attach to, and the loss would be invisible -- the page
    would simply show one fewer picture. This is the guard against that.
    """
    from ofpe.procedures._core import labels_in

    for monitor_key in pr.SCREEN_ICONS:
        icons = pr.icons_for(monitor_key)
        named = {
            label.lower()
            for procedure in pr.PROCEDURES
            if procedure.monitor_key == monitor_key
            for step in procedure.steps
            for label in labels_in(step)
        }
        # Not every icon has to be used, but the two that carry the navigation
        # must be reachable, or no step on this display shows a picture at all.
        for essential in ("menu", "file manager"):
            assert essential in icons, f"{monitor_key} has no {essential} icon"
        assert named & set(icons), (
            f"{monitor_key} declares icons but no step names any of them"
        )


# --------------------------------------------------------------------------- #
#  Finding the software version                                                #
# --------------------------------------------------------------------------- #

def test_version_help_images_exist():
    root = pathlib.Path(__file__).resolve().parent.parent / "assets" / "photos"
    missing = []
    for key, help_ in pr.VERSION_HELP.items():
        for number, step in enumerate(help_.steps, 1):
            for kind, name in (("button", step.button), ("screen", step.screen)):
                if name and not (root / help_.folder / name).is_file():
                    missing.append(f"{key} step {number} {kind}: {name}")
    assert not missing, "missing photos:\n  " + "\n  ".join(missing)


def test_version_help_photos_carry_their_own_explanation():
    """A photo with no caption is decoration, not evidence.

    The point of showing a whole screen is that somebody can check it against
    their own display. That only works if we say what to look at -- five photos
    of the same 2630 are indistinguishable at thumbnail size otherwise.
    """
    for key, help_ in pr.VERSION_HELP.items():
        assert help_.evidence, f"{key} shows photos without saying where from"
        for number, step in enumerate(help_.steps, 1):
            if step.screen:
                assert step.look_for, f"{key} step {number}: screen with no caption"
                assert step.screen_name, f"{key} step {number}: screen with no name"


def test_version_help_points_at_a_display_that_asks_for_a_version():
    """Help for a display with nothing to choose would be help for nothing."""
    for key in pr.VERSION_HELP:
        assert key in catalog_module.MONITORS, key
        assert pr.versions_for(key), f"{key} has no versions to pick between"


def test_version_help_names_the_field_it_is_hunting_for():
    for key, help_ in pr.VERSION_HELP.items():
        assert help_.field_label, key
        assert help_.example, f"{key} gives no example of what the number looks like"
        # The last step is the payoff, so it must name that field.
        assert help_.field_label in help_.steps[-1].text, (
            f"{key}: the final step does not name {help_.field_label!r}"
        )


def test_walkthrough_photos_exist():
    root = pathlib.Path(__file__).resolve().parent.parent / "assets" / "photos"
    missing = []
    for walk in pr.WALKTHROUGHS:
        for number, step in enumerate(walk.steps, 1):
            for kind, name in (("button", step.button), ("screen", step.screen)):
                if name and not (root / walk.folder / name).is_file():
                    missing.append(
                        f"{walk.monitor_key}/{walk.objective} step {number} "
                        f"{kind}: {name}"
                    )
    assert not missing, "missing photos:\n  " + "\n  ".join(missing)


def test_a_walkthrough_owns_the_steps_of_the_procedure_it_documents():
    """One source of truth for a photographed job.

    The photos are matched to steps by position, so a procedure that keeps its
    own copy of the text would slide out of alignment the first time either side
    is edited -- and the failure is silent: photos simply illustrate the wrong
    instruction. So the procedure reads its steps from the walk-through, and
    this is the guard that it still does.
    """
    for walk in pr.WALKTHROUGHS:
        result = pr.resolve(
            walk.monitor_key, walk.objective, walk.transport, None
        )
        assert result.procedure is not None, (
            f"{walk.monitor_key}/{walk.objective} has photos but no procedure"
        )
        assert result.procedure.steps == walk.step_texts(), (
            f"{walk.monitor_key}/{walk.objective}: the procedure's steps have "
            "drifted from the photographed ones. Set "
            "steps=<walk>.step_texts() rather than repeating them."
        )


def test_a_photographed_procedure_is_allowed_to_claim_verified():
    """Photographs are the strongest evidence here, so they must count.

    _demote_unread_menu_paths downgrades anything that names no button. A
    photographed job that happened to describe a press without quoting a label
    would be demoted despite being the best-evidenced answer we have, so this
    catches that going unnoticed.
    """
    for walk in pr.WALKTHROUGHS:
        result = pr.resolve(
            walk.monitor_key, walk.objective, walk.transport, None
        )
        assert result.procedure.confidence is pr.Confidence.VERIFIED, (
            f"{walk.monitor_key}/{walk.objective} is photographed but sits at "
            f"{result.procedure.confidence.value}"
        )


# --------------------------------------------------------------------------- #
#  What a machine can actually be asked to do                                  #
# --------------------------------------------------------------------------- #

def test_a_combine_is_not_offered_a_prescription():
    """It harvests. It does not apply seed, fertiliser or chemical.

    The display is the same box on a combine and on a sprayer, so filtering by
    display alone cannot catch this -- the machine underneath is what rules the
    job out, and that is the wizard's first question.
    """
    for monitor in ("john_deere.gs3_2630", "john_deere.gen4", "case_ih.afs_pro_700"):
        offered = {o.key for o in pr.available_objectives(monitor, None, "combine")}
        assert "import_prescription" not in offered, monitor
        # And the same display on a sprayer still gets it.
        on_sprayer = {o.key for o in pr.available_objectives(monitor, None, "sprayer")}
        assert "import_prescription" in on_sprayer, monitor


def test_asking_without_an_equipment_type_still_offers_everything():
    """The filter narrows an answer; it must not require one."""
    everything = {o.key for o in pr.available_objectives("john_deere.gs3_2630")}
    assert "import_prescription" in everything


def test_a_display_specific_job_name_only_applies_to_that_display():
    """Renaming a job is scoped to one display, and falls back everywhere else.

    The table is empty at the moment -- the 2630 lost its rename when it gained
    a second guidance route -- so the mechanism is exercised against a name
    injected here rather than whatever happens to be configured. A test that
    asserted today's contents would fail the next time a rename is added or
    withdrawn, which is not what it is for.
    """
    injected = ("john_deere.gs3_2630", "import_guidance")
    pr.OBJECTIVE_LABELS[injected] = "Load guidance lines (test)"
    try:
        assert pr.objective_label(*reversed(injected)) == "Load guidance lines (test)"
        assert (
            pr.objective_label("import_guidance", "john_deere.gen4")
            == pr.OBJECTIVES["import_guidance"].label
        )
        assert (
            pr.objective_label("import_guidance")
            == pr.OBJECTIVES["import_guidance"].label
        )
    finally:
        del pr.OBJECTIVE_LABELS[injected]


def test_a_job_with_two_routes_keeps_its_plain_name():
    """A rename that names one route is a lie once a second route exists.

    The 2630 takes a guidance line two ways now -- typed coordinates and a USB
    profile -- so calling the job "lat and long" would be wrong half the time.
    The route question, one press later, is where that distinction belongs.
    """
    routes = {
        p.transport.value
        for p in pr.PROCEDURES
        if p.monitor_key == "john_deere.gs3_2630"
        and p.objective == "import_guidance"
    }
    assert {"manual", "usb"} <= routes, routes
    for monitor_key, objective_key in pr.OBJECTIVE_LABELS:
        offered = pr.available_transports(monitor_key, objective_key)
        assert len(offered) == 1, (
            f"{monitor_key}/{objective_key} is renamed for one route but has "
            f"{len(offered)}: {[t.value for t in offered]}"
        )


def test_every_renamed_job_points_at_a_real_display_and_objective():
    for (monitor_key, objective_key), label in pr.OBJECTIVE_LABELS.items():
        assert monitor_key in catalog_module.MONITORS, monitor_key
        assert objective_key in pr.OBJECTIVES, objective_key
        assert label, f"{monitor_key}/{objective_key} renamed to nothing"
        offered = {o.key for o in pr.available_objectives(monitor_key)}
        assert objective_key in offered, (
            f"{monitor_key} renames {objective_key} but does not offer it"
        )


def test_scope_and_impossibility_stay_separate():
    """Two reasons a job is missing, kept apart on purpose.

    Both hide a row from the same menu, so it would be easy to collapse them
    into one list. Don't: `not_for` says the machine cannot do it, and
    OUT_OF_SCOPE says we chose not to cover it. Only one of those is safe to
    reverse without checking anything.
    """
    # A combine genuinely cannot take a prescription.
    assert "combine" in pr.OBJECTIVES["import_prescription"].not_for
    assert "import_prescription" not in pr.OUT_OF_SCOPE

    # A display can perfectly well update its software; we just do not cover it.
    assert "software_update" in pr.OUT_OF_SCOPE
    assert not pr.OBJECTIVES["software_update"].not_for


def test_the_same_display_offers_the_same_jobs_on_every_machine():
    """An operator moves a 2630 between the tractor and the combine, and the
    display does not change what it can do on the way. The only differences
    allowed are physical ones -- a prescription has nowhere to go on a
    combine -- so the job lists may differ exactly by `not_for` and nothing
    else."""
    for eq_a, eq_b in (("combine", "tractor"), ("tractor", "sprayer"),
                       ("sprayer", "planter")):
        a = {o.key for o in pr.available_objectives(
            "john_deere.gs3_2630", None, eq_a)}
        b = {o.key for o in pr.available_objectives(
            "john_deere.gs3_2630", None, eq_b)}
        for key in a ^ b:
            assert pr.OBJECTIVES[key].not_for, (
                f"{key} differs between {eq_a} and {eq_b} without a physical reason")


def test_out_of_scope_jobs_are_hidden_everywhere():
    """The scope calls were made while looking at a combine, but none of the
    reasons was about combines -- so a sprayer or a tractor does not get
    offered the jobs the project chose not to cover."""
    for eq in ("combine", "tractor", "sprayer", "planter", None):
        offered = {o.key for o in pr.available_objectives(
            "john_deere.gs3_2630", None, eq)}
        overlap = set(pr.OUT_OF_SCOPE) & offered
        assert not overlap, f"{eq}: {sorted(overlap)}"


def test_every_scope_exclusion_names_things_that_exist():
    """A typo here silently hides nothing, which is the worst kind of bug."""
    for key in pr.OUT_OF_SCOPE:
        assert key in pr.OBJECTIVES, key
    for equipment, keys in pr.SCOPE_EXCLUSIONS.items():
        assert equipment in {e.value for e in pr.EquipmentType}, equipment
        for key in keys:
            assert key in pr.OBJECTIVES, f"{equipment}: {key}"


# ----------------------------------------------------------------- speech


def test_a_spoken_step_drops_the_marks_and_names_the_slashes():
    """« » are for the eye; a slash read aloud as "backslash" helps nobody."""
    said = pr.voice.spoken("Open «Data Transfer» and go to GS3_2630\\Profile\\RCD")
    assert "«" not in said and "»" not in said
    assert "\\" not in said
    assert said == "Open Data Transfer and go to GS3_2630, Profile, RCD"


def test_a_clip_is_named_after_what_is_inside_it():
    """Content-addressed, so an edited step cannot reuse the old recording."""
    a = pr.voice.clip_id("Press Menu.")
    assert a == pr.voice.clip_id("Press Menu.")
    assert a != pr.voice.clip_id("Press Menu, then Setup.")
    assert len(a) == 16 and a.isalnum()


def test_every_step_of_every_procedure_has_a_line_to_record():
    """A step with no clip falls back to the phone voice -- silently. So the
    corpus has to cover all of them, and this is what notices when it does not."""
    corpus = pr.voice.lines()
    missing = [
        step
        for procedure in pr.PROCEDURES
        for step in procedure.steps
        if pr.voice.clip_id(pr.voice.spoken(step)) not in corpus
    ]
    assert not missing, missing[:3]


def test_the_numbers_called_out_reach_the_longest_procedure():
    corpus = pr.voice.lines()
    longest = pr.voice.longest_procedure()
    assert longest == max(len(p.steps) for p in pr.PROCEDURES)
    for n in (1, longest):
        assert pr.voice.clip_id(pr.voice.step_prefix(n)) in corpus


def test_the_page_and_the_recordings_say_the_same_thing():
    """The page still speaks the steps itself when a clip is missing. If its
    idea of a spoken step drifted from voice.spoken(), the two voices would
    read the same step differently -- which sounds like a mistake, and is one."""
    source = (pathlib.Path(__file__).resolve().parents[1]
              / "tools" / "build_guide.py").read_text()
    forspeech = source.split("const forSpeech")[1].split(";")[0]
    assert ".replace(/«|»/g, '')" in forspeech
    assert r".replace(/\\/g, ', ')" in forspeech


def test_placeholder_tones_cannot_reach_a_built_page():
    """The tone backend exists so the player can be exercised without model
    weights. It must not be one forgotten flag away from being published:
    clips that load perfectly and are not speech never trigger the fallback."""
    tones = {"backend": pr.voice.PLACEHOLDER_BACKEND, "clips": {"a": {"s": 1, "b": 2}}}
    real = {"backend": "kitten", "clips": {"a": {"s": 1, "b": 2}}}
    assert not pr.voice.shippable(tones)
    assert pr.voice.shippable(tones, allow_placeholder=True)
    assert pr.voice.shippable(real)
    assert not pr.voice.shippable({"backend": "kitten", "clips": {}})


# --------------------------------------------------------------- checklist


def test_every_check_has_a_key_that_is_its_own():
    """A tick is remembered under its key. Two items sharing one means ticking
    one ticks the other, on a list whose whole job is to be trusted."""
    keys = [c.key for stage in pr.checklist_for("harvest") for c in stage.checks]
    assert keys, "the harvest list is empty"
    assert len(keys) == len(set(keys)), sorted(keys)
    for key in keys:
        assert key.replace("_", "").isalnum(), key


def test_the_checklist_carries_no_numbers_of_its_own():
    """The trial sheet has the header width, the field and the coordinates.
    Anything numeric here would be invented, and would be believed."""
    import re

    for stage in pr.checklist_for("harvest"):
        for check in stage.checks:
            text = check.text + " " + check.why
            bad = [n for n in re.findall(r"\d+(?:\.\d+)?", text)]
            assert not bad, f"{check.key} states a number: {bad}"


def test_the_ones_that_cannot_be_undone_say_why():
    hard = [c for stage in pr.checklist_for("harvest")
            for c in stage.checks if c.hard]
    assert hard, "nothing is marked as unrecoverable, which cannot be right"
    for check in hard:
        assert check.why, check.key


def test_every_display_with_a_usb_route_teaches_stick_preparation():
    """The stick is the step everything else depends on, so no display that
    uses one may be missing the how-to -- on any machine it is bolted into."""
    from ofpe import catalog as cat

    missing = []
    for key, m in cat.MONITORS.items():
        if not m.is_terminal:
            continue
        has_usb = any(p.transport is pr.Transport.USB
                      for p in pr.PROCEDURES if p.monitor_key == key)
        if not has_usb:
            continue
        for eq in m.equipment:
            jobs = {o.key for o in pr.available_objectives(key, None, eq)}
            if "prepare_media" not in jobs:
                missing.append((key, eq))
    assert not missing, missing
