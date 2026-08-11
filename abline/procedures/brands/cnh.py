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
    version_key=("pro700_28", "pro700_29"),
    file_format="Complete shapefile, files loose at the drive root",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="Drive root — the display browses the stick itself",
    minutes=15,
    steps=(
        _FAT32,
        _SHP_SET,
        "Leave the files LOOSE at the drive root, not inside a folder.",
        "Plug the stick into the display's USB port.",
        "Go to Toolbox > Data Management.",
        "Choose the shapefile import option.",
        "Select the Grower, Farm and Field the prescription belongs to.",
        "Select the file, then choose the rate column and the unit.",
        "Confirm and wait for the import to finish.",
    ),
    verify=("The prescription draws on the run screen over the right field.",),
    cautions=(
        "Case IH ships a branded USB stick (part 84398840). Any properly "
        "formatted FAT32 stick works, but if one misbehaves that is the "
        "known-good one.",
        _EJECT,
    ),
    common_errors=(
        "Copying only the .shp file.",
        "Leaving the files inside a folder.",
    ),
    confidence=Confidence.VERIFIED,
    sources=("Case IH AFS Pro 700 shapefile import guide",),
)

_add(
    monitor_key="case_ih.afs_pro_700",
    objective="import_prescription",
    transport=Transport.USB,
    version_key="pro700_30",
    file_format="Complete shapefile, files loose at the drive root",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="Drive root",
    minutes=15,
    steps=(
        _FAT32,
        _SHP_SET,
        "Leave the files LOOSE at the drive root.",
        "Plug the stick into the display's USB port.",
        "On this software line the import lives under Toolbox > Swath / Data, "
        "rather than Data Management. If you do not see it, check both.",
        "Choose the shapefile import.",
        "Select Grower, Farm and Field.",
        "Select the file, the rate column and the unit.",
    ),
    verify=("The prescription draws over the right field.",),
    cautions=(
        "Menu wording moved between the 28.x and 30.x software lines. The file "
        "itself is identical — only the path through the menus changed.",
    ),
    common_errors=("Following 28.x instructions and concluding the file is bad.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("Case IH AFS Pro 700 software operating guide",),
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
        "Go to Toolbox > Swath.",
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
    common_errors=("Copying only the .shp file.",),
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
        "Toolbox > Data Management > Export.",
        "Select the Grower / Farm / Field data you want.",
        "Confirm and wait for the transfer to complete.",
        _EJECT,
        "At the office, import the folder into AFS Software or your FMIS.",
    ),
    verify=("The folder on the stick is not empty and carries today's date.",),
    cautions=("Use one stick per machine to avoid overwriting folder trees.",),
    common_errors=("Removing the stick before the transfer finishes.",),
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
        "TASKDATA appears, containing TASKDATA.XML.",
        "Plug the stick into the display.",
        "Open the data management / import screen.",
        "Run the ISOXML import and select the task data on the stick.",
        "Confirm the field and its guidance lines appear.",
        "On the run screen, select the line.",
    ),
    verify=("The field and its reference lines are listed after the import.",),
    cautions=(
        "The folder must be named TASKDATA, capitals, at the root. Nested one "
        "level deeper it will not be found.",
        "CNH publishes its own ADAPT plugin for this format, so ISOXML is a "
        "well-supported route here rather than a hopeful one.",
    ),
    common_errors=(
        "Leaving the download zipped on the stick.",
        "A TASKDATA folder inside another TASKDATA folder after unzipping.",
        "Renaming TASKDATA.XML — the name is fixed by the standard.",
    ),
    confidence=Confidence.VERIFIED,
    sources=(
        "CNH developer portal, ISOXML ADAPT plugin guide",
        "Case IH AFS Pro 1200 software operating manual",
    ),
)

