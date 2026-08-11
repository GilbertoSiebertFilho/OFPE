"""John Deere: GreenStar 3 2630, Gen 4 CommandCenter, G5."""

from __future__ import annotations

from ..families import _point_routes
from .._core import (
    ANY_VERSION,
    _mirror,
    Confidence,
    Transport,
    _add,
    _EJECT,
    _FAT32,
    _NO_ACCENTS,
    _SHP_SET,
)

# =========================================================================== #
#  JOHN DEERE                                                                 #
# =========================================================================== #

_add(
    monitor_key="john_deere.gen4",
    objective="import_prescription",
    transport=Transport.USB,
    file_format="Complete shapefile: .shp + .shx + .dbf + .prj, same base name",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="Rx\\  — at the ROOT of the stick, not inside another folder",
    minutes=10,
    prerequisites=(
        "The rate map has to be built for this, with the rates stored as "
        "numbers and the field drawn as an area. If somebody else prepared "
        "it, they will know whether it is right; if it draws with blank or "
        "zero rates on the display, it is not.",
    ),
    steps=(
        _FAT32,
        "At the ROOT of the stick create a folder named exactly Rx.",
        "Copy the four shapefile parts into Rx.",
        "With the machine powered up, plug the stick into the display's USB port.",
        "Tap the Menu button, bottom left of the screen.",
        "Open File Manager.",
        "Choose Import Data, select the USB as the source, and tick the prescription.",
        "Confirm and wait for the progress bar to finish.",
        "Go to Work Setup > Field > Prescription, choose the file, then choose "
        "the RATE COLUMN and the UNIT.",
    ),
    verify=(
        "The prescription map draws on the run screen in the right place.",
        "The rate legend shows sensible numbers, not zeros or blanks -- blanks "
        "mean the rate column was read as text.",
    ),
    cautions=(_NO_ACCENTS, _EJECT),
    common_errors=(
        "The .prj part is missing, so the display does not know where on Earth "
        "the map belongs and draws it in the wrong place.",
        "The map was saved using a different coordinate system, which puts the "
        "field in the wrong place — sometimes in another country.",
        "The rates in the file are stored as words rather than numbers. The map "
        "draws, but every rate reads as zero or blank.",
        "The Rx folder nested inside another folder.",
        "The file draws lines or dots rather than areas, so the display has "
        "nothing to apply a rate to.",
    ),
    confidence=Confidence.VERIFIED,
    sources=(
        "John Deere StellarSupport, Gen 4 File Manager",
        "Gen 4 CommandCenter release notes",
    ),
)

_add(
    monitor_key="john_deere.gen4",
    objective="export_work_data",
    transport=Transport.USB,
    file_format="Display data package (folders the display creates itself)",
    media_path="Work data -> JD-Data\\   |   Setup data -> JD4600\\",
    minutes=15,
    prerequisites=("Finish or pause the job first, so the last of it is saved.",),
    steps=(
        _FAT32,
        "Use one stick for this machine only.",
        "End or pause the current job.",
        "Plug the stick into the display's USB port.",
        "Menu > File Manager.",
        "Choose Export Data.",
        "Choose Work Data — the display writes into a JD-Data folder.",
        "If you also need the client/farm/field structure, choose Setup Data — "
        "that writes into JD4600.",
        "Wait for the progress bar to finish completely.",
        _EJECT,
    ),
    verify=(
        "On a computer, confirm the JD-Data folder exists and is not empty.",
        "Import it into Operations Center and check the field and date look right.",
    ),
    cautions=(
        "Exporting with the job still open can produce an incomplete file. "
        "Always wait for the on-screen confirmation.",
    ),
    common_errors=(
        "Using the same stick on more than one machine. The second machine can "
        "write over the first one's data without warning.",
    ),
    confidence=Confidence.VERIFIED,
    sources=("John Deere StellarSupport, Generation 4 Displays File Manager",),
)

