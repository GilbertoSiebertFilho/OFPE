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
        # This one happens on a computer, not on the display, so the marked
        # names are the Windows ones. They are marked for the same reason the
        # display's are: a name you have to find on a screen reads faster as a
        # cap than as a word inside a sentence.
        steps=(
            # It is the ceiling that bites, not the floor. John Deere's own
            # Gen 4 manual suggests 4 GB and up, and a procedure file is
            # measured in kilobytes -- telling somebody their 4 GB stick is
            # too small sends them to buy one they did not need.
            "Pick a stick of 32 GB or less — 4 GB is plenty. Bigger ones "
            "often are not read at all, however new they are.",
            "Plug it into a computer.",
            "Open «This PC», right-click the stick, and choose «Format».",
            "In the box that opens, set «File system» to «FAT32».",
            "Type a short «Volume label» — letters and numbers only, no "
            "spaces. That is the name the display will show.",
            "Leave «Quick Format» ticked and press «Start». It takes a few "
            "seconds.",
            "Copy your files on, in the folder your display expects.",
            "Right-click the stick and choose «Eject» before you pull it out.",
        ),
        verify=(
            "Right-click the stick and choose «Properties»: it should say "
            "FAT32.",
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
