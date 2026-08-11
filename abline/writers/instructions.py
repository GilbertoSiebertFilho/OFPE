"""The instruction sheet that ships inside every download.

A producer standing at the machine with a USB stick has no internet and no
patience. The sheet is plain text, wrapped to 78 columns so it prints, and it
leads with what the file *is* and whether it will import in one step or two --
because the honest answer to that varies by brand and it is better read at the
desk than discovered in the cab.
"""

from __future__ import annotations

import textwrap
from datetime import datetime, timezone

from ..catalog import FORMATS, MonitorProfile, SupportLevel
from ..models import FieldRecord, GuidanceLine, Machine

__all__ = ["build_instructions"]

_WIDTH = 78


def _rule(char: str = "-") -> str:
    return char * _WIDTH


def _heading(text: str) -> list[str]:
    return ["", text.upper(), _rule()]


def _wrap(text: str, indent: str = "") -> list[str]:
    return textwrap.wrap(
        text, width=_WIDTH, initial_indent=indent, subsequent_indent=indent
    ) or [""]


def _numbered(items) -> list[str]:
    out: list[str] = []
    for i, item in enumerate(items, 1):
        prefix = f"{i:>2}. "
        out.extend(
            textwrap.wrap(
                item, width=_WIDTH, initial_indent=prefix, subsequent_indent=" " * 4
            )
        )
    return out


def _bulleted(items, marker: str = "  * ") -> list[str]:
    out: list[str] = []
    for item in items:
        out.extend(
            textwrap.wrap(
                item,
                width=_WIDTH,
                initial_indent=marker,
                subsequent_indent=" " * len(marker),
            )
        )
    return out


_SUPPORT_NOTE = {
    SupportLevel.NATIVE: (
        "This file imports directly. Your display reads this format natively -- "
        "copy it to a USB stick, import, and drive."
    ),
    SupportLevel.STRUCTURAL: (
        "This file imports directly, but the exact menu wording moves between "
        "software versions. If the steps below do not match your screen, look "
        "for the equivalent import option -- the file itself is right."
    ),
    SupportLevel.DESKTOP_BRIDGE: (
        "IMPORTANT: this brand's guidance file format is closed, so this is a "
        "TWO-STEP import. The file goes into the manufacturer's own software "
        "first, and that software writes the file your display reads. There is "
        "no way around this and no third party can skip it. The steps below "
        "walk through both halves."
    ),
    SupportLevel.NEEDS_SAMPLE: (
        "HEADS UP: we have this brand's folder layout from the manufacturer's "
        "manual, but we have not yet been able to confirm the internal format "
        "of the line file itself against a real machine export. A shapefile "
        "copy of the same lines is included as a fallback. If the native import "
        "does not list your lines, use the shapefile and let us know -- one "
        "real export from your display is all we need to fix this properly."
    ),
    SupportLevel.API_ONLY: (
        "NOTE: there is no file-based route into this display. The contents "
        "here are for reference and for rebuilding the line by hand."
    ),
}


def build_instructions(
    monitor: MonitorProfile,
    field: FieldRecord,
    lines: list[GuidanceLine],
    *,
    machine: Machine | None = None,
    format_key: str = "",
    file_list: list[str] | None = None,
) -> str:
    """Compose the HOW-TO-IMPORT sheet for one download."""
    out: list[str] = [
        _rule("="),
        f"AB LINES FOR: {monitor.label}".center(_WIDTH).rstrip(),
        _rule("="),
        "",
    ]

    out.append(f"Field:     {field.name or '(unnamed)'}")
    if field.farm:
        out.append(f"Farm:      {field.farm}")
    if field.grower:
        out.append(f"Grower:    {field.grower}")
    if field.has_boundary:
        out.append(f"Area:      {field.area_ha():.2f} ha")
    if machine:
        out.append(f"Machine:   {machine.name} ({machine.display_width})")
        if machine.overlap_m:
            out.append(
                f"           swath spacing {machine.effective_width_m:g} m "
                f"after {machine.overlap_m:g} m overlap"
            )
    out.append(f"Lines:     {len(lines)}")
    out.append(f"Generated: {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}")

    fmt = FORMATS.get(format_key)
    if fmt:
        out.append(f"Format:    {fmt.label}")

    out.extend(_heading("What you are holding"))
    out.extend(_wrap(_SUPPORT_NOTE[monitor.support]))
    if fmt:
        out.append("")
        out.extend(_wrap(fmt.description))

    if file_list:
        out.extend(_heading("Files in this download"))
        out.extend(_bulleted(sorted(file_list)))

    if monitor.usb_path:
        out.extend(_heading("Where it goes on the stick"))
        out.extend(_wrap(monitor.usb_path))
        out.append("")
        out.extend(_wrap(f"Format the stick as: {monitor.filesystem}"))

    if monitor.steps:
        out.extend(_heading("Step by step"))
        out.extend(_numbered(monitor.steps))

    if monitor.guidance_vocabulary:
        out.extend(_heading("What this brand calls an AB line"))
        out.extend(_wrap(monitor.guidance_vocabulary))
        out.append("")
        out.extend(
            _wrap(
                "Look for those words in the menus. Every manufacturer names "
                "the same idea differently."
            )
        )

    out.extend(_heading("The lines in this file"))
    for line in lines:
        heading = line.computed_heading()
        bits = [f"{line.name or 'Line'} -- {line.pattern.value}"]
        if heading is not None:
            bits.append(f"heading {heading:.2f} deg true")
        bits.append(f"swath {line.swath_width_m:g} m")
        out.extend(_bulleted([", ".join(bits)]))
        detail = []
        if line.source_detail:
            detail.append(line.source_detail)
        if line.confidence and line.confidence != "ok":
            detail.append(f"confidence: {line.confidence}")
        if detail:
            out.extend(_bulleted(["; ".join(detail)], marker="      "))

    if monitor.caveats:
        out.extend(_heading("Worth knowing"))
        out.extend(_bulleted(monitor.caveats))

    if monitor.common_errors:
        out.extend(_heading("Things that go wrong"))
        out.extend(_bulleted(monitor.common_errors))

    out.extend(_heading("Before you engage the steering"))
    out.extend(
        _bulleted(
            [
                "Check the line is drawn where you expect it on the run screen.",
                "Check the swath width on the display matches your machine. A "
                "line imported at the wrong width will look right and drive "
                "wrong.",
                "Drive one pass with the steering off and confirm the machine "
                "tracks the line before you hand it over.",
            ]
        )
    )

    if monitor.sources:
        out.extend(_heading("Where these steps come from"))
        out.extend(_bulleted(monitor.sources))

    out.extend(
        [
            "",
            _rule("="),
            "Generated by the CWSI AB Line Platform.",
            _rule("="),
            "",
        ]
    )
    return "\r\n".join(out)
