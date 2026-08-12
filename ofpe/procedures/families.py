"""Procedure shapes shared by whole families of displays.

Twenty-odd ISOBUS terminals genuinely do behave the same way. Writing each of
them out by hand would be twenty chances to introduce a difference that is not
real, and twenty places to fix a wording change. Where the behaviour is
identical it is expressed once, here; where a brand actually differs, the brand
module says so in its own words.
"""

from __future__ import annotations

from ._core import (
    ANY_VERSION,
    Confidence,
    Transport,
    _add,
    _EJECT,
    _FAT32,
    _SHP_SET,
)

# These steps are deliberately generic: ISO 11783-10 fixes the file -- the
# TASKDATA folder, the TASKDATA.XML name, the capitals -- but nothing fixes what
# any one manufacturer calls the screen you import it from. So every procedure
# built on them sits at FILE_VERIFIED: right about the file, approximate about
# the menu. A brand that publishes its own wording gets its own entry, at the
# top confidence, in its own module.
_ISOXML_IMPORT_STEPS = (
    _FAT32,
    "Unzip the download at the ROOT of the stick so a folder named exactly "
    "TASKDATA sits at the top level, holding TASKDATA.XML.",
    "Check both of those names are in CAPITALS. Several terminals will not "
    "find them written any other way.",
    "Before you go out, switch the terminal's task controller on. Look for an "
    "app or a licence called «Task Controller», «ISOBUS-TC» or «TC».",
    "Plug the stick into the terminal.",
    "Open the task controller and run its import.",
    "Confirm the field appears with its reference lines before you drive off.",
    "Select the line you want on the run screen.",
)

_ISOXML_ERRORS = (
    "Leaving the file zipped on the stick — most terminals cannot open a zip.",
    "A TASKDATA folder nested inside another folder, usually a second TASKDATA "
    "left behind by unzipping.",
    "taskdata or Taskdata instead of TASKDATA. The capitals are part of the "
    "standard and some terminals are strict about them.",
    "Renaming TASKDATA.XML — the name is fixed by the standard.",
    "The task controller was never switched on, so the terminal reports nothing "
    "to import even though the file is perfectly good.",
)


def _isoxml_pair(monitor_key: str, sources: tuple[str, ...], *, version_key=ANY_VERSION,
                 vocabulary: str = "", quirks: tuple[str, ...] = ()) -> None:
    """Add the import and export ISOXML procedures for one ISOBUS terminal.

    The ISOBUS family genuinely does behave the same way, so writing these out
    by hand twenty times would be twenty chances to introduce a difference that
    is not real. `quirks` is for the places where a brand really does differ --
    a zipped archive here, a moved folder there -- so the shared shape stays
    honest instead of quietly averaging the brands together.
    """
    note = (
        (f"This terminal calls an AB line a {vocabulary}.",) if vocabulary else ()
    ) + quirks
    _add(
        monitor_key=monitor_key,
        objective="import_guidance",
        transport=Transport.USB,
        version_key=version_key,
        file_format="ISOXML task data (ISO 11783-10)",
        extensions=(".xml",),
        media_path="TASKDATA\\ at the drive ROOT",
        minutes=10,
        steps=_ISOXML_IMPORT_STEPS,
        verify=("The field and its reference lines are listed after the import.",),
        cautions=note
        + (
            "Any terminal advertising TC-BAS should read this file. If yours is "
            "not listed by name, this procedure still applies.",
        ),
        common_errors=_ISOXML_ERRORS,
        confidence=Confidence.FILE_VERIFIED,
        sources=sources,
    )
    _add(
        monitor_key=monitor_key,
        objective="export_work_data",
        transport=Transport.USB,
        version_key=version_key,
        file_format="ISOXML task data written by the terminal",
        extensions=(".xml", ".bin"),
        media_path="TASKDATA\\ — created by the terminal on the stick",
        minutes=15,
        prerequisites=("Close the running job first, so the last of it is saved.",),
        steps=(
            _FAT32,
            "Close the running task.",
            "Plug the stick into the terminal.",
            "Open the task controller data screen and choose the export or "
            "synchronise option.",
            "Wait for the write to finish.",
            _EJECT,
            "At the office, read the TASKDATA folder with any ISOXML-capable FMIS.",
        ),
        verify=(
            "TASKDATA.XML exists on the stick with .bin time-log files beside it.",
        ),
        cautions=(
            "The .bin files beside TASKDATA.XML hold the recorded values. Copy "
            "the whole folder.",
        ),
        common_errors=("Copying only TASKDATA.XML and losing every logged value.",),
        confidence=Confidence.FILE_VERIFIED,
        sources=sources,
    )




