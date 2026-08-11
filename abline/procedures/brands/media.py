"""Preparing the USB stick -- applies to every display with a USB port."""

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
#  Media preparation -- applies to everything with a USB port                 #
# =========================================================================== #

for _monitor in (
    "john_deere.gen4",
    "john_deere.g5",
    "john_deere.gs3_2630",
    "case_ih.afs_pro_700",
    "case_ih.afs_pro_1200",
    "new_holland.intelliview_iv",
    "new_holland.intelliview_12",
    "trimble.precision_iq",
    "trimble.fmx",
    "ag_leader.incommand",
    "raven.viper4",
    "topcon.x_family",
    "claas.cemis_1200",
    "claas.s10",
    "agco.fendt_one",
    "agco.valtra_smarttouch",
    "agco.mf_datatronic",
    "kverneland.isomatch",
    "mueller.track_leader",
    "precision_planting.2020",
    "teejet.matrix_pro_gs",
    "generic.isobus",
):
    _add(
        monitor_key=_monitor,
        objective="prepare_media",
        transport=Transport.USB,
        file_format="n/a — this prepares the stick itself",
        media_path="n/a",
        minutes=5,
        steps=(
            "Use a stick between 8 GB and 32 GB. Larger sticks are the most "
            "common cause of an import list that comes up empty.",
            "Plug it into a computer.",
            "Right-click the drive in File Explorer and choose Format.",
            "Set the file system to FAT32.",
            "Tick Quick Format and press Start.",
            "Give the stick a short label with no accents or spaces.",
            "Copy your files on, following the folder layout for your display.",
            "Safely eject from the computer before unplugging.",
        ),
        verify=(
            "The computer reports the drive as FAT32 in its properties.",
            "The display lists your files when you open the import screen.",
        ),
        cautions=(
            "Formatting erases the stick. Copy anything you need off it first.",
            "Use one stick per machine. Sharing one stick across displays "
            "overwrites folder trees that share a name.",
        ),
        common_errors=(
            "exFAT or NTFS instead of FAT32.",
            "A stick larger than 32 GB.",
            "A GPT partition table where the display expects MBR.",
        ),
        confidence=Confidence.VERIFIED,
        sources=("Manufacturer data-management documentation, consolidated",),
    )
