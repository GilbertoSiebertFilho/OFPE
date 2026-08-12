"""CNH: Case IH AFS and New Holland IntelliView displays."""

from __future__ import annotations

from .._core import (
    ANY_VERSION,
    Confidence,
    Transport,
    _add,
    _EJECT,
    _FAT32,
    _NO_ACCENTS,
    _SHP_SET,
)

# =========================================================================== #
#  CNH -- Case IH, New Holland                                                #
# =========================================================================== #

_add(
    monitor_key="case_ih.afs_pro_700",
    objective="import_prescription",
    transport=Transport.USB,
    version_key=("pro700_28", "pro700_29", "pro700_30"),
    file_format="Complete shapefile, inside a folder named Shapefile",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="Shapefile\\  — that exact name, at the ROOT of the stick",
    minutes=25,
    prerequisites=(
        "This display loads in two halves with a power cycle in between. Do "
        "not start it five minutes before you want to be moving.",
    ),
    steps=(
        _FAT32,
        "At the ROOT of the stick create a folder named exactly Shapefile — "
        "capital S, no s on the end.",
        "Copy all four parts into it — the .shp, .shx, .dbf and .prj.",
        "In the cab, turn the display OFF. On this display the stick goes in "
        "with the power off; plugging into a running Pro 700 does nothing.",
        "Plug the stick in, then power the machine ON.",
        "As it starts, the display copies the files into its own internal "
        "storage.",
        "When the message about importing to internal storage appears, press "
        "«OK», then key off and let the display shut all the way down.",
        "Power on again. The files are inside the display now; the stick is no "
        "longer needed.",
        "Open «Data Management» and go to the «Import2» tab. This is the half "
        "everybody misses: here you tell the display which field each "
        "prescription belongs to.",
        "Pick the first prescription in the list.",
        "Press the «Select Field» drop-down and set the Grower, Farm and Field.",
        "Press «Product Form» and choose what it is — Seed, Fertilizer, and so "
        "on.",
        "Press «Units», choose the unit the map is in, and set the default "
        "application rate.",
        "Press «Import», top right of the screen.",
        "Repeat for each remaining prescription.",
    ),
    verify=(
        "The prescription draws on the run screen over the right field.",
        "The Grower, Farm and Field on the run screen match the ones you set.",
    ),
    cautions=(
        "The two-stage load is what everyone gets wrong. Files reach internal "
        "storage on the first power-up; assigning them to fields on the "
        "«Import2» tab is a separate job afterwards.",
        "Case IH ships a branded USB stick (part 84398840). Any properly "
        "formatted FAT32 stick works, but if one misbehaves that is the "
        "known-good one.",
        _EJECT,
    ),
    common_errors=(
        "Plugging the stick into a running display. Nothing loads, and the "
        "list looks empty as if the file were bad.",
        "Naming the folder Shapefiles, shapefile or Rx. It has to be Shapefile.",
        "Skipping the key-off after the import message, so the second half "
        "never happens.",
        "Stopping once the files reach internal storage and wondering why no "
        "prescription shows in the field — the «Import2» assignment is still "
        "to do.",
    ),
    confidence=Confidence.VERIFIED,
    sources=(
        "Case IH AFS Pro 700 shapefile (.shp) import guide — Shapefile folder, "
        "power-off insertion, Data Management > Import2 assignment",
        "Case IH AFS Rx quick reference card",
    ),
)

_add(
    monitor_key="case_ih.afs_pro_700",
    objective="import_guidance",
    transport=Transport.USB,
    file_format="Shapefile lines — the display calls this a Multiswath",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="Drive root",
    minutes=15,
    steps=(
        _FAT32,
        _SHP_SET,
        "Leave the four files loose at the drive root.",
        "Plug the stick in.",
        "Open «Swath».",
        "Choose the shapefile / Multiswath import.",
        "Select the Grower, Farm and Field.",
        "Select the file and import.",
        "On the run screen, pick the swath before engaging the steering.",
    ),
    verify=(
        "The swath draws where you expect on the run screen.",
        "Drive one pass with steering off to confirm the machine tracks it.",
    ),
    cautions=(
        "This display calls an AB line a Swath, and a set of imported lines a "
        "Multiswath. Look for those words, not 'guidance line'.",
    ),
    confidence=Confidence.VERIFIED,
    sources=("Case IH AFS Pro 700 shapefile import guide",),
)

