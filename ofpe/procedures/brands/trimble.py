"""Trimble: Precision-IQ (GFX / TMX) and the older AgGPS generation."""

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
#  TRIMBLE                                                                    #
# =========================================================================== #

_add(
    monitor_key="trimble.precision_iq",
    objective="import_prescription",
    transport=Transport.USB,
    file_format="Complete shapefile, files loose inside the Prescriptions folder",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="AgData\\Prescriptions\\  — at the drive root",
    minutes=10,
    steps=(
        _FAT32,
        "At the root of the stick create a folder named AgData.",
        "Inside AgData create a folder named Prescriptions.",
        "Put the four shapefile parts LOOSE inside Prescriptions — not in a "
        "further subfolder.",
        "Give every part the same base name. Precision-IQ matches them by name.",
        "Plug the stick into the display.",
        "On the home screen, tap «Data Transfer».",
        "Choose the USB drive as the source, then import the prescription.",
        "Attach it to the field and choose the rate column and unit.",
    ),
    verify=("The rate map draws over the right field.",),
    cautions=(
        "Prescriptions genuinely are loose shapefiles in AgData\\Prescriptions. "
        "Guidance lines are NOT — those go through Trimble Ag Software.",
        _NO_ACCENTS,
    ),
    common_errors=(
        "Putting the shapefile in AgData directly instead of "
        "AgData\\Prescriptions.",
        "Nesting the files one folder deeper.",
    ),
    confidence=Confidence.VERIFIED,
    sources=("Trimble Precision-IQ data management documentation",),
)

