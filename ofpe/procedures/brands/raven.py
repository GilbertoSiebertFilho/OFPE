"""Raven: Viper 4 and the GFF folder tree."""

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
#  RAVEN                                                                      #
# =========================================================================== #

_add(
    monitor_key="raven.viper4",
    objective="import_guidance",
    transport=Transport.USB,
    file_format="Guidance line files inside the GFF folder tree",
    extensions=(".ab",),
    media_path="Raven\\GFF\\<Grower>\\<Farm>\\<Field>\\abLines\\",
    minutes=15,
    prerequisites=(
        "The Grower / Farm / Field folder names should match what is already on "
        "the display, or the lines land under a newly created field.",
    ),
    steps=(
        _FAT32,
        "Build the folder tree on the stick: "
        "Raven\\GFF\\<Grower>\\<Farm>\\<Field>\\abLines",
        "Put the line files in the abLines folder.",
        "Plug the stick into the display.",
        "Touch the «Administrator» or «User» panel along the top of the main "
        "screen to open it out.",
        "Select the «File Manager» utility.",
        "Touch the «USB Manager» tab.",
        "Touch the USB drop-down and pick the stick you just plugged in.",
        "Tick the box to the left of each line you want, or touch «Select All» "
        "at the top of the list.",
        "Touch «Copy». That brings the lines in and leaves them on the stick. "
        "«Move» also works but deletes them from the stick, so only use it if "
        "you mean to.",
    ),
    verify=("The imported lines appear in the guidance list for that field.",),
    cautions=(
        "The folder tree is documented in Raven's manual; the internal layout "
        "of a .ab file is not something we have been able to confirm. If the "
        "import lists nothing, use a shapefile instead and tell us.",
    ),
    common_errors=(
        "Grower / farm / field names that do not match the display, creating a "
        "duplicate field.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("Raven Viper installation and operator's manual, import guidance lines",),
)

_add(
    monitor_key="raven.viper4",
    objective="export_work_data",
    transport=Transport.USB,
    file_format="Field operation files in the GFF tree",
    media_path="Raven\\GFF\\<Grower>\\<Farm>\\<Field>\\",
    minutes=15,
    steps=(
        _FAT32,
        "Plug the stick into the display.",
        "Open the USB manager.",
        "Choose to export field operation files.",
        "Select the grower, farm and field.",
        "Confirm and wait for the transfer.",
        "At the office, read the GFF tree, or upload through Slingshot.",
    ),
    verify=("The Raven\\GFF tree on the stick contains the field folder.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("Raven Viper installation and operator's manual",),
)


# --------------------------------------------------------------------------- #
#  The rest of the Raven jobs                                                  #
# --------------------------------------------------------------------------- #

from ..families import _cloud_route, _terminal_update  # noqa: E402

_RAVEN_SOURCES = ("Raven Viper installation and operator's manual",)
_GFF = r"Raven\GFF\<Grower>\<Farm>\<Field>"

_add(
    monitor_key="raven.viper4",
    objective="import_boundary",
    transport=Transport.USB,
    file_format="Boundary files inside the GFF folder tree",
    media_path=_GFF + r"\boundaries",
    minutes=15,
    prerequisites=(
        "Grower / Farm / Field folder names must match what is already on the "
        "display, or the boundary lands under a newly created field.",
    ),
    steps=(
        _FAT32,
        f"Build the tree on the stick: {_GFF}\\boundaries",
        "Put the boundary file in that folder.",
        "Plug the stick into the display.",
        "Touch the «Administrator» or «User» panel along the top of the main "
        "screen, then select «File Manager».",
        "Touch the «USB Manager» tab and pick the stick from the USB drop-down.",
        "Tick the boundary, then touch «Copy».",
    ),
    verify=("The boundary draws around the field on the run screen.",),
    cautions=(
        "The GFF tree is documented in Raven's manual; the internal layout of "
        "the individual files is not something we have confirmed. If the import "
        "lists nothing, try a shapefile and tell us what your display wrote.",
    ),
    common_errors=(
        "Folder names that do not match the display, creating a duplicate field.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=_RAVEN_SOURCES,
)

_add(
    monitor_key="raven.viper4",
    objective="import_setup",
    transport=Transport.USB,
    file_format="The GFF folder tree itself is the structure",
    media_path=r"Raven\GFF\<Grower>\<Farm>\<Field>",
    minutes=15,
    prerequisites=(
        "On this display the folder names ARE the setup. Grower, Farm and Field "
        "are literally directory names on the stick, so spelling them the way "
        "your office does is not cosmetic.",
    ),
    steps=(
        _FAT32,
        "Create Raven\\GFF at the root of the stick.",
        "Inside it create one folder per grower, then farm, then field, spelled "
        "exactly as your office records them.",
        "Plug the stick in and import through the USB manager.",
        "Confirm the names appear on the display as you typed them.",
    ),
    verify=("The display's grower / farm / field list matches the office.",),
    cautions=(
        "Because the structure is folder names, a typo is silent: you get a "
        "second field rather than an error.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=_RAVEN_SOURCES,
)

_add(
    monitor_key="raven.viper4",
    objective="export_guidance",
    transport=Transport.USB,
    file_format="Guidance line files written into the GFF tree",
    extensions=(".ab",),
    media_path=_GFF + r"\abLines",
    minutes=15,
    steps=(
        _FAT32,
        "Plug the stick into the display.",
        "Open the USB manager and choose to export field operation files.",
        "Select Guidance Lines as the file type.",
        "Select the grower, farm and field.",
        "Confirm and wait for the transfer.",
        "The lines land in the abLines folder inside the field's directory.",
    ),
    verify=("The abLines folder on the stick contains your lines.",),
    cautions=(
        "This is the best way to see the real .ab file layout. If you can send "
        "us one, we can write that format directly instead of falling back to "
        "shapefile.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=_RAVEN_SOURCES,
)

_add(
    monitor_key="raven.viper4",
    objective="export_boundary",
    transport=Transport.USB,
    file_format="Boundary files written into the GFF tree",
    media_path=_GFF + r"\boundaries",
    minutes=15,
    steps=(
        _FAT32,
        "Plug the stick into the display and open the USB manager.",
        "Choose to export field operation files.",
        "Select the boundary file type and the field.",
        "Confirm and wait for the transfer.",
    ),
    verify=("The boundary file appears in the field's folder on the stick.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=_RAVEN_SOURCES,
)

_add(
    monitor_key="raven.viper4",
    objective="export_backup",
    transport=Transport.USB,
    file_format="The whole Raven\\GFF tree",
    media_path="Raven\\GFF\\",
    minutes=25,
    prerequisites=("Do this before a software update and before a trade-in.",),
    steps=(
        _FAT32,
        "Use a stick with room to spare.",
        "Open the USB manager and export every grower / farm / field, not one.",
        "Wait for the transfer to complete.",
        "Copy the entire Raven folder somewhere that gets backed up.",
    ),
    verify=("The Raven\\GFF tree on the stick contains every field you expected.",),
    cautions=(
        "The folder tree is human-readable, which makes this backup unusually "
        "easy to check: open it and look.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=_RAVEN_SOURCES,
)

_terminal_update("raven.viper4", "the Raven support portal", _RAVEN_SOURCES)
_cloud_route("raven.viper4", "Raven Slingshot", _RAVEN_SOURCES)


from ..families import _point_routes  # noqa: E402

_point_routes("raven.viper4", _RAVEN_SOURCES,
              vocabulary="Field marker", file_kind="shapefile",
              media_path=_GFF + "\\markers")
