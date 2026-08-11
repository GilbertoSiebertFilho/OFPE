"""Ag Leader: InCommand and the SMS / AgFiniti ecosystem."""

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
#  AG LEADER                                                                  #
# =========================================================================== #

_add(
    monitor_key="ag_leader.incommand",
    objective="import_prescription",
    transport=Transport.USB,
    version_key=("ic_1_3", "ic_4_9", "ic_10"),
    file_format=".agsetup exported from SMS, or a complete shapefile",
    extensions=(".agsetup", ".shp", ".shx", ".dbf", ".prj"),
    media_path="Drive root",
    minutes=15,
    steps=(
        _FAT32,
        "Put the .agsetup file, or the four shapefile parts, at the drive root.",
        "Plug the stick into the display.",
        "Tap the status indicator in the top right corner.",
        "Choose Data Transfer from the drop-down.",
        "Tap Import Setup and find the file on the stick.",
        "Confirm the import.",
        "Attach the prescription to the field and choose the rate column.",
    ),
    verify=("The rate map draws over the right field.",),
    cautions=(
        ".agsetup files are forward compatible but not backward. A file written "
        "by newer software may not open on an older display.",
    ),
    confidence=Confidence.VERIFIED,
    sources=(
        "Ag Leader support portal, AgSetup file supported uses",
        "Ag Leader InCommand display user guide",
    ),
)

