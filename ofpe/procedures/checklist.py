"""The short list of things that spoil a trial if they are missed.

This is not a procedure. A procedure answers "how do I get this file into
this display"; this answers "what did I forget", and it is read once at the
start of a day rather than followed step by step.

It is deliberately generic. The list a grower gets from their agronomist
carries the numbers -- which field, which header width, the coordinates of
the line -- and those are different for every trial, so putting any of them
here would be inventing them. What is the same for everybody is the shape of
the day and the handful of mistakes that cannot be undone afterwards, and
that is all this holds.

Each item earns its place by failing badly:

  * A treatment strip is only a treatment strip if the yield data lines up
    with where the treatment actually went. Two combines on two different
    lines, or one line nudged mid-field, and it does not.
  * Yield is computed from the header width. Get it wrong and every point in
    the field is wrong by the same factor, invisibly.
  * A yield monitor that is not calibrated, or not recording, produces a
    field's worth of nothing -- and you find out at the end.

Items that are merely good practice are left out. A list nobody finishes
reading protects nothing.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["CHECKLISTS", "Check", "Stage", "checklist_for"]


@dataclass(frozen=True)
class Check:
    """One line of the list.

    `key` is what a tick is remembered under, so it has to stay put when the
    wording is improved -- a checklist that quietly unticks itself because
    somebody fixed a comma is worse than no memory at all.
    """

    key: str
    text: str
    why: str = ""
    hard: bool = False  # the ones with no way back once they have happened


@dataclass(frozen=True)
class Stage:
    key: str
    title: str
    note: str
    checks: tuple[Check, ...]


_BEFORE = Stage(
    "before",
    "Before you go out",
    "At the yard, with a computer and a signal. Everything here is painful "
    "to fix from the field.",
    (
        Check(
            "same_line",
            "The same guidance line is in every combine that will run this "
            "trial.",
            "Two machines on two different lines put the strips in two "
            "different places, and no amount of work afterwards separates "
            "them again.",
        ),
        Check(
            "line_by_hand",
            "You can type an AB line in by hand if the file will not load.",
            "Four numbers — Lat A, Long A, Lat B, Long B — off the trial "
            "sheet. Pick your display below for the exact screens.",
        ),
        Check(
            "yield_cal_known",
            "You know how to calibrate the yield monitor on each combine.",
            "Different machines, different menus. Worth finding out before "
            "the crop is ready rather than on the headland.",
        ),
        Check(
            "recording_setup",
            "Each combine is set up to record yield data, with room to store "
            "it.",
            "A full card stops recording without stopping the machine.",
        ),
        Check(
            "guidance_works",
            "Guidance actually works: the machine tracks the line you "
            "loaded, not one it made itself.",
        ),
    ),
)

_FIELD = Stage(
    "field",
    "When you pull into the field",
    "In each combine, before the first pass.",
    (
        Check(
            "field_task",
            "Grower, Farm, Field, Task and Crop Type are all correct.",
            "This is what the yield data gets filed under. Wrong here and "
            "the data is somewhere, but not where anybody looks for it.",
        ),
        Check(
            "right_line",
            "The trial's own guidance line is selected — not last season's, "
            "not one the display generated.",
        ),
        Check(
            "header_width",
            "Header width is set to what the trial assumes.",
            "Yield per area is calculated from it, so a wrong width is a "
            "wrong yield on every point in the field, and it looks "
            "perfectly normal.",
        ),
        Check(
            "cal_headlands",
            "Yield monitor calibrated on the headlands, before you go into "
            "the trial area.",
        ),
        Check(
            "headlands_first",
            "Headlands finished first, then the field harvested on the AB "
            "line.",
        ),
        Check(
            "no_nudge",
            "Do not press nudge, shift or recentre while harvesting the "
            "trial.",
            "It moves the line under the machine, so the yield no longer "
            "sits where the treatment went — and nothing in the data says "
            "it happened. If the line looks wrong, finish the pass and tell "
            "whoever laid the trial out. Do not move it.",
            hard=True,
        ),
        Check(
            "recording",
            "Yield monitor is recording — checked again after the first "
            "pass, not only at the start.",
            "Starting and recording are two different things, and the "
            "difference costs a whole field.",
            hard=True,
        ),
    ),
)

#: Keyed by operation, so a planting or spraying list is data to add rather
#: than code to write.
CHECKLISTS: dict[str, tuple[Stage, ...]] = {
    "harvest": (_BEFORE, _FIELD),
}


def checklist_for(operation: str = "harvest") -> tuple[Stage, ...]:
    return CHECKLISTS.get(operation, ())
