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

# The Generation 4 operator manual (RE338096, 080714) states its USB rules
# outright, and two of them contradict what everyone assumes:
#
#   "Capacity - There are no specific limits to the memory capacity of the
#    drive"       -- so the 32 GB rule people carry over from the 2630 is not a
#                    Gen 4 rule, and a big stick is not the problem here.
#   "Maximum Dimensions - 9.2 mm thick by 21.7 mm wide"
#                 -- a physical limit. A fat stick does not fit the port, which
#                    looks exactly like a stick that "does not work".
#
# So Gen 4 gets its own media step rather than the shared one.
_GEN4_STICK = (
    "Format the stick FAT32. On a computer, right-click it, choose Format, "
    "pick FAT32 from the list, and press Start."
)
_GEN4_STICK_SIZE = (
    "There is no size limit on a Gen 4 — 4 GB or bigger is what John Deere "
    "suggests, so several backups fit."
)
_GEN4_SLIM = (
    "The port is narrow: the stick must be no thicker than 9.2 mm and no wider "
    "than 21.7 mm. A chunky one will not physically go in."
)
_GEN4_WAIT = (
    "After plugging in, give it about 10 seconds. A large stick takes a moment "
    "to be recognised, and people give up too early."
)
_GEN4_NTFS = (
    "The stick was formatted NTFS. This display does not read NTFS at all — it "
    "takes FAT or FAT32 only, and an NTFS stick simply never appears."
)
_GEN4_FAT = (
    "A stick straight out of the packet is often NTFS. Formatting it FAT32 is "
    "the one thing that has to be done first."
)