_TASKDATA_ROOT = "TASKDATA\\ at the drive ROOT"


def _isoxml_extras(monitor_key: str, sources: tuple[str, ...],
                   *, vocabulary: str = "") -> None:
    """Boundary, setup, guidance export, backup: the rest of the ISOXML jobs."""
    note = (f"This terminal calls an AB line a {vocabulary}.",) if vocabulary else ()

    _add(
        monitor_key=monitor_key,
        objective="import_boundary",
        transport=Transport.USB,
        file_format="ISOXML task data — the boundary rides with the field",
        extensions=(".xml",),
        media_path=_TASKDATA_ROOT,
        minutes=10,
        prerequisites=(
            "In ISOXML a boundary is part of the field record, not a separate "
            "file. Importing the field brings its boundary with it.",
        ),
        steps=_ISOXML_IMPORT_STEPS[:-2]
        + (
            "Confirm the field appears with its outline drawn.",
            "Attach the field to the running task.",
        ),
        verify=(
            "The boundary draws around the field on the run screen.",
            "If you run section control, the sections shut off at the line.",
        ),
        cautions=note
        + (
            "A hole in the field -- a slough, a pylon -- must be an interior "
            "ring of the same polygon. As a separate polygon it will be treated "
            "as workable ground.",
        ),
        common_errors=_ISOXML_ERRORS,
        confidence=Confidence.FILE_VERIFIED,
        sources=sources,
    )

    _add(
        monitor_key=monitor_key,
        objective="import_setup",
        transport=Transport.USB,
        file_format="ISOXML task data containing customer, farm and field records",
        extensions=(".xml",),
        media_path=_TASKDATA_ROOT,
        minutes=10,
        prerequisites=(
            "Do this before anything else. Every later export files itself "
            "under these names, so getting them right once saves renaming a "
            "season's worth of records later.",
        ),
        steps=(
            _FAT32,
            "Export the customer / farm / field structure from your FMIS as "
            "ISOXML.",
            "Unzip at the ROOT of the stick so a TASKDATA folder appears.",
            "Plug the stick in and run the ISOXML import.",
            "Confirm the names on the terminal match what you expect to see in "
            "reports.",
        ),
        verify=("The field list on the terminal matches your office records.",),
        cautions=(
            "Importing a fresh structure over a working season can leave two "
            "copies of the same field under slightly different names. Match the "
            "spelling your office already uses.",
        ),
        common_errors=_ISOXML_ERRORS,
        confidence=Confidence.CONFIRM_ON_MACHINE,
        sources=sources,
    )

    _add(
        monitor_key=monitor_key,
        objective="export_guidance",
        transport=Transport.USB,
        file_format="ISOXML task data — guidance patterns ride with the field",
        extensions=(".xml",),
        media_path="TASKDATA\\ — written by the terminal onto the stick",
        minutes=10,
        steps=(
            _FAT32,
            "Plug the stick into the terminal.",
            "Open the task controller data screen and choose export or "
            "synchronise to USB.",
            "Wait for the write to finish.",
            _EJECT,
            "At the office, read TASKDATA.XML — the reference lines are stored "
            "as guidance patterns inside the field record.",
        ),
        verify=(
            "TASKDATA.XML exists on the stick and your FMIS lists the lines "
            "after import.",
        ),
        cautions=note
        + (
            "Lines recorded in the cab are often better than anything drawn in "
            "the office, because they follow the ground the machine can "
            "actually drive. Pull them off and keep them.",
        ),
        common_errors=(
            "Exporting only the completed task and missing the field record "
            "that holds the lines.",
        ),
        confidence=Confidence.FILE_VERIFIED,
        sources=sources,
    )

    _add(
        monitor_key=monitor_key,
        objective="export_boundary",
        transport=Transport.USB,
        file_format="ISOXML task data — the boundary is part of the field record",
        extensions=(".xml",),
        media_path="TASKDATA\\ — written by the terminal",
        minutes=10,
        prerequisites=(
            "A boundary driven around the headland is usually the most accurate "
            "outline of that field in existence. Worth collecting even when the "
            "office already has one.",
        ),
        steps=(
            _FAT32,
            "Plug the stick into the terminal.",
            "Open the task controller data screen and export or synchronise.",
            "Wait for the write, then eject from the menu.",
            "At the office, read the field record out of TASKDATA.XML.",
        ),
        verify=("Your FMIS draws the boundary where you expect after import.",),
        cautions=(
            "Compare the driven boundary against your existing one before "
            "replacing it — a boundary recorded with a wide implement can sit "
            "half a machine width inside the fence.",
        ),
        confidence=Confidence.FILE_VERIFIED,
        sources=sources,
    )

    _add(
        monitor_key=monitor_key,
        objective="export_backup",
        transport=Transport.USB,
        file_format="The complete TASKDATA set: XML plus every .bin time log",
        extensions=(".xml", ".bin"),
        media_path="TASKDATA\\ — copy the whole folder",
        minutes=20,
        prerequisites=(
            "Do this before a software update and before the machine changes "
            "hands.",
        ),
        steps=(
            _FAT32,
            "Close any running task.",
            "Plug the stick into the terminal.",
            "Export or synchronise the full task data set, not a single task.",
            "Wait for the write to finish and eject from the menu.",
            "Copy the entire TASKDATA folder somewhere that gets backed up.",
        ),
        verify=(
            "TASKDATA.XML is present along with the .bin files — those hold the "
            "recorded values and are the part people lose.",
        ),
        cautions=(
            "Copying only TASKDATA.XML looks like a backup and contains none of "
            "the logged data.",
        ),
        common_errors=("Backing up the XML and leaving the .bin files behind.",),
        confidence=Confidence.FILE_VERIFIED,
        sources=sources,
    )


