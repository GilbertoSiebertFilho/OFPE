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
            "Pick a stick of 8 GB to 32 GB. Bigger ones often are not read at "
            "all, however new they are.",
            "Plug it into a computer.",
            "Open This PC, right-click the stick, and choose Format.",
            "In the box that opens, set File system to FAT32.",
            "Tick Quick Format, then press Start. It takes a few seconds.",
            "Give it a short name — letters and numbers only.",
            "Copy your files on, in the folder your display expects.",
            "Click Eject on the computer before you unplug it.",
        ),
        verify=(
            "Right-click the stick and choose Properties: it should say FAT32.",
            "Your files appear on the display when you open its import screen.",
        ),
        cautions=(
            "Formatting wipes the stick. Copy anything you want to keep off it "
            "first.",
            "Use one stick per machine. Two machines sharing a stick can "
            "overwrite each other's folders.",
            "A stick works for years once it is set up like this — you only do "
            "it once.",
        ),
        common_errors=(
        ),
        confidence=Confidence.VERIFIED,
        sources=("Manufacturer data-management documentation, consolidated",),
    )