_add(
    monitor_key="john_deere.gen4",
    objective="import_prescription",
    transport=Transport.USB,
    file_format="Complete shapefile: .shp + .shx + .dbf + .prj, same base name",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="Rx\\  — at the ROOT of the stick, not inside another folder",
    minutes=15,
    prerequisites=(
        "The rate map has to be built for this: the field drawn as areas, and "
        "at least one rate column stored as numbers. The column name is what "
        "the display offers you as the rate, and it can be no longer than 10 "
        "characters.",
        "If the map arrived as a .zip, unzip it on the computer first. The "
        "display cannot open a zip.",
    ),
    steps=(
        _GEN4_STICK,
        _GEN4_SLIM,
        "At the ROOT of the stick create a folder named exactly Rx — capital "
        "R, small x, nothing else.",
        "Copy all four parts into Rx — the .shp, .shx, .dbf and .prj. Several "
        "fields can share one Rx folder.",
        "With the machine running, plug the stick into the display's USB port.",
        _GEN4_WAIT,
        "The display puts «USB Drive Options» on screen by itself. Press "
        "«Import Data», then «USB Drive».",
        "If that screen does not appear, go the long way: press «Menu», open "
        "the «System» tab, and select «File Manager».",
        "Press «Next», then pick the folder holding the prescription.",
        "Press «Import», then «OK». Taking 5 to 15 seconds to open is normal, "
        "not a fault.",
        "Now tell the machine to use it: press «Menu», then «Work Setup».",
        "On «Work Summary» set «Crop Type» and «Variety», then press "
        "«Target Rate/Rx» and choose your prescription.",
        "Press the «Rate Column» box and pick your rate from the "
        "«Select Rate Column» list.",
        "Press the «Rate Column Units» box and pick the unit — kg/ha, "
        "seeds/ha, whatever the map is in.",
    ),
    verify=(
        "The prescription map draws on the run screen over the right field.",
        "The rate legend shows sensible numbers, not zeros or blanks -- blanks "
        "mean the rate column was read as text.",
        "In «Fields and Boundaries», the client, farm and field are the ones "
        "you expect. Wrong here and the work files itself in the wrong place.",
    ),
    cautions=(
        _NO_ACCENTS,
        _EJECT,
        "One prescription can carry several rate columns, and different tanks "
        "or bins can each use a different column. Import it once.",
        "John Deere publishes a free JD Rx Converter on StellarSupport that "
        "fixes most files a display refuses. Try that before blaming the "
        "display.",
    ),
    common_errors=(
        _GEN4_NTFS,
        "The stick is physically too fat for the port. It looks like a display "
        "fault and is not one.",
        "The folder is named anything other than Rx — rx, RX, Prescriptions. "
        "The display simply does not see it.",
        "The Rx folder sits inside another folder instead of at the root.",
        "The map was saved in a different coordinate system rather than WGS84, "
        "which puts the field in the wrong place — sometimes in another "
        "country.",
        "The rates are stored as words rather than numbers. The map draws, but "
        "every rate reads as zero or blank.",
        "The rate column name is longer than 10 characters, so it arrives cut "
        "off or not at all.",
        "The file draws lines or dots rather than areas, so the display has "
        "nothing to apply a rate to.",
    ),
    confidence=Confidence.VERIFIED,
    sources=(
        "Generation 4 CommandCenter operator manual RE338096 (080714), "
        "File Manager 35-1 and USB Drive 35-2",
        "John Deere Gen 4 on-screen help — File Manager: Import Data",
        "John Deere Gen 4 on-screen help — Work Setup: Select Prescription, "
        "Prescription Rate Setup",
        "John Deere developer documentation, prescription file requirements",
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
        _GEN4_STICK,
        "Use a fresh stick, or one that holds only this display's data. Read "
        "the warning below before reusing one.",
        "End or pause the current job so the last of it is written.",
        "Plug the stick into the display's USB port and give it 10 seconds.",
        "Press «Menu», open the «System» tab, and select «File Manager». The "
        "«USB Drive Options» screen offers the same thing if it appears on its "
        "own.",
        "Press «Export Data».",
        "Tick what you want to send. «Work Data» is what the machine did, and "
        "goes into a folder called JD-Data.",
        "Note that ticking an option sends everything inside it. You are not "
        "picking single fields.",
        "If the office also needs your client, farm and field list, export "
        "«Setup Data» as well. That one writes into JD4600.",
        "Leave «Delete files after transfer» alone unless you mean it — and "
        "know that it only clears screenshots and error logs.",
        "Wait for the progress bar to finish completely.",
        _EJECT,
    ),
    verify=(
        "On a computer, confirm the JD-Data folder exists and is not empty.",
        "Upload it to Operations Center and check the field and the date look "
        "right before you wipe the stick.",
    ),
    cautions=(
        "The manual is blunt about this: exporting to a stick that already "
        "holds Generation 4 information OVERWRITES what is on it. Last week's "
        "export is gone, with no second chance. Empty the stick to a computer "
        "first.",
        "Exporting with the job still open can produce an incomplete file. "
        "Wait for the on-screen confirmation.",
        "«Delete files after transfer» does not clear your setup data or your "
        "guidance lines — only screenshots and error logs. Those are removed "
        "through «Fields» and the guidance application instead.",
    ),
    common_errors=(
        "Reusing a stick that already carries a Gen 4 export, and losing the "
        "earlier one.",
        "Using the same stick on more than one machine. The second machine can "
        "write over the first one's data without warning.",
        "Pulling the stick during the progress bar. The folder exists, looks "
        "plausible, and is short of the last part of the day.",
    ),
    confidence=Confidence.VERIFIED,
    sources=(
        "Generation 4 CommandCenter operator manual RE338096 (080714), "
        "File Manager 35-1: Export Data, Remove Data",
        "Gen 4 release notes: Work data goes to JD-Data, Setup data to JD4600",
    ),
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
        "Press the menu button, open «File Manager», then press «Import "
        "Data».",
        "Select the setup package and confirm.",
        "Choose REPLACE or MERGE. Choose MERGE unless you are certain.",
        "Open «Work Setup», go to «Guidance», and select the imported track.",
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
        "Press the menu button, open «File Manager», then press «Import "
        "Data».",
        "Select the package, choose MERGE, and confirm.",
        "Open «Work Setup», go to «Guidance», and select the track.",
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
        "Press the menu button and open «File Manager» to confirm the file "
        "arrived.",
        "Open «Work Setup», press «Target Rate/Rx», then set «Rate Column» "
        "and «Rate Column Units».",
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
        "On the display, press the menu button, open «System», then "
        "«Wireless Data Transfer», and confirm Data Sync is on.",
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
        "Press the menu button, open «File Manager», then press «Export "
        "Data».",
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
    file_format="Complete shapefile: .shp + .shx + .dbf + .prj, same base name",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="Rx\\  — at the ROOT of the stick, never inside another folder",
    minutes=15,
    prerequisites=(
        "The stick must be under 32 GB. The 2630 does not read larger ones, "
        "however new they are.",
        "If the map arrived zipped, unzip it on the computer first.",
    ),
    steps=(
        _FAT32,
        "At the ROOT of the stick create a folder named exactly Rx and copy "
        "all four parts into it — the .shp, .shx, .dbf and .prj.",
        "In the cab: stop the machine and switch off every kind of recording. "
        "The import option is greyed out while anything is recording.",
        "Let the display finish starting up FIRST, then plug the stick in. On "
        "this display the order matters.",
        "Wait about 10 seconds. A «Data Transfer» page comes up on its own.",
        "Choose the third option, «Import Shapefile Data».",
        "Pick your file and confirm.",
        "Go to the GreenStar setup and attach the prescription to the field, "
        "then choose the rate column.",
    ),
    verify=(
        "The prescription draws on the map page over the right field before "
        "you start.",
    ),
    cautions=(
        _NO_ACCENTS,
        "If «Import Shapefile Data» is greyed out, the files are in the wrong "
        "place — not a display fault. Take the stick back to the computer and "
        "check the Rx folder is at the root.",
        "If the display does not see the stick at all, try the other USB port "
        "before anything else.",
    ),
    common_errors=(
        "Plugging the stick in before the display has booted, so the "
        "«Data Transfer» page never appears.",
        "Leaving a recording running, which greys out the import.",
        "A stick larger than 32 GB.",
        "The Rx folder nested inside another folder.",
    ),
    confidence=Confidence.VERIFIED,
    sources=(
        "John Deere GreenStar GS2/GS3 prescription loading guide "
        "(Rx folder at root, Data Transfer page, Import Shapefile Data)",
        "John Deere GS3 2630 user guide",
    ),
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
        "Press «Menu», open «GreenStar 3», go to «Data», then press «Export».",
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
    media_path="Rx\\  — at the ROOT of the stick, not inside another folder",
    minutes=15,
    prerequisites=(
        "The field drawn as areas, and at least one rate column stored as "
        "numbers with a name of 10 characters or less.",
        "If the map arrived as a .zip, unzip it on the computer first.",
    ),
    steps=(
        _FAT32,
        "At the ROOT of the stick create a folder named exactly Rx — capital "
        "R, small x.",
        "Copy all four parts into Rx — the .shp, .shx, .dbf and .prj.",
        "With the machine running, plug the stick into the display's USB port.",
        "Wait a few seconds for «USB Drive Options» to appear, then press "
        "«Import Data» and «USB Drive».",
        "Press «Next», pick the folder holding the prescription, then «Import» "
        "and «OK».",
        "Press the menu button and open «Work Setup».",
        "On «Work Summary» set «Crop Type» and «Variety», then press "
        "«Target Rate/Rx» and choose your prescription.",
        "Press «Rate Column», pick the rate, then press «Rate Column Units» "
        "and pick the unit.",
    ),
    verify=(
        "The map draws over the right field with a sensible rate legend.",
        "The rates are numbers, not blanks. Blanks mean the column came through "
        "as text.",
    ),
    cautions=(
        _NO_ACCENTS,
        _EJECT,
        "The G5 runs the same data handling as Gen 4, so anything written for a "
        "4640 applies here — including the JD Rx Converter on StellarSupport.",
    ),
    common_errors=(
        "The folder is named anything other than Rx.",
        "The Rx folder sits inside another folder rather than at the root.",
        "The map is in a coordinate system other than WGS84, so the field "
        "lands somewhere else entirely.",
        "The rate column name is longer than 10 characters.",
    ),
    confidence=Confidence.VERIFIED,
    sources=(
        "John Deere Gen 4 / G5 on-screen help — File Manager: Import Data",
        "John Deere G5 and Generation 4 compatibility chart, StellarSupport",
    ),
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
        "Open «Work Setup», go to «Guidance», and select the track.",
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
        "Press the menu button, open «File Manager», then press «Import "
        "Data».",
        "Select the package, choose MERGE, and confirm.",
        "Open «Work Setup», go to «Field», and confirm the boundary is "
        "attached.",
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
        "Press the menu button, open «File Manager», then press «Import "
        "Data».",
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
        "Press the menu button, open «File Manager», then press «Export "
        "Data».",
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
        "Press the menu button, open «File Manager», then press «Export "
        "Data».",
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
        "Press the menu button, open «System», then «Software Manager».",
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
        "Open «Work Setup», go to «Field», and confirm the boundary is "
        "attached.",
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
        "On the display, press the menu button, open «System», then "
        "«Wireless Data Transfer», and confirm sync is on.",
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
        "Press «Menu», open «GreenStar 3», go to «Data», then press «Import».",
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
        "Press «Menu», open «GreenStar 3», go to «Data», then press «Export».",
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
        "Press «Menu», open «GreenStar 3», then «Software Manager». The "
        "wording moves a little between releases.",
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

# The shared by-hand route ends in "drive to the spot with your phone, then
# mark where you are" -- honest for a display whose manual we have not read.
# The Gen 4 manual names the screen outright, so this display answers for
# itself and skips the generic version rather than offering two answers.
_GEN4_LATLON_SOURCES = (
    "Generation 4 CommandCenter operator manual RE338096 (080714), "
    "Guidance 25-5 Set Guidance Track and 25-6 Straight Track",
)

_add(
    monitor_key="john_deere.gen4",
    objective="import_point",
    transport=Transport.MANUAL,
    file_format="None — you type the numbers in",
    media_path="",
    filesystem="n/a",
    minutes=10,
    prerequisites=(
        "This display really does take coordinates typed in, which most do "
        "not. It does it while defining a guidance track, so what you get is a "
        "line through your point rather than a loose flag.",
        "Have the numbers written down as decimal degrees before you climb in.",
    ),
    steps=(
        "Press «Menu», open the «Applications» tab, and select «Fields».",
        "Set the «Client», «Farm» and «Field» this point belongs to. Get this "
        "right first — the coordinates are filed under it.",
        "Go to the main guidance page and press «SET TRACK».",
        "On the «Guidance Track List», press the add button to make a new "
        "track.",
        "Choose «Straight Track». It now asks how to define Track 0, and two of "
        "the methods let you type coordinates instead of driving.",
        "EITHER pick «Lat/Long» and type latitude and longitude for both the A "
        "and the B point — use this when you have two known corners.",
        "OR pick «Lat/Long + Heading» and type latitude and longitude for the A "
        "point only, then a heading in degrees — use this when you have one "
        "point and know the direction.",
        "Key the numbers in as decimal degrees, minus signs included.",
        "Save the track with a name you will recognise next season.",
    ),
    verify=(
        "The track draws through the point you meant, not somewhere else in the "
        "district. If it is far away, check the minus signs first.",
        "Drive to the A end and confirm the machine is where you expect on the "
        "ground.",
    ),
    cautions=(
        "Write coordinates as plain decimal degrees — -27.845123, -54.477456 — "
        "with south and west negative. Degrees-and-minutes is a different "
        "notation and lands the point kilometres away.",
        "A Gen 4 stores data as latitude and longitude, not against the field "
        "name — the manual says so. The name is only a filter, which is why a "
        "typo in the coordinates cannot be fixed by renaming anything.",
        "Track 0 can be defined mid-job, planting included, though some buttons "
        "are unavailable while you are creating it.",
        "If you only need a rough position and not a line, the simpler route is "
        "to drive to the spot with a phone map and mark a flag there.",
    ),
    common_errors=(
        "Latitude and longitude the wrong way round. In this part of the world "
        "latitude is the smaller number and both are negative.",
        "Dropping the minus sign, which puts the field in the northern "
        "hemisphere.",
        "Using the «Quick Line» softkey by mistake. It makes a line with no "
        "setup and no name, and pressing it again OVERWRITES the last one. To "
        "keep a Quick Line, open the guidance track list, press edit, and "
        "rename it.",
    ),
    confidence=Confidence.VERIFIED,
    sources=_GEN4_LATLON_SOURCES,
)

_point_routes("john_deere.gen4", ("John Deere StellarSupport, Gen 4 File Manager",),
              vocabulary="Flag", file_kind="shapefile",
              media_path="Setup file folder written by Operations Center",
              skip=("manual",))
# The G5 runs the same operating system and the same guidance application, so
# the track methods are the same screens.
_mirror(
    "john_deere.gen4",
    "john_deere.g5",
    [("import_point", Transport.MANUAL)],
    extra_sources=("John Deere G5 and Generation 4 compatibility chart",),
)

_point_routes("john_deere.g5", ("John Deere StellarSupport, G5 data management",),
              vocabulary="Flag", file_kind="shapefile", skip=("manual",),
              media_path="Setup file folder written by Operations Center")
_point_routes("john_deere.gs3_2630",
              ("John Deere StellarSupport, legacy display data management",),
              vocabulary="Flag", file_kind="shapefile",
              media_path="GS3_2630\\<Profile>\\RCD\\")