def _terminal_update(monitor_key: str, portal: str, sources: tuple[str, ...],
                     *, dealer: bool = False) -> None:
    """Software update. Shape is common; who is allowed to run it is not."""
    dealer_note = (
        (
            "On this brand a display update is normally a dealer job — the "
            "package is not published for open download. Booking it is the "
            "procedure; doing it yourself usually is not an option.",
        )
        if dealer
        else ()
    )
    _add(
        monitor_key=monitor_key,
        objective="software_update",
        transport=Transport.USB,
        file_format="Manufacturer update package",
        media_path="Drive root — the package creates its own folders",
        minutes=60,
        prerequisites=(
            "Take a full backup first. An update is the classic moment to lose "
            "a season of data.",
            "Park the machine and keep it running or on a charger. A display "
            "that loses power mid-update can need a dealer to recover.",
        ),
        steps=dealer_note
        + (
            _FAT32,
            f"Obtain the update package from {portal}.",
            "Copy it to the stick exactly as supplied — do not rearrange or "
            "rename the folders.",
            "Plug the stick into the terminal with the machine running.",
            "Open the terminal's service / software menu and select the update.",
            "Leave it alone until the terminal restarts on its own.",
            "Confirm the new version, then check your fields and lines survived.",
        ),
        verify=(
            "The terminal reports the version you installed.",
            "Your field list, boundaries and guidance lines are still present.",
        ),
        cautions=(
            "Allow an hour, in the yard, not at the end of a field.",
        )
        + dealer_note,
        common_errors=(
            "Updating with no backup.",
            "Switching off partway through.",
        ),
        confidence=Confidence.CONFIRM_ON_MACHINE,
        sources=sources,
    )