_add(
    monitor_key="case_ih.afs_pro_1200",
    objective="import_prescription",
    transport=Transport.USB,
    file_format="ISOXML task data, or a complete shapefile",
    extensions=(".xml", ".shp", ".shx", ".dbf", ".prj"),
    media_path="TASKDATA\\ at the drive ROOT (ISOXML), or the root (shapefile)",
    minutes=10,
    steps=(
        _FAT32,
        "For ISOXML: unzip at the root so TASKDATA\\TASKDATA.XML exists.",
        "For a shapefile: put all four parts loose at the root.",
        "Plug the stick in and open the data management screen.",
        "Run the import and pick the file.",
        "Attach the prescription to the field, then choose the rate column "
        "and unit.",
    ),
    verify=("The rate map draws over the right field with sensible values.",),
    cautions=(_NO_ACCENTS,),
    common_errors=("Mixing an ISOXML TASKDATA folder and loose shapefiles on one stick.",),
    confidence=Confidence.VERIFIED,
    sources=("CNH developer portal, ISOXML ADAPT plugin guide",),
)

_add(
    monitor_key="case_ih.afs_pro_1200",
    objective="export_work_data",
    transport=Transport.USB,
    file_format="ISOXML task data written by the display",
    extensions=(".xml", ".bin"),
    media_path="TASKDATA\\ — created by the display on the stick",
    minutes=15,
    prerequisites=("Close the running task first.",),
    steps=(
        _FAT32,
        "Close the running task.",
        "Plug the stick into the display.",
        "Open data management and choose Export.",
        "Select the tasks or the whole task data set.",
        "Wait for completion, then eject from the menu.",
        "At the office, read the TASKDATA folder with any ISOXML-capable FMIS.",
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
    media_path="Drive root",
    minutes=15,
    steps=(
        _FAT32,
        _SHP_SET,
        "Leave the four files loose at the drive root.",
        "Plug the stick in.",
        "Toolbox > Swath > import from USB.",
        "Select Grower, Farm and Field, then the file.",
        "Pick the swath on the run screen.",
    ),
    verify=("The swath draws where you expect.",),
    cautions=(
        "IntelliView IV and the Case IH AFS Pro 700 are the same display in "
        "different paint. Anything that imports on one imports on the other.",
    ),
    common_errors=("Copying only the .shp file.",),
    confidence=Confidence.VERIFIED,
    sources=("Case IH / New Holland Voyager display documentation",),
)

_add(
    monitor_key="new_holland.intelliview_iv",
    objective="import_prescription",
    transport=Transport.USB,
    file_format="Complete shapefile, or ISOXML / CN1 on later software",
    extensions=(".shp", ".shx", ".dbf", ".prj", ".xml"),
    media_path="Drive root",
    minutes=15,
    steps=(
        _FAT32,
        _SHP_SET,
        "Plug the stick in.",
        "Toolbox > Data Management > Import.",
        "Select Grower, Farm and Field.",
        "Select the prescription, then the rate column and unit.",
    ),
    verify=("The rate map draws over the right field.",),
    cautions=("Later IntelliView IV software also accepts ISOXML and CN1 format.",),
    common_errors=("Rate column stored as text.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("New Holland IntelliView IV documentation",),
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

_cloud_route("case_ih.afs_pro_1200", "AFS Connect", _CNH_1200_SOURCES)
_cloud_route("new_holland.intelliview_12", "PLM Connect", _CNH_IV12_SOURCES)


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
            "Toolbox > Data Management (or Field, depending on software line).",
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
            "Line geometry instead of polygon.",
            "Copying only the .shp file.",
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
            "Toolbox > Data Management.",
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
            "Toolbox > Data Management > Export.",
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
            "Toolbox > Data Management > Export.",
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
            "Toolbox > Data Management > Export.",
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
    prerequisites=("Close the running task so the last records are written.",),
    steps=(
        _FAT32,
        "Close or pause the running task.",
        "Plug the stick into the display.",
        "Toolbox > Data Management > Export.",
        "Select the Grower / Farm / Field data you want.",
        "Confirm and wait for the transfer to complete.",
        _EJECT,
    ),
    verify=("The folder on the stick is not empty and carries today's date.",),
    cautions=("Use one stick per machine to avoid overwriting folder trees.",),
    common_errors=("Removing the stick before the transfer finishes.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=_VOYAGER_SOURCES,
)