_add(
    monitor_key="john_deere.gen4",
    objective="import_guidance",
    transport=Transport.USB,
    version_key=("gen4_10x", "gen4_11x"),
    file_format="Setup file exported from Operations Center for a Gen 4 display",
    media_path="JD4600\\  — the setup folder Operations Center writes",
    minutes=20,
    prerequisites=(
        "There is no open guidance-line file for this display. The line has to "
        "pass through Operations Center first.",
    ),
    steps=(
        "In Operations Center, select the client, farm and field, and the "
        "guidance lines you want.",
        "Generate a setup file for a Gen 4 display and download it.",
        "Copy the generated folder to the ROOT of the stick, keeping its "
        "structure exactly as downloaded.",
        "Plug the stick into the display.",
        "Menu > File Manager > Import Data.",
        "Select the setup package and confirm.",
        "Choose REPLACE or MERGE. Choose MERGE unless you are certain.",
        "Open Work Setup > Guidance and select the imported track.",
    ),
    verify=(
        "The track name appears in the guidance list under the right field.",
        "Drive one pass with steering off and confirm the machine tracks it.",
    ),
    cautions=(
        "REPLACE erases setup data already on the display. MERGE is the safe "
        "choice.",
    ),
    common_errors=(
        "Renaming or reorganising the folders inside the package — the display "
        "stops recognising it.",
        "Importing a setup package built for a different display generation.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("John Deere Operations Center / StellarSupport",),
)

_add(
    monitor_key="john_deere.gen4",
    objective="import_guidance",
    transport=Transport.USB,
    version_key="gen4_2025_3",
    file_format="Setup file exported from Operations Center (Current System Display format)",
    media_path="JD4600\\  — the setup folder Operations Center writes",
    minutes=20,
    prerequisites=(
        "From the 2025-3 update onward, setup files built by Apex or by a "
        "legacy display are NO LONGER accepted directly. They must be uploaded "
        "to Operations Center first and re-exported in the current format.",
    ),
    steps=(
        "If your file came from Apex or an older display, upload it to "
        "Operations Center first and let it convert.",
        "In Operations Center, select client, farm, field and the guidance lines.",
        "Generate a setup file in the Current System Display format and download it.",
        "Copy the folder to the ROOT of the stick, unchanged.",
        "Plug the stick into the display.",
        "Menu > File Manager > Import Data.",
        "Select the package, choose MERGE, and confirm.",
        "Open Work Setup > Guidance and select the track.",
    ),
    verify=(
        "The import preview lists your tracks before you confirm. If the "
        "preview is empty, the file is in the old format.",
    ),
    cautions=(
        "If two tracks share a name, the display renames the incoming one — "
        "Track1 becomes Track1(1) rather than overwriting.",
    ),
    common_errors=(
        "Trying to import an Apex-era setup file directly. On this release it "
        "will simply not appear.",
    ),
    confidence=Confidence.VERIFIED,
    sources=(
        "John Deere StellarSupport, Generation 4 and G5 data management, "
        "2025-3 release notes",
    ),
)

_add(
    monitor_key="john_deere.gen4",
    objective="import_prescription",
    transport=Transport.CLOUD,
    file_format="Prescription published in Operations Center, sent over the air",
    media_path="",
    filesystem="n/a — wireless",
    minutes=10,
    prerequisites=(
        "The machine needs an active MTG / JDLink connection and must show as "
        "connected in Operations Center.",
    ),
    steps=(
        "Confirm the machine appears as connected in Operations Center.",
        "Upload the prescription under Files, or build it in Operations Center.",
        "Attach it to the correct client, farm and field.",
        "Use Send to Machine and pick the target machine.",
        "In the cab, accept the incoming transfer notification.",
        "Menu > File Manager to confirm the file arrived.",
        "Work Setup > Prescription: select the file, the rate column and the unit.",
    ),
    verify=("The map draws on the run screen with a sensible rate legend.",),
    cautions=(
        "Wireless transfer needs an active data subscription. If Send to "
        "Machine is greyed out, that is usually why.",
    ),
    common_errors=(
        "Sending to the wrong machine in a fleet with similar names.",
        "The operator never accepting the notification in the cab.",
    ),
    confidence=Confidence.VERIFIED,
    sources=("John Deere Operations Center documentation",),
)

_add(
    monitor_key="john_deere.gen4",
    objective="export_work_data",
    transport=Transport.CLOUD,
    file_format="Automatic sync to Operations Center",
    media_path="",
    filesystem="n/a — wireless",
    minutes=5,
    prerequisites=("MTG / JDLink active and the machine paired to the organisation.",),
    steps=(
        "Confirm the machine is connected in Operations Center.",
        "Confirm Data Sync is enabled on the display: Menu > System > "
        "Wireless Data Transfer.",
        "Work data uploads on its own as the job runs — no operator action.",
        "In Operations Center, open Field Analyzer to see the coverage arrive.",
        "If a job is missing, end the job in the cab to force the final upload.",
    ),
    verify=("The job appears in Operations Center with the expected area.",),
    cautions=(
        "Wireless sync does not remove the need for an occasional USB backup. "
        "A machine that loses connectivity mid-season buffers, but not forever.",
    ),
    common_errors=(
        "Assuming sync is on when it was never enabled on the display.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("John Deere Operations Center / JDLink documentation",),
)

_add(
    monitor_key="john_deere.gen4",
    objective="export_guidance",
    transport=Transport.USB,
    file_format="Setup data package written by the display",
    media_path="JD4600\\",
    minutes=10,
    steps=(
        _FAT32,
        "Plug the stick into the display.",
        "Menu > File Manager > Export Data.",
        "Choose Setup Data (not Work Data) — guidance lines live in setup.",
        "Select the client, farm and fields whose tracks you want.",
        "Wait for the progress bar, then eject from the menu.",
        "At the office, upload the JD4600 folder to Operations Center.",
    ),
    verify=(
        "The JD4600 folder exists on the stick and is not empty.",
        "Operations Center lists the tracks against the right fields after upload.",
    ),
    cautions=(
        "Guidance lines are setup data, not work data. Exporting only Work Data "
        "will not include them, which surprises people.",
    ),
    common_errors=("Exporting Work Data and wondering where the tracks went.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("John Deere StellarSupport, Gen 4 File Manager",),
)

_add(
    monitor_key="john_deere.gs3_2630",
    objective="import_prescription",
    transport=Transport.USB,
    file_format=(
        "A setup profile built by Operations Center. You feed Operations "
        "Center a shapefile; it writes the profile the 2630 reads."
    ),
    media_path="GS3_2630\\<Profile>\\RCD\\",
    minutes=20,
    prerequisites=(
        "The 2630 does not browse a bare stick. Data must sit inside the "
        "GS3_2630 profile structure written by Deere software.",
    ),
    steps=(
        _FAT32,
        "In Operations Center, build a setup file for a Legacy System Display "
        "including the prescription.",
        "Write it to the stick from Operations Center — it creates the "
        "GS3_2630 folder structure for you.",
        "Plug the stick into the 2630.",
        "Menu > GreenStar 3 > Data > Import.",
        "Select the profile and confirm.",
        "Under Field Setup, attach the prescription to the field and choose the "
        "rate column.",
    ),
    verify=("The prescription draws on the map page before you start.",),
    cautions=(
        "Apex is discontinued; use Operations Center.",
        "Do not hand-build the GS3_2630 folder tree — the display validates it.",
    ),
    common_errors=(
        "Copying a loose shapefile to the stick root. The 2630 will not see it.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("John Deere StellarSupport, legacy display data management",),
)

_add(
    monitor_key="john_deere.gs3_2630",
    objective="export_work_data",
    transport=Transport.USB,
    file_format="GS3 data package",
    media_path="GS3_2630\\<Profile>\\RCD\\",
    minutes=15,
    steps=(
        _FAT32,
        "Finish the job first, so the last of it is saved.",
        "Plug the stick into the 2630.",
        "Menu > GreenStar 3 > Data > Export.",
        "Select the profile and confirm.",
        "Wait for the confirmation message before removing the stick.",
        "At the office, upload the whole GS3_2630 folder to Operations Center.",
    ),
    verify=("Operations Center shows the job with the expected area and date.",),
    cautions=("Upload the entire folder, not selected files inside it.",),
    common_errors=("Uploading only the RCD contents without the parent folders.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("John Deere StellarSupport, legacy display data management",),
)

_add(
    monitor_key="john_deere.g5",
    objective="import_prescription",
    transport=Transport.USB,
    file_format="Complete shapefile: .shp + .shx + .dbf + .prj, same base name",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="Rx\\  — at the ROOT of the stick",
    minutes=10,
    prerequisites=("The file has to be a proper rate map, not a picture of one. If you did "
        "not build it yourself, the person who sent it will know.",),
    steps=(
        _FAT32,
        "Create a folder named exactly Rx at the ROOT of the stick.",
        "Copy the four shapefile parts into it.",
        "Plug the stick into the display.",
        "Menu > System > File Manager > Import Data.",
        "Select the prescription and confirm.",
        "Work Setup > Prescription: pick the file, the rate column and the unit.",
    ),
    verify=("The map draws with a sensible rate legend.",),
    cautions=(_NO_ACCENTS, _EJECT),
    common_errors=(
        "The .prj part is missing, so the field lands in the wrong place.",
        "Rx folder nested inside another folder.",
    ),
    confidence=Confidence.VERIFIED,
    sources=("John Deere G5 and Generation 4 compatibility chart, StellarSupport",),
)

_add(
    monitor_key="john_deere.g5",
    objective="import_guidance",
    transport=Transport.CLOUD,
    file_format="Guidance line published in Operations Center",
    media_path="",
    filesystem="n/a — wireless",
    minutes=10,
    prerequisites=("Machine connected via JDLink and visible in Operations Center.",),
    steps=(
        "Upload or draw the guidance line in Operations Center and attach it to "
        "the field.",
        "Use Send to Machine and select the machine.",
        "In the cab, accept the incoming transfer.",
        "Work Setup > Guidance: select the track.",
    ),
    verify=("The track appears under the correct field in the guidance list.",),
    cautions=(
        "This is the easiest route into a Deere display by a wide margin. If "
        "the machine has JDLink, use it instead of a USB stick.",
    ),
    confidence=Confidence.VERIFIED,
    sources=("John Deere Operations Center guidance line documentation",),
)


# --------------------------------------------------------------------------- #
#  Boundaries, setup, backup and software                                      #
# --------------------------------------------------------------------------- #
# On a Deere display, boundaries and guidance lines are both *setup* data and
# travel in the same package. That is the single most useful thing to know here:
# people look for a separate boundary import and there is not one.

_OPS_CENTER = "John Deere Operations Center"

_add(
    monitor_key="john_deere.gen4",
    objective="import_boundary",
    transport=Transport.USB,
    file_format="Setup file exported from Operations Center",
    media_path="JD4600\\  — the setup folder Operations Center writes",
    minutes=20,
    prerequisites=(
        "Boundaries are setup data on this display, exactly like guidance "
        "lines. There is no separate boundary import — do not go looking for "
        "one.",
    ),
    steps=(
        "Upload the boundary shapefile to Operations Center, or draw it there.",
        "Attach it to the correct client, farm and field.",
        "Generate a setup file for the display and download it.",
        "Copy the folder to the ROOT of the stick, unchanged.",
        "Plug the stick into the display.",
        "Menu > File Manager > Import Data.",
        "Select the package, choose MERGE, and confirm.",
        "Open Work Setup > Field and confirm the boundary is attached.",
    ),
    verify=(
        "The boundary draws around the field on the map page.",
        "Section control switches off when you cross the line, if you run it.",
    ),
    cautions=(
        "A boundary with a hole in it (a slough, a tower base) must be drawn as "
        "an interior ring, not as a second polygon, or section control will "
        "treat the hole as workable ground.",
    ),
    common_errors=("Looking for a boundary-only import that does not exist.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("John Deere StellarSupport, Gen 4 data management",),
)

_add(
    monitor_key="john_deere.gen4",
    objective="import_setup",
    transport=Transport.USB,
    file_format="Setup file exported from Operations Center",
    media_path="JD4600\\ at the drive root",
    minutes=20,
    prerequisites=(
        "Do this FIRST, before any other import. Every later export files "
        "itself under the client / farm / field names on the display, so "
        "getting them right once saves renaming everything later.",
    ),
    steps=(
        "In Operations Center, confirm the client, farm and field names are "
        "the ones you want to see in reports.",
        "Generate a setup file for the display and download it.",
        "Copy the folder to the ROOT of the stick, unchanged.",
        "Menu > File Manager > Import Data.",
        "Choose MERGE, not REPLACE, unless the display is being commissioned.",
        "Confirm the client / farm / field list on the display matches.",
    ),
    verify=("Work Setup shows your client, farm and field names.",),
    cautions=(
        "REPLACE wipes what is on the display. On a machine that has been "
        "working, that loses any field the operator created in the cab.",
    ),
    common_errors=(
        "Importing setup after a season's work and overwriting in-cab field "
        "names the operator has been using.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("John Deere StellarSupport, Gen 4 File Manager",),
)

_add(
    monitor_key="john_deere.gen4",
    objective="export_boundary",
    transport=Transport.USB,
    file_format="Setup data package written by the display",
    media_path="JD4600\\",
    minutes=10,
    prerequisites=(
        "A boundary recorded by driving the perimeter is usually the most "
        "accurate outline anyone has of that field. Worth pulling off even if "
        "you think you already have one.",
    ),
    steps=(
        _FAT32,
        "Plug the stick into the display.",
        "Menu > File Manager > Export Data.",
        "Choose Setup Data — boundaries live in setup, not in work data.",
        "Select the client, farm and fields you want.",
        "Wait for the progress bar, then eject from the menu.",
        "Upload the JD4600 folder to Operations Center.",
    ),
    verify=("Operations Center shows the boundary against the right field.",),
    cautions=(
        "Guidance lines come out in the same package. If you only wanted "
        "boundaries you will get both, which is rarely a problem.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("John Deere StellarSupport, Gen 4 File Manager",),
)

_add(
    monitor_key="john_deere.gen4",
    objective="export_backup",
    transport=Transport.USB,
    file_format="Work data package plus setup data package",
    media_path="JD-Data\\ (work)  +  JD4600\\ (setup)",
    minutes=25,
    prerequisites=(
        "Do this before a software update and before the machine changes "
        "hands. Both are moments when data goes missing and nobody notices "
        "until months later.",
    ),
    steps=(
        _FAT32,
        "Use a stick with room to spare — a season of work data is not small.",
        "End the running job.",
        "Menu > File Manager > Export Data.",
        "Export Work Data. Wait for it to finish.",
        "Export Setup Data as well — it is a separate action.",
        _EJECT,
        "Copy both folders somewhere that gets backed up, then upload to "
        "Operations Center.",
    ),
    verify=(
        "Both JD-Data and JD4600 exist on the stick and neither is empty.",
        "Operations Center accepts the upload without errors.",
    ),
    cautions=(
        "Work data and setup data are two separate exports. Exporting only one "
        "is the most common way a 'backup' turns out to be half a backup.",
    ),
    common_errors=("Exporting Work Data only and calling it a backup.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("John Deere StellarSupport, Gen 4 File Manager",),
)

_add(
    monitor_key="john_deere.gen4",
    objective="software_update",
    transport=Transport.USB,
    file_format="Gen 4 software update package from StellarSupport",
    media_path="Drive root — the installer creates its own folders",
    minutes=60,
    prerequisites=(
        "Take a full backup first. An update is the classic moment to lose a "
        "season of data.",
        "The machine must be parked, running or on a battery charger. A "
        "display that loses power mid-update can need a dealer to recover.",
    ),
    steps=(
        _FAT32,
        "On a PC, go to John Deere StellarSupport and find your display.",
        "Download the update and run the installer, pointing it at the USB "
        "stick. It writes the folder structure itself — do not rearrange it.",
        "Plug the stick into the display with the machine running.",
        "Menu > System > Software Manager.",
        "Select the update on the USB and start the installation.",
        "Do NOT switch off, and do not remove the stick, until the display "
        "restarts on its own.",
        "After the restart, check Software Manager shows the new version.",
    ),
    verify=(
        "Software Manager reports the version you installed.",
        "Your fields, guidance lines and boundaries are still there.",
    ),
    cautions=(
        "Allow an hour and do it in the yard, not at the end of a field.",
        "From the 2025-3 update onward, setup files from Apex or a legacy "
        "display stop importing directly — plan for that before you update.",
    ),
    common_errors=(
        "Updating with no backup.",
        "Switching the machine off partway through.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("John Deere StellarSupport, Generation 4 software downloads",),
)

_add(
    monitor_key="john_deere.gen4",
    objective="import_boundary",
    transport=Transport.CLOUD,
    platform=_OPS_CENTER,
    file_format="Boundary held in Operations Center, sent over the air",
    media_path="",
    filesystem="n/a — wireless",
    minutes=10,
    prerequisites=("MTG / JDLink active and the machine visible in the portal.",),
    steps=(
        "In Operations Center, open Land and confirm the field boundary.",
        "Use Send to Machine and pick the machine.",
        "In the cab, accept the incoming transfer.",
        "Work Setup > Field: confirm the boundary is attached.",
    ),
    verify=("The boundary draws on the map page in the cab.",),
    cautions=(
        "This is far and away the easiest route into a Deere display. If the "
        "machine has JDLink, do not reach for a USB stick.",
    ),
    confidence=Confidence.VERIFIED,
    sources=("John Deere Operations Center documentation",),
)

_add(
    monitor_key="john_deere.gen4",
    objective="export_guidance",
    transport=Transport.CLOUD,
    platform=_OPS_CENTER,
    file_format="Automatic sync of setup data to Operations Center",
    media_path="",
    filesystem="n/a — wireless",
    minutes=5,
    prerequisites=("MTG / JDLink active, and Data Sync enabled on the display.",),
    steps=(
        "On the display: Menu > System > Wireless Data Transfer, and confirm "
        "sync is on.",
        "Lines recorded in the cab upload on their own.",
        "In Operations Center, open the field and check the guidance line list.",
        "From there the line can be sent on to any other machine in the fleet.",
    ),
    verify=("The line appears in Operations Center under the right field.",),
    cautions=(
        "This is how a line recorded by one operator reaches the rest of the "
        "fleet without anyone driving a stick around.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("John Deere Operations Center documentation",),
)

# The G5 shares the Gen 4 data model, so the same procedures apply verbatim.
_mirror(
    "john_deere.gen4",
    "john_deere.g5",
    [
        ("import_boundary", Transport.USB),
        ("import_setup", Transport.USB),
        ("export_boundary", Transport.USB),
        ("export_guidance", Transport.USB),
        ("export_work_data", Transport.USB),
        ("export_backup", Transport.USB),
        ("software_update", Transport.USB),
        ("import_boundary", Transport.CLOUD),
        ("export_guidance", Transport.CLOUD),
        ("export_work_data", Transport.CLOUD),
    ],
    extra_cautions=(
        "G5 and Gen 4 share setup-file handling, so anything documented for "
        "one applies to the other.",
    ),
    extra_sources=("John Deere G5 and Generation 4 compatibility chart",),
)


_add(
    monitor_key="john_deere.gs3_2630",
    objective="import_boundary",
    transport=Transport.USB,
    file_format="Setup profile built by Operations Center",
    media_path="GS3_2630\\<Profile>\\RCD\\",
    minutes=20,
    steps=(
        _FAT32,
        "In Operations Center, attach the boundary to the field.",
        "Build a setup file for a Legacy System Display and write it to the "
        "stick from Operations Center.",
        "Plug the stick into the 2630.",
        "Menu > GreenStar 3 > Data > Import.",
        "Select the profile and confirm.",
    ),
    verify=("The boundary draws on the map page.",),
    cautions=("Do not hand-build the GS3_2630 tree; the display validates it.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("John Deere StellarSupport, legacy display data management",),
)

_add(
    monitor_key="john_deere.gs3_2630",
    objective="export_guidance",
    transport=Transport.USB,
    file_format="GS3 profile package",
    media_path="GS3_2630\\<Profile>\\RCD\\",
    minutes=15,
    steps=(
        _FAT32,
        "Plug the stick into the 2630.",
        "Menu > GreenStar 3 > Data > Export.",
        "Select the profile and confirm.",
        "Wait for the confirmation before removing the stick.",
        "Upload the whole GS3_2630 folder to Operations Center to read the "
        "lines and pass them to newer machines.",
    ),
    verify=("Operations Center lists the tracks after the upload.",),
    cautions=(
        "This is the route for rescuing years of lines off an ageing 2630 "
        "before it is retired.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("John Deere StellarSupport, legacy display data management",),
)

_add(
    monitor_key="john_deere.gs3_2630",
    objective="software_update",
    transport=Transport.USB,
    file_format="GS3 software update package from StellarSupport",
    media_path="Drive root — the installer creates its own folders",
    minutes=60,
    prerequisites=("Export the profile first. Treat an update as data-risky.",),
    steps=(
        _FAT32,
        "Download the GS3 update from StellarSupport and run the installer "
        "against the USB stick.",
        "Plug the stick into the 2630 with the machine running.",
        "Menu > GreenStar 3 > Software Manager (wording varies by release).",
        "Start the update and leave the machine running until it restarts.",
        "Confirm the new version afterwards.",
    ),
    verify=("The display reports the new version and your data is intact.",),
    cautions=("Allow an hour, in the yard, with the machine running.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("John Deere StellarSupport, GreenStar 3 software downloads",),
)


# --------------------------------------------------------------------------- #
#  Points through Operations Center                                            #
# --------------------------------------------------------------------------- #
# Deere calls a marked point a Flag, and Operations Center is the good route
# here: you place it on the map at the office and it reaches the cab without
# anyone typing a coordinate into a display.

for _jd_monitor in ("john_deere.gen4", "john_deere.g5"):
    _add(
        monitor_key=_jd_monitor,
        objective="import_point",
        transport=Transport.CLOUD,
        platform=_OPS_CENTER,
        file_format="A flag placed in Operations Center, sent over the air",
        media_path="",
        filesystem="n/a — wireless",
        minutes=10,
        prerequisites=(
            "The machine needs JDLink and must show as connected in Operations "
            "Center. This is the tidiest way to get a point into a Deere cab: "
            "nobody has to key in a coordinate.",
        ),
        steps=(
            "In Operations Center, open Land and select the field.",
            "Switch on the map view and place a flag at the position you want.",
            "If you have the coordinates rather than a spot on the map, paste "
            "them into the search box to jump there first.",
            "Name the flag something the operator will recognise.",
            "Send the field to the machine, or let it sync on its own.",
            "In the cab, open the field and check the flag is on the map.",
        ),
        verify=(
            "The flag appears on the display's map in the right place.",
            "Its name matches what you typed at the office.",
        ),
        cautions=(
            "Deere calls a marked point a Flag. Look for that word, not "
            "'marker' or 'waypoint'.",
            "Write coordinates as decimal degrees — -27.845123, -54.477456 — "
            "with south and west negative.",
            "Flags dropped by the operator in the cab come back the same way, "
            "so this works in both directions once sync is on.",
        ),
        common_errors=(
            "Placing the flag on the wrong field when two fields have similar "
            "names.",
        ),
        confidence=Confidence.CONFIRM_ON_MACHINE,
        sources=("John Deere Operations Center documentation",),
    )

    _add(
        monitor_key=_jd_monitor,
        objective="export_point",
        transport=Transport.CLOUD,
        platform=_OPS_CENTER,
        file_format="Flags sync back to Operations Center on their own",
        media_path="",
        filesystem="n/a — wireless",
        minutes=5,
        prerequisites=("JDLink active and data sync enabled on the display.",),
        steps=(
            "Flags the operator drops in the cab upload by themselves.",
            "In Operations Center, open the field and look at the map.",
            "Export them from there if your agronomy software needs them.",
        ),
        verify=("The operator's flags appear against the right field.",),
        cautions=(
            "This is the cheapest field record anyone makes: the operator taps "
            "once when they see a problem, and it is on the office map before "
            "they finish the pass.",
        ),
        confidence=Confidence.CONFIRM_ON_MACHINE,
        sources=("John Deere Operations Center documentation",),
    )

_point_routes("john_deere.gen4", ("John Deere StellarSupport, Gen 4 File Manager",),
              vocabulary="Flag", file_kind="shapefile",
              media_path="Setup file folder written by Operations Center")
_point_routes("john_deere.g5", ("John Deere StellarSupport, G5 data management",),
              vocabulary="Flag", file_kind="shapefile",
              media_path="Setup file folder written by Operations Center")
_point_routes("john_deere.gs3_2630",
              ("John Deere StellarSupport, legacy display data management",),
              vocabulary="Flag", file_kind="shapefile",
              media_path="GS3_2630\\<Profile>\\RCD\\")