def _cloud_route(monitor_key: str, platform: str, sources: tuple[str, ...],
                 *, objectives=("import_prescription", "import_guidance",
                                "import_boundary", "export_work_data"),
                 caveat: str = "") -> None:
    """The manufacturer's own platform, in place of walking a stick out."""
    for objective_key in objectives:
        outbound = objective_key.startswith("export")
        _add(
            monitor_key=monitor_key,
            objective=objective_key,
            transport=Transport.CLOUD,
            platform=platform,
            file_format=f"Handled by {platform} — no file for you to place",
            media_path="",
            filesystem="n/a — wireless",
            minutes=10,
            prerequisites=(
                f"A {platform} account, an active data subscription, and the "
                "machine showing as connected in the portal.",
            ),
            steps=(
                f"Log in to {platform} and confirm the machine appears as "
                "connected.",
                "Confirm the client / farm / field names match what is on the "
                "terminal, or the data will land under a duplicate field.",
            )
            + (
                (
                    "Completed work uploads on its own once the task is closed.",
                    "Open the field in the portal and confirm the record arrived "
                    "with the area you expect.",
                    "Export from there to your FMIS in whatever format it takes.",
                )
                if outbound
                else (
                    "Upload or build the item in the portal and attach it to the "
                    "right field.",
                    "Send it to the machine.",
                    "In the cab, accept the incoming transfer if the terminal "
                    "prompts.",
                    "Select it on the run screen before starting work.",
                )
            ),
            verify=(
                "The portal shows the completed work against the right field."
                if outbound
                else "The item appears on the terminal under the right field."
            ,),
            cautions=(
                (caveat,)
                if caveat
                else ()
            )
            + (
                "Wireless is the easiest route when it works and the most "
                "confusing when it does not. If a transfer never arrives, check "
                "the subscription before suspecting the file.",
                "Keep taking an occasional USB export. A machine that loses "
                "connectivity buffers its data, but not forever.",
            ),
            confidence=Confidence.CONFIRM_ON_MACHINE,
            sources=sources,
        )




# --------------------------------------------------------------------------- #
#  Points: getting a latitude / longitude onto the display                     #
# --------------------------------------------------------------------------- #
# The thing to understand before reading any of these: a display marks where
# the machine IS far more readily than it navigates to where you WANT it. Most
# terminals will drop a flag at the current position with one tap, and most
# will draw points that arrived in a file -- but very few let you key in an
# arbitrary latitude and then guide you there.
#
# That shapes the advice. If the point matters, it should arrive as a file. The
# typed route is documented because it is genuinely the fastest way to record
# one spot, not because it is the way to find one.

_COORD_FORMAT = (
    "Write coordinates as plain decimal degrees -- -27.845123, -54.477456 -- "
    "with south and west negative. Degrees-and-minutes (27 50.7 S) is a "
    "different notation and lands the point kilometres away."
)

_POINT_USES = (
    "Trial plot corners, soil sample points, a tile inlet, a rock worth "
    "steering around: anything the operator has to find rather than guess at."
)