_add(
    monitor_key="case_ih.afs_pro_700",
    objective="export_work_data",
    transport=Transport.USB,
    file_format="Display data package written by the AFS software",
    media_path="Drive root — the display creates its own folder tree",
    minutes=15,
    prerequisites=("Close the current task so the last records are written.",),
    steps=(
        _FAT32,
        "Close or pause the running task.",
        "Plug the stick into the display.",
        "Open «Data Management» and press «Export».",
        "Select the Grower / Farm / Field data you want.",
        "Confirm and wait for the transfer to complete.",
        _EJECT,
        "At the office, import the folder into AFS Software or your FMIS.",
    ),
    verify=("The folder on the stick is not empty and carries today's date.",),
    cautions=("Use one stick for this machine only.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("Case IH AFS Pro 700 software operating guide",),
)

_add(
    monitor_key="case_ih.afs_pro_1200",
    objective="import_guidance",
    transport=Transport.USB,
    file_format="ISOXML task data (ISO 11783-10)",
    extensions=(".xml",),
    media_path="TASKDATA\\  — folder named exactly that, at the drive ROOT",
    minutes=10,
    steps=(
        _FAT32,
        "Unzip the download at the ROOT of the stick so a folder named exactly "
        "TASKDATA appears, containing TASKDATA.XML. Capitals both times.",
        "Plug the stick into the display's USB port.",
        "Press the button on the top bar to open «Menu».",
        "Open the «Data» card.",
        "Press «Import».",
        "Press «Select Import Source».",
        "In the «Select Import Source» window pick the folder on the stick, "
        "then press «Select».",
        "Confirm the field and its guidance lines are listed, then finish the "
        "import.",
        "On the run screen, select the line before you engage the steering.",
    ),
    verify=(
        "The field and its reference lines are listed after the import.",
        "Drive one pass with the steering off and confirm the machine tracks "
        "the line you expect.",
    ),
    cautions=(
        "The folder must be named TASKDATA, in capitals, at the root. One level "
        "deeper and it will not be found.",
        "This display calls an AB line a Swath. Look for that word, not "
        "'guidance line'.",
        "CNH publishes its own ADAPT plugin for this format, so ISOXML is a "
        "well-supported route here rather than a hopeful one.",
    ),
    common_errors=(
        "Leaving the download zipped on the stick.",
        "A TASKDATA folder inside another TASKDATA folder after unzipping.",
        "Renaming TASKDATA.XML — the name is fixed by the standard, and in "
        "capitals.",
    ),
    confidence=Confidence.VERIFIED,
    sources=(
        "Case IH AFS Pro 1200 software operating manual — Importing data "
        "(Menu > Data > Import > Select Import Source)",
        "CNH developer portal, ISOXML ADAPT plugin guide",
    ),
)

_add(
    monitor_key="case_ih.afs_pro_1200",
    objective="import_prescription",
    transport=Transport.USB,
    file_format="ISOXML task data, or a complete shapefile",
    extensions=(".xml", ".shp", ".shx", ".dbf", ".prj"),
    media_path="TASKDATA\\ (ISOXML) or Shapefile\\ (shapefile) — at the ROOT",
    minutes=15,
    steps=(
        _FAT32,
        "For ISOXML: unzip at the root so TASKDATA\\TASKDATA.XML exists, in "
        "capitals.",
        "For a shapefile: create a folder named exactly Shapefile at the root "
        "and put all four parts inside it — the .shp, .shx, .dbf and .prj.",
        "Not loose at the root, and not in a folder of your own naming.",
        "Plug the stick into the display's USB port.",
        "Press the button on the top bar to open «Menu».",
        "Open the «Data» card, then press «Import».",
        "Press «Select Import Source», pick the folder, and press «Select».",
        "Work through the import and attach the prescription to the right "
        "Grower, Farm and Field.",
        "Choose the rate column and the unit the map is in.",
    ),
    verify=(
        "The rate map draws over the right field with sensible values, not "
        "zeros or blanks.",
    ),
    cautions=(
        _NO_ACCENTS,
        "Keep one kind of data per stick. A TASKDATA folder and a Shapefile "
        "folder together confuses the import screen more than it helps.",
    ),
    common_errors=(
        "Leaving shapefile parts loose at the root instead of inside a folder "
        "named Shapefile.",
        "Mixing an ISOXML TASKDATA folder and shapefiles on one stick.",
    ),
    confidence=Confidence.VERIFIED,
    sources=(
        "Case IH AFS Pro 1200 software operating manual — Importing Shapefile "
        "Data (Shapefile folder; Menu > Data > Import > Select Import Source)",
        "CNH developer portal, ISOXML ADAPT plugin guide",
    ),
)

_add(
    monitor_key="case_ih.afs_pro_1200",
    objective="export_work_data",
    transport=Transport.USB,
    file_format="ISOXML task data written by the display",
    extensions=(".xml", ".bin"),
    media_path="TASKDATA\\ — created by the display on the stick",
    minutes=15,
    prerequisites=("Close the running job first.",),
    steps=(
        _FAT32,
        "Close the running task so the last records are written.",
        "Plug the stick into the display's USB port.",
        "Press the button on the top bar to open «Menu».",
        "Open the «Data» card and press «Export».",
        "Select the tasks, or the whole task data set.",
        "Wait for it to finish, then eject from the menu.",
        "At the office, read the whole TASKDATA folder with any ISOXML-capable "
        "farm software.",
    ),
    verify=(
        "TASKDATA.XML exists on the stick and there are .bin time-log files "
        "beside it — those hold the recorded data.",
    ),
    cautions=(
        "The .bin files beside TASKDATA.XML are the actual logged data. Copy "
        "the whole folder, not just the XML.",
    ),
    common_errors=("Copying only TASKDATA.XML and losing every logged value.",),
    confidence=Confidence.VERIFIED,
    sources=("CNH developer portal, ISOXML ADAPT plugin guide",),
)

_add(
    monitor_key="case_ih.afs_pro_1200",
    objective="export_work_data",
    transport=Transport.CLOUD,
    file_format="Automatic sync to AFS Connect",
    media_path="",
    filesystem="n/a — wireless",
    minutes=5,
    prerequisites=("An AFS Connect subscription and a connected modem.",),
    steps=(
        "Confirm the machine shows as connected in the AFS Connect portal.",
        "Confirm data sharing is enabled on the display.",
        "Work data uploads automatically as tasks are completed.",
        "In the portal, open the farm and confirm the task has arrived.",
    ),
    verify=("The task appears in AFS Connect with the expected area.",),
    cautions=("Keep taking an occasional USB export as a backup.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("Case IH AFS Connect documentation",),
)

_add(
    monitor_key="new_holland.intelliview_iv",
    objective="import_guidance",
    transport=Transport.USB,
    file_format="Shapefile lines — the display calls this a Multiswath",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="Shapefile\\  — that exact name, at the ROOT of the stick",
    minutes=20,
    steps=(
        _FAT32,
        "At the ROOT of the stick create a folder named exactly Shapefile and "
        "copy all four parts of the line file into it.",
        "Turn the display OFF, plug the stick in, then power ON.",
        "Let the display copy the files into internal storage, press «OK» at "
        "the message, key off and let it shut down.",
        "Power on again and open «Data Management».",
        "Import the lines and assign them to the right Grower, Farm and Field.",
        "Pick the swath on the run screen before engaging the steering.",
    ),
    verify=(
        "The swath draws where you expect it on the run screen.",
        "Drive one pass with the steering off to confirm the machine tracks it.",
    ),
    cautions=(
        "This display calls an AB line a Swath, and a set of imported lines a "
        "Multiswath. Look for those words.",
        "IntelliView IV and the Case IH AFS Pro 700 are the same display in "
        "different paint. Anything that imports on one imports on the other.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("Case IH / New Holland Voyager display documentation",),
)

_add(
    monitor_key="new_holland.intelliview_iv",
    objective="import_prescription",
    transport=Transport.USB,
    file_format="Complete shapefile, or ISOXML / CN1 on later software",
    extensions=(".shp", ".shx", ".dbf", ".prj", ".xml"),
    media_path="Shapefile\\  — that exact name, at the ROOT of the stick",
    minutes=25,
    prerequisites=(
        "Like the Pro 700 it shares its hardware with, this loads in two halves "
        "with a power cycle between them.",
    ),
    steps=(
        _FAT32,
        "At the ROOT of the stick create a folder named exactly Shapefile — "
        "capital S, no s on the end.",
        "Copy all four parts into it — the .shp, .shx, .dbf and .prj.",
        "Turn the display OFF, plug the stick in, then power ON. The stick goes "
        "in with the power off on this display.",
        "The display copies the files into internal storage as it starts. When "
        "the message appears, press «OK», then key off and let it shut down.",
        "Power on again and open «Data Management».",
        "Go to the import tab and pick the first prescription.",
        "Set the Grower, Farm and Field it belongs to.",
        "Set the product form, the unit and the default rate, then import.",
        "Repeat for each remaining prescription.",
    ),
    verify=(
        "The rate map draws over the right field with sensible values.",
    ),
    cautions=(
        "IntelliView IV and the Case IH AFS Pro 700 are the same display in "
        "different paint. Anything written for one applies to the other, "
        "including the Shapefile folder name and the power-off insertion.",
        "Later IntelliView IV software also accepts ISOXML and CN1 files.",
    ),
    common_errors=(
        "Plugging the stick into a running display, so nothing loads.",
        "Naming the folder Shapefiles or shapefile rather than Shapefile.",
        "The rates stored as words rather than numbers, so they all read as "
        "zero.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=(
        "New Holland IntelliView IV prescription import guidance (Shapefile "
        "folder, capital S, no trailing s)",
        "Case IH AFS Pro 700 shapefile import guide — same hardware",
    ),
)

_add(
    monitor_key="new_holland.intelliview_12",
    objective="import_guidance",
    transport=Transport.USB,
    file_format="ISOXML task data (ISO 11783-10)",
    extensions=(".xml",),
    media_path="TASKDATA\\ at the drive ROOT",
    minutes=10,
    steps=(
        _FAT32,
        "Unzip at the root so a TASKDATA folder appears with TASKDATA.XML inside.",
        "Plug the stick in and open data management.",
        "Run the ISOXML import.",
        "Select the field, then pick the swath on the run screen.",
    ),
    verify=("The field and its lines are listed after the import.",),
    cautions=(
        "IntelliView 12 and AFS Pro 1200 are the same display; both read and "
        "write ISO 11783-10.",
    ),
    common_errors=("Leaving the file zipped.", "A nested TASKDATA folder."),
    confidence=Confidence.VERIFIED,
    sources=("CNH developer portal, ISOXML ADAPT plugin guide",),
)

_add(
    monitor_key="new_holland.intelliview_12",
    objective="export_work_data",
    transport=Transport.USB,
    file_format="ISOXML task data written by the display",
    extensions=(".xml", ".bin"),
    media_path="TASKDATA\\ — created by the display",
    minutes=15,
    steps=(
        _FAT32,
        "Close the running task.",
        "Plug the stick in, open data management, choose Export.",
        "Select the task data and confirm.",
        "Wait for completion and eject from the menu.",
    ),
    verify=("TASKDATA.XML plus .bin log files are on the stick.",),
    cautions=("Copy the whole TASKDATA folder — the .bin files hold the data.",),
    confidence=Confidence.VERIFIED,
    sources=("New Holland IntelliView 12 operating system guide",),
)


# --------------------------------------------------------------------------- #
#  The rest of the CNH jobs                                                    #
# --------------------------------------------------------------------------- #
# The generational split runs through everything here. Pro 1200 and
# IntelliView 12 are ISOXML natives and behave like the rest of the ISOBUS
# world, so they take the family shapes. Pro 700 and IntelliView IV predate
# that and need their own words.

from ..families import _cloud_route, _isoxml_extras, _terminal_update  # noqa: E402

_CNH_1200_SOURCES = (
    "CNH developer portal, ISOXML ADAPT plugin guide",
    "Case IH AFS Pro 1200 software operating manual",
)
_CNH_IV12_SOURCES = (
    "CNH developer portal, ISOXML ADAPT plugin guide",
    "New Holland IntelliView 12 operating system guide",
)

_isoxml_extras("case_ih.afs_pro_1200", _CNH_1200_SOURCES, vocabulary="Swath")
_isoxml_extras("new_holland.intelliview_12", _CNH_IV12_SOURCES, vocabulary="Swath")

_terminal_update("case_ih.afs_pro_1200", "your Case IH dealer or the AFS portal",
                 _CNH_1200_SOURCES, dealer=True)
_terminal_update("new_holland.intelliview_12", "your New Holland dealer or PLM",
                 _CNH_IV12_SOURCES, dealer=True)

_cloud_route("case_ih.afs_pro_1200", "AFS Connect", _CNH_1200_SOURCES,
             objectives=("import_prescription", "import_guidance",
                         "import_boundary", "import_point", "export_work_data"))
_cloud_route("new_holland.intelliview_12", "PLM Connect", _CNH_IV12_SOURCES,
             objectives=("import_prescription", "import_guidance",
                         "import_boundary", "import_point", "export_work_data"))


# --------------------------------------------------------------------------- #
#  Voyager generation: AFS Pro 700 and IntelliView IV                          #
# --------------------------------------------------------------------------- #

_VOYAGER_SOURCES = (
    "Case IH AFS Pro 700 software operating guide",
    "Case IH / New Holland Voyager display documentation",
)


def _voyager_extras(monitor_key: str, brand: str) -> None:
    """The Voyager-era jobs. Same display, two badges."""
    _add(
        monitor_key=monitor_key,
        objective="import_boundary",
        transport=Transport.USB,
        file_format="Complete shapefile, POLYGON geometry, files loose at the root",
        extensions=(".shp", ".shx", ".dbf", ".prj"),
        media_path="Drive root",
        minutes=15,
        steps=(
            _FAT32,
            _SHP_SET,
            "Leave the four files loose at the drive root.",
            "Plug the stick into the display.",
            "Open «Data Management». On some software lines this sits under "
        "«Field» instead — check both.",
            "Choose the boundary import.",
            "Select the Grower, Farm and Field it belongs to.",
            "Select the file and import.",
        ),
        verify=(
            "The boundary draws around the field on the run screen.",
            "Section control shuts the booms off at the line, if you run it.",
        ),
        cautions=(
            "The geometry must be a polygon. A boundary exported as a line will "
            "import and then behave as if there is no boundary at all.",
        ),
        common_errors=(
            "The file draws the field as an outline rather than an area. It imports "
        "and then behaves as if there is no boundary at all.",
        ),
        confidence=Confidence.CONFIRM_ON_MACHINE,
        sources=_VOYAGER_SOURCES,
    )

    _add(
        monitor_key=monitor_key,
        objective="import_setup",
        transport=Transport.USB,
        file_format="Grower / Farm / Field structure, created on the display or imported",
        media_path="Drive root",
        minutes=15,
        prerequisites=(
            "Do this before importing anything else. Every swath, boundary and "
            "recorded task on this display files itself under Grower / Farm / "
            "Field, and fixing those names afterwards means re-filing the lot.",
        ),
        steps=(
            _FAT32,
            "Decide the exact Grower, Farm and Field spellings your office uses.",
            "Plug the stick into the display.",
            "Open «Data Management».",
            "Either import the structure from your FMIS export, or create the "
            "entries by hand on the display.",
            "Check the spelling character by character against the office list.",
        ),
        verify=("The Grower / Farm / Field list matches your office records.",),
        cautions=(
            "A trailing space or a different spelling creates a second field "
            "that looks identical on screen and reports separately.",
        ),
        common_errors=("Letting each operator type field names their own way.",),
        confidence=Confidence.CONFIRM_ON_MACHINE,
        sources=_VOYAGER_SOURCES,
    )

    _add(
        monitor_key=monitor_key,
        objective="export_guidance",
        transport=Transport.USB,
        file_format="Display data package containing the saved swaths",
        media_path="Drive root — the display writes its own folder tree",
        minutes=15,
        steps=(
            _FAT32,
            "Plug the stick into the display.",
            "Open «Data Management» and press «Export».",
            "Select the Grower / Farm / Field whose swaths you want.",
            "Confirm and wait for the transfer to finish.",
            _EJECT,
            "At the office, read the folder with AFS Software or your FMIS.",
        ),
        verify=("The exported folder is present and not empty.",),
        cautions=(
            "This display calls an AB line a Swath. If you go looking for "
            "'guidance lines' in the export menu you will not find them.",
        ),
        confidence=Confidence.CONFIRM_ON_MACHINE,
        sources=_VOYAGER_SOURCES,
    )

    _add(
        monitor_key=monitor_key,
        objective="export_boundary",
        transport=Transport.USB,
        file_format="Display data package containing the recorded boundary",
        media_path="Drive root",
        minutes=15,
        prerequisites=(
            "A boundary recorded by driving the headland is usually more "
            "accurate than anything the office has on file.",
        ),
        steps=(
            _FAT32,
            "Plug the stick into the display.",
            "Open «Data Management» and press «Export».",
            "Select the Grower / Farm / Field.",
            "Confirm and wait for the transfer.",
            "Read the folder at the office and convert to shapefile if your "
            "FMIS needs it.",
        ),
        verify=("The boundary opens in your office software where you expect.",),
        cautions=(
            "A boundary driven with a wide header sits half a machine width "
            "inside the fence. Check before replacing an existing one.",
        ),
        confidence=Confidence.CONFIRM_ON_MACHINE,
        sources=_VOYAGER_SOURCES,
    )

    _add(
        monitor_key=monitor_key,
        objective="export_backup",
        transport=Transport.USB,
        file_format="Full display data export",
        media_path="Drive root",
        minutes=25,
        prerequisites=("Do this before a software update and before a trade-in.",),
        steps=(
            _FAT32,
            "Use a stick with room to spare and nothing else on it.",
            "Close the running task.",
            "Open «Data Management» and press «Export».",
            "Select everything, not one field.",
            "Wait for the transfer to complete fully.",
            _EJECT,
            "Copy the folder somewhere that gets backed up.",
        ),
        verify=("The folder contains every Grower / Farm / Field you expected.",),
        cautions=(
            "Displays get traded in with a season of unexported yield data on "
            "them every year. This is the ten minutes that prevents it.",
        ),
        confidence=Confidence.CONFIRM_ON_MACHINE,
        sources=_VOYAGER_SOURCES,
    )

    _terminal_update(
        monitor_key,
        f"your {brand} dealer — Voyager display updates are normally dealer-installed",
        _VOYAGER_SOURCES,
        dealer=True,
    )


_voyager_extras("case_ih.afs_pro_700", "Case IH")
_voyager_extras("new_holland.intelliview_iv", "New Holland")

_add(
    monitor_key="new_holland.intelliview_iv",
    objective="export_work_data",
    transport=Transport.USB,
    file_format="Display data package written by the IntelliView software",
    media_path="Drive root — the display creates its own folder tree",
    minutes=15,
    prerequisites=("Close the running job first, so the last of it is saved.",),
    steps=(
        _FAT32,
        "Close or pause the running task.",
        "Plug the stick into the display.",
        "Open «Data Management» and press «Export».",
        "Select the Grower / Farm / Field data you want.",
        "Confirm and wait for the transfer to complete.",
        _EJECT,
    ),
    verify=("The folder on the stick is not empty and carries today's date.",),
    cautions=("Use one stick for this machine only.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=_VOYAGER_SOURCES,
)


from ..families import _point_routes  # noqa: E402

_point_routes("case_ih.afs_pro_1200", _CNH_1200_SOURCES, vocabulary="Marker")
_point_routes("new_holland.intelliview_12", _CNH_IV12_SOURCES, vocabulary="Marker")
_point_routes("case_ih.afs_pro_700", _VOYAGER_SOURCES,
              vocabulary="Marker", file_kind="shapefile")
_point_routes("new_holland.intelliview_iv", _VOYAGER_SOURCES,
              vocabulary="Marker", file_kind="shapefile")