_add(
    monitor_key="ag_leader.incommand",
    objective="import_guidance",
    transport=Transport.DESKTOP,
    file_format="Shapefile into SMS, which exports the .agsetup the display reads",
    extensions=(".agsetup",),
    media_path="Drive root",
    minutes=30,
    prerequisites=(
        "The .agsetup container is Ag Leader's own and is not publicly "
        "documented, so it cannot be written directly by third-party software.",
    ),
    steps=(
        "Import the shapefile into SMS Software, Basic or Advanced.",
        "Attach it to the field as a guidance pattern.",
        "Export an .agsetup file from SMS to a USB stick, or push it through "
        "AgFiniti.",
        "Plug the stick into the display.",
        "Tap the status indicator, top right.",
        "Choose Data Transfer, then Import Setup.",
        "Select the .agsetup and confirm.",
        "Select the pattern on the run screen.",
    ),
    verify=("The pattern appears in the guidance list for that field.",),
    cautions=(
        "This display calls an AB line a Pattern. Look for Pattern, A+ heading, "
        "Adaptive Curve or SmartPath.",
    ),
    common_errors=("Expecting a loose shapefile to import as a guidance pattern.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("Ag Leader support portal, AgSetup file supported uses",),
)

_add(
    monitor_key="ag_leader.incommand",
    objective="export_work_data",
    transport=Transport.USB,
    file_format=".agdata — the logged operation data",
    extensions=(".agdata",),
    media_path="Drive root",
    minutes=15,
    prerequisites=("End the operation so the last records are written.",),
    steps=(
        _FAT32,
        "Finish the job on the display first.",
        "Plug the stick into the display.",
        "Tap the status indicator, top right.",
        "Choose Data Transfer.",
        "Tap Export and choose the logged data.",
        "Wait for completion and eject.",
        "At the office, import the .agdata into SMS.",
    ),
    verify=("SMS lists the operation with the expected area after import.",),
    cautions=(
        ".agsetup carries setup — fields, boundaries, patterns. .agdata carries "
        "what the machine did. They are different files and you usually want both.",
    ),
    common_errors=("Exporting only setup and losing the season's records.",),
    confidence=Confidence.VERIFIED,
    sources=("Ag Leader InCommand display user guide",),
)

_add(
    monitor_key="ag_leader.incommand",
    objective="export_guidance",
    transport=Transport.USB,
    file_format=".agsetup — guidance patterns live in setup, not in data",
    extensions=(".agsetup",),
    media_path="Drive root",
    minutes=10,
    steps=(
        _FAT32,
        "Plug the stick into the display.",
        "Tap the status indicator, top right, then Data Transfer.",
        "Choose Export Setup (not Export Data).",
        "Select the fields whose patterns you want.",
        "Wait for completion and eject.",
        "Open the .agsetup in SMS to view or convert the patterns.",
    ),
    verify=("SMS lists the patterns under the right fields.",),
    cautions=("Guidance patterns are setup data. Exporting only .agdata misses them.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("Ag Leader support portal, AgSetup file supported uses",),
)


# --------------------------------------------------------------------------- #
#  The rest of the Ag Leader jobs                                              #
# --------------------------------------------------------------------------- #
# The .agsetup / .agdata split runs through everything here and is the thing to
# understand: setup carries fields, boundaries and patterns; data carries what
# the machine did. Almost every "where did it go" question on this display is
# someone exporting one and expecting the other.

from ..families import _cloud_route, _terminal_update  # noqa: E402

_AGL_SOURCES = (
    "Ag Leader support portal, AgSetup file supported uses",
    "Ag Leader InCommand display user guide",
)

_add(
    monitor_key="ag_leader.incommand",
    objective="import_boundary",
    transport=Transport.USB,
    file_format=".agsetup from SMS, or a complete shapefile with POLYGON geometry",
    extensions=(".agsetup", ".shp", ".shx", ".dbf", ".prj"),
    media_path="Drive root",
    minutes=15,
    steps=(
        _FAT32,
        _SHP_SET,
        "Put the .agsetup, or the four shapefile parts, at the drive root.",
        "Plug the stick into the display.",
        "Tap the status indicator in the top right corner.",
        "Choose Data Transfer, then Import Setup.",
        "Select the file and confirm.",
        "Check the boundary is attached to the right field.",
    ),
    verify=(
        "The boundary draws around the field on the map.",
        "Section control shuts off at the line, if you run it.",
    ),
    cautions=(
        "Boundaries are setup data. They arrive in .agsetup, never in .agdata.",
    ),
    common_errors=("The file draws the field as an outline rather than an area. It imports "
        "and then behaves as if there is no boundary at all.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=_AGL_SOURCES,
)

_add(
    monitor_key="ag_leader.incommand",
    objective="import_setup",
    transport=Transport.USB,
    file_format=".agsetup exported from SMS",
    extensions=(".agsetup",),
    media_path="Drive root",
    minutes=15,
    prerequisites=(
        "Do this first. Everything the display records afterwards files itself "
        "under these grower / farm / field names.",
    ),
    steps=(
        "In SMS, confirm the grower / farm / field structure is the one your "
        "office reports on.",
        "Export an .agsetup and copy it to the drive root.",
        "Status indicator > Data Transfer > Import Setup.",
        "Select the file and confirm.",
    ),
    verify=("The display's field list matches SMS.",),
    cautions=(
        ".agsetup files are forward compatible but not backward. A file written "
        "by newer software may not open on an older display.",
    ),
    confidence=Confidence.VERIFIED,
    sources=_AGL_SOURCES,
)

_add(
    monitor_key="ag_leader.incommand",
    objective="export_boundary",
    transport=Transport.USB,
    file_format=".agsetup — boundaries live in setup, not in data",
    extensions=(".agsetup",),
    media_path="Drive root",
    minutes=10,
    steps=(
        _FAT32,
        "Plug the stick into the display.",
        "Status indicator > Data Transfer.",
        "Choose Export Setup, not Export Data.",
        "Select the fields whose boundaries you want.",
        "Wait for completion and eject.",
        "Open the .agsetup in SMS to view or convert them.",
    ),
    verify=("SMS lists the boundaries under the right fields.",),
    cautions=(
        "Exporting .agdata will not include boundaries. This is the single most "
        "common mix-up on this display.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=_AGL_SOURCES,
)

_add(
    monitor_key="ag_leader.incommand",
    objective="export_backup",
    transport=Transport.USB,
    file_format="Both files: .agsetup for setup and .agdata for the records",
    extensions=(".agsetup", ".agdata"),
    media_path="Drive root",
    minutes=25,
    prerequisites=("Do this before a firmware update and before a trade-in.",),
    steps=(
        _FAT32,
        "Finish the job on the display first.",
        "Status indicator > Data Transfer.",
        "Export Setup — this is your fields, boundaries and patterns.",
        "Then Export Data — this is what the machine actually did.",
        "Both are needed. Exporting one is half a backup.",
        _EJECT,
        "Import both into SMS once, to prove they read.",
    ),
    verify=(
        "Both an .agsetup and an .agdata are on the stick.",
        "SMS imports both without errors.",
    ),
    cautions=(
        "Setup and data are two separate exports on this display. Almost every "
        "'we lost the season' story starts with someone exporting only one.",
    ),
    common_errors=("Exporting .agdata only and calling it a backup.",),
    confidence=Confidence.VERIFIED,
    sources=_AGL_SOURCES,
)

_terminal_update("ag_leader.incommand", "the Ag Leader support portal", _AGL_SOURCES)
_cloud_route("ag_leader.incommand", "AgFiniti", _AGL_SOURCES)


from ..families import _point_routes  # noqa: E402

_point_routes("ag_leader.incommand", _AGL_SOURCES,
              vocabulary="Marker", file_kind="shapefile")