def _point_routes(
    monitor_key: str,
    sources: tuple[str, ...],
    *,
    vocabulary: str = "Flag",
    file_kind: str = "isoxml",
    media_path: str = "",
    filesystem: str = "FAT32",
    skip: tuple[str, ...] = (),
) -> None:
    """Import and export of marked points, by file and by hand.

    ``filesystem`` exists because not every target is a USB stick: AgOpenGPS is
    an application on a PC, where demanding a FAT32 stick would be nonsense.

    ``skip`` drops a route this display documents better in its own module. The
    by-hand route in particular ends in "look under the field or flag setup" --
    honest for a display we have not read a manual for, and no longer good
    enough once we have. A brand that can name the screen should say so, and
    skipping is how it takes over without leaving two answers to one question.
    """
    on_a_stick = filesystem.upper().startswith("FAT")

    if not on_a_stick:
        # A PC application: there is no stick to format and no display to plug
        # it into, so the steps are a straight file copy.
        fmt = "Point file dropped into the field folder"
        extensions = (".shp", ".shx", ".dbf", ".prj")
        path = media_path or "The field folder"
        file_steps = (
            "Copy the point file into the field folder on the computer.",
            "Open the field in the software.",
            "The points draw on the map.",
        )
        export_steps = (
            "Close the field so everything is written to disk.",
            "Copy the field folder out.",
            "The points are in there with the rest of the field.",
        )
    elif file_kind == "isoxml":
        fmt = "ISOXML task data -- points travel inside the field record"
        extensions = (".xml",)
        path = media_path or "TASKDATA\\ at the drive ROOT"
        file_steps = (
            _FAT32,
            "Unzip at the ROOT of the stick so a TASKDATA folder appears.",
            "Plug the stick into the terminal and run the import.",
            "Open the field. The points appear on the map as markers.",
        )
        export_steps = (
            _FAT32,
            "Plug the stick into the display.",
            "Open the data screen and export the field data.",
            "Wait for it to finish, then eject.",
            f"At the office, the {vocabulary.lower()}s come out with the field.",
        )
    else:
        fmt = "Point shapefile: the .shp, .shx, .dbf and .prj together"
        extensions = (".shp", ".shx", ".dbf", ".prj")
        path = media_path or "Drive root"
        file_steps = (
            _FAT32,
            _SHP_SET,
            "Plug the stick into the display and open the import screen.",
            f"Import it as {vocabulary.lower()}s, then open the field.",
        )
        export_steps = (
            _FAT32,
            "Plug the stick into the display.",
            "Open the data screen and export the field data.",
            "Wait for it to finish, then eject.",
            f"At the office, the {vocabulary.lower()}s come out with the field.",
        )

    _add(
        monitor_key=monitor_key,
        objective="import_point",
        transport=Transport.USB,
        file_format=fmt,
        extensions=extensions,
        media_path=path,
        filesystem=filesystem,
        minutes=10,
        prerequisites=(
            _POINT_USES,
            "You need the points as a file. If you only have numbers on a bit "
            "of paper, the office can turn them into one -- or use the "
            "type-it-in route instead.",
        ),
        steps=file_steps,
        verify=(
            f"The {vocabulary.lower()}s draw on the map where you expect them.",
            "Zoom right in on one and check it sits where it should relative to "
            "a fence or a corner you recognise.",
        ),
        cautions=(
            f"This display calls a marked point a {vocabulary}.",
            _COORD_FORMAT,
            "A point that lands in the wrong place is almost always a "
            "coordinate written in the wrong notation, not a broken import.",
        ),
        common_errors=(
            "Latitude and longitude the wrong way round. In this part of the "
            "world latitude is the smaller number and both are negative.",
        ),
        confidence=Confidence.CONFIRM_ON_MACHINE,
        sources=sources,
    )

    if "manual" not in skip:
        _add(
            monitor_key=monitor_key,
            objective="import_point",
            transport=Transport.MANUAL,
            file_format="None -- nothing to prepare",
            media_path="",
            filesystem="n/a",
            minutes=5,
            prerequisites=(
                "Read this before you start: almost every display can mark where "
                "the machine IS, but very few can be given a latitude and then "
                "guide you to it. So the reliable way to hit an exact point by hand "
                "is to get there first, then mark it.",
            ),
            steps=(
                "Put the coordinates into the map app on your phone and drive to "
                "the spot. Any phone map takes decimal degrees.",
                "Stop with the machine sitting on the point.",
                f"On the display, add a {vocabulary.lower()} at the current "
                "position -- usually one button on the map or run screen.",
                "Give it a name you will recognise later, not the default.",
                "Repeat for each point.",
            ),
            verify=(
                f"The {vocabulary.lower()} shows on the map at the machine.",
                "Drive away and back: it should stay put.",
            ),
            cautions=(
                _COORD_FORMAT,
                "This is accurate to wherever you stopped the machine, which is "
                "fine for a sample point and not fine for a trial plot corner. For "
                "anything that has to be exact, use a file.",
                "If your display does let you key in a latitude directly, it is "
                "usually under the field or flag setup rather than on the run "
                "screen. Worth two minutes of looking before you drive out.",
            ),
            common_errors=(
                "Marking the point from the cab while the machine is a few metres "
                "past it. The display marks the antenna, not the drawbar.",
            ),
            confidence=Confidence.CONFIRM_ON_MACHINE,
            sources=sources,
        )

    _add(
        monitor_key=monitor_key,
        objective="export_point",
        transport=Transport.USB,
        file_format=fmt,
        extensions=extensions,
        media_path=path,
        filesystem=filesystem,
        minutes=10,
        prerequisites=(
            "Flags dropped in the cab are often the only record that something "
            "happened -- a wet hole, a blocked row, where a trial actually "
            "started rather than where it was planned.",
        ),
        steps=export_steps,
        verify=("The points open in your office software where you expect.",),
        cautions=(
            "Collect these at the end of every season. They are the cheapest "
            "field records anyone ever makes and the first ones lost when a "
            "display is traded in.",
        ),
        confidence=Confidence.CONFIRM_ON_MACHINE,
        sources=sources,
    )