_add(
    monitor_key="trimble.precision_iq",
    objective="import_guidance",
    transport=Transport.DESKTOP,
    file_format="Shapefile into Trimble Ag Software, which writes the display file",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="AgData\\ — written by Trimble Ag Software, do not hand-build it",
    minutes=30,
    prerequisites=(
        "Trimble's own .agdata container is AES encrypted and cloud-keyed. No "
        "third party can write one. This route is not a workaround; it is the "
        "supported path.",
    ),
    steps=(
        "Import the shapefile into Trimble Ag Software, desktop or web.",
        "Attach it to the matching client / farm / field as a guidance line.",
        "If the machine has connectivity, sync over the air and stop here.",
        "Otherwise export from Trimble Ag Software onto a USB stick — it "
        "writes the AgData folder for you.",
        "Plug the stick into the display.",
        "On the home screen, tap «Data Transfer», choose the USB drive, and "
        "import the field.",
        "Select the line on the run screen.",
    ),
    verify=("The line appears under the correct field in Precision-IQ.",),
    cautions=(
        "Do not try to hand-build an AgData folder. The display validates it "
        "and will reject it.",
    ),
    common_errors=("Expecting a loose shapefile to import as a guidance line.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("Trimble Ag Software desktop release notes",),
)

_add(
    monitor_key="trimble.precision_iq",
    objective="export_work_data",
    transport=Transport.USB,
    file_format="AgData package written by the display (encrypted container)",
    media_path="AgData\\ — created by the display",
    minutes=15,
    steps=(
        _FAT32,
        "Close the running task.",
        "Plug the stick into the display.",
        "On the home screen, tap «Data Transfer».",
        "Choose to export data to the USB.",
        "Select the fields or the whole data set.",
        "Wait for completion and eject.",
        "At the office, import the AgData folder into Trimble Ag Software.",
    ),
    verify=("Trimble Ag Software lists the job after import.",),
    cautions=(
        "The exported .agdata is encrypted. It can only be opened by Trimble "
        "Ag Software or the Trimble cloud — no third-party tool will read it.",
    ),
    common_errors=(
        "Expecting to open the export in QGIS or Excel. Export from Trimble Ag "
        "Software to shapefile first if you need that.",
    ),
    confidence=Confidence.VERIFIED,
    sources=("Trimble Precision-IQ data management documentation",),
)

_add(
    monitor_key="trimble.fmx",
    objective="import_prescription",
    transport=Transport.USB,
    file_format="Complete shapefile in the AgGPS structure",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="AgGPS\\Prescriptions\\  — note AgGPS, not AgData",
    minutes=15,
    steps=(
        _FAT32,
        "Create AgGPS\\Prescriptions at the root of the stick.",
        "Put the four shapefile parts loose inside Prescriptions.",
        "Plug the stick into the display.",
        "Open the «Data» screen, choose «USB», and read from the stick.",
        "Attach the prescription to the field and set the rate column.",
    ),
    verify=("The rate map draws over the right field.",),
    cautions=(
        "This generation uses AgGPS, the newer GFX/TMX uses AgData. Files from "
        "one will not drop straight into the other.",
    ),
    common_errors=("Using an AgData folder on an FmX.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("Trimble legacy display data management documentation",),
)


# --------------------------------------------------------------------------- #
#  The rest of the Trimble jobs                                                #
# --------------------------------------------------------------------------- #

from ..families import _cloud_route, _terminal_update  # noqa: E402

_PIQ_SOURCES = ("Trimble Precision-IQ data management documentation",)
_TRIMBLE_AG = "Trimble Ag Software"

_add(
    monitor_key="trimble.precision_iq",
    objective="import_boundary",
    transport=Transport.DESKTOP,
    file_format="Shapefile into Trimble Ag Software, which writes the display file",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="AgData\\ — written by Trimble Ag Software, do not hand-build it",
    minutes=30,
    prerequisites=(
        "Boundaries travel inside the encrypted AgData container along with the "
        "field record, so they take the same route as guidance lines: through "
        "Trimble's own software.",
    ),
    steps=(
        "Import the boundary shapefile into Trimble Ag Software.",
        "Attach it to the matching client / farm / field.",
        "Sync over the air if the machine has connectivity, and stop here.",
        "Otherwise export to a USB stick — Trimble Ag Software writes the "
        "AgData folder for you.",
        "On the display, tap «Data Transfer», choose the USB drive, and import the "
        "field.",
    ),
    verify=(
        "The boundary draws around the field on the run screen.",
        "Section control switches off at the line, if you run it.",
    ),
    cautions=(
        "Prescriptions are the exception on this display: those genuinely are "
        "loose shapefiles in AgData\\Prescriptions. Boundaries and guidance "
        "lines are not.",
    ),
    common_errors=(
        "Putting a boundary shapefile in AgData\\Prescriptions and expecting it "
        "to become a boundary.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=_PIQ_SOURCES,
)

_add(
    monitor_key="trimble.precision_iq",
    objective="import_setup",
    transport=Transport.DESKTOP,
    file_format="Client / farm / field structure from Trimble Ag Software",
    media_path="AgData\\ — written by Trimble Ag Software",
    minutes=25,
    prerequisites=(
        "Set the names up once, in Trimble Ag Software, and push them out. "
        "Names typed in the cab drift between machines and split one field's "
        "records across several.",
    ),
    steps=(
        "In Trimble Ag Software, confirm the client / farm / field names.",
        "Sync to the display over the air, or export to USB.",
        "On the display, tap «Data Transfer» and import from the USB drive.",
        "Check the field list on the display matches the office.",
    ),
    verify=("The display's field list matches Trimble Ag Software.",),
    cautions=(
        "Two spellings of one field name means two sets of records that have to "
        "be merged by hand later.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=_PIQ_SOURCES,
)

_add(
    monitor_key="trimble.precision_iq",
    objective="export_guidance",
    transport=Transport.USB,
    file_format="AgData package written by the display (encrypted container)",
    media_path="AgData\\ — created by the display",
    minutes=15,
    steps=(
        _FAT32,
        "Plug the stick into the display.",
        "On the home screen, tap «Data Transfer».",
        "Export the field data to the USB — lines travel with the field record.",
        "Wait for completion and eject.",
        "At the office, import the AgData folder into Trimble Ag Software.",
        "From there, export to shapefile if you need the lines in another system.",
    ),
    verify=("Trimble Ag Software lists the lines under the right field.",),
    cautions=(
        "The .agdata container is AES encrypted and cloud-keyed. Trimble Ag "
        "Software is the only thing that will open it — no third-party tool "
        "will, including this platform. Convert to shapefile there if you need "
        "the geometry elsewhere.",
    ),
    common_errors=("Trying to open the export in QGIS or Excel.",),
    confidence=Confidence.VERIFIED,
    sources=_PIQ_SOURCES,
)

_add(
    monitor_key="trimble.precision_iq",
    objective="export_boundary",
    transport=Transport.USB,
    file_format="AgData package written by the display",
    media_path="AgData\\ — created by the display",
    minutes=15,
    steps=(
        _FAT32,
        "Plug the stick into the display and open Data Transfer.",
        "Export the field data to USB.",
        "Import the AgData folder into Trimble Ag Software at the office.",
        "Export to shapefile from there if another system needs it.",
    ),
    verify=("The boundary appears in Trimble Ag Software where you expect.",),
    cautions=(
        "Same encrypted container as everything else here — the conversion to "
        "an open format happens in Trimble Ag Software, not on the stick.",
    ),
    confidence=Confidence.VERIFIED,
    sources=_PIQ_SOURCES,
)

_add(
    monitor_key="trimble.precision_iq",
    objective="export_backup",
    transport=Transport.USB,
    file_format="Complete AgData export",
    media_path="AgData\\",
    minutes=25,
    prerequisites=("Do this before a firmware update and before a trade-in.",),
    steps=(
        _FAT32,
        "Close the running task.",
        "Tap «Data Transfer» and export everything, not a single field.",
        "Wait for the write to finish and eject.",
        "Copy the AgData folder somewhere backed up, and import it into "
        "Trimble Ag Software so there is a readable copy too.",
    ),
    verify=(
        "Trimble Ag Software imports the folder without errors and shows the "
        "fields you expected.",
    ),
    cautions=(
        "An encrypted backup you have never test-imported is not a backup. "
        "Import it once at the office to prove it opens.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=_PIQ_SOURCES,
)

_terminal_update("trimble.precision_iq", "the Trimble support portal or your dealer",
                 _PIQ_SOURCES)
_terminal_update("trimble.fmx", "the Trimble support portal or your dealer",
                 ("Trimble legacy display data management documentation",))

_cloud_route("trimble.precision_iq", _TRIMBLE_AG, _PIQ_SOURCES)

_add(
    monitor_key="trimble.fmx",
    objective="import_guidance",
    transport=Transport.DESKTOP,
    file_format="Shapefile into Trimble Ag Software or the legacy Farm Works desktop",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="AgGPS\\ — written by the desktop software",
    minutes=30,
    steps=(
        "Import the shapefile into Trimble Ag Software, or the legacy Farm "
        "Works desktop if that is what this machine has always used.",
        "Attach it to the field.",
        "Export to USB — the software writes the AgGPS folder structure.",
        "On the display, open the «Data» screen, choose «USB», and read from "
        "the stick.",
        "Select the line before engaging the steering.",
    ),
    verify=("The line appears in the display's line list for that field.",),
    cautions=(
        "This generation uses AgGPS, not AgData. A stick written for a GFX or "
        "TMX will not be read by an FmX, and the reverse is also true.",
    ),
    common_errors=("Mixing AgData and AgGPS folder structures on one stick.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("Trimble legacy display data management documentation",),
)

_add(
    monitor_key="trimble.fmx",
    objective="export_work_data",
    transport=Transport.USB,
    file_format="AgGPS data package written by the display",
    media_path="AgGPS\\",
    minutes=15,
    steps=(
        _FAT32,
        "End the running job.",
        "Plug the stick into the display.",
        "Open the «Data» screen, choose «USB», and write to the stick.",
        "Wait for the write to finish before removing it.",
        "At the office, read the AgGPS folder with Trimble Ag Software or "
        "Farm Works.",
    ),
    verify=("The AgGPS folder exists on the stick and is not empty.",),
    cautions=(
        "These displays are old enough that the internal storage is often the "
        "only copy of several seasons. Export before doing anything else to one.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("Trimble legacy display data management documentation",),
)

_add(
    monitor_key="trimble.fmx",
    objective="export_backup",
    transport=Transport.USB,
    file_format="Complete AgGPS export",
    media_path="AgGPS\\",
    minutes=25,
    steps=(
        _FAT32,
        "End the running job.",
        "Open the «Data» screen, choose «USB», and export everything on the "
        "display rather than one field.",
        "Wait for completion, then copy the AgGPS folder somewhere backed up.",
        "Import it into desktop software once, to prove it reads.",
    ),
    verify=("The desktop software opens the export and lists your fields.",),
    cautions=(
        "This generation is being retired across the industry. Get the data off "
        "before the display fails, not after.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("Trimble legacy display data management documentation",),
)


from ..families import _point_routes  # noqa: E402

_point_routes("trimble.precision_iq", _PIQ_SOURCES,
              vocabulary="Landmark", file_kind="shapefile",
              media_path="AgData\\ — written by Trimble Ag Software")
_point_routes("trimble.fmx", ("Trimble legacy display data management documentation",),
              vocabulary="Landmark", file_kind="shapefile",
              media_path="AgGPS\\ — written by the desktop software")
