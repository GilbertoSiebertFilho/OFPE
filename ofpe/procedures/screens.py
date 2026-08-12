"""The application icons that actually appear on a display's screen.

Everything else in this package describes a screen in words. This module carries
the pictures -- and the distinction matters, because the two are used
differently. Words tell you what to do; the icon is what your eye is hunting
for while your hand is on the armrest and the engine is running.

These are not our drawings. The terminal pictures elsewhere in the guide are
schematics we drew, deliberately generic, carrying no manufacturer's marks. An
application icon cannot work that way: its whole job is to match the glyph on
the glass, so a redrawn approximation is worse than none. So they are lifted
from the manufacturer's own operator manual, credited to it, and shown at the
size a person needs to recognise them.

A step earns its icon by naming the button. `«File Manager»` in a Gen 4 step
resolves through the table below and picks up the folder glyph; nothing extra is
written on the procedure, and an icon can never drift away from the label it
belongs to, because the label *is* the key.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ScreenIcon", "SCREEN_ICONS", "icons_for", "icon_credit"]


@dataclass(frozen=True)
class ScreenIcon:
    """One glyph on one display, and where it came from."""

    label: str
    """The exact on-screen wording, as it is written in a step's « »."""

    file: str
    """File name inside assets/icons/<monitor folder>/."""

    code: str
    """The manufacturer's own illustration number, so a reader can find it."""


# The manual reproduces each icon beside the paragraph naming its application,
# with John Deere's illustration code in the margin. Labels here are matched
# case-insensitively against the « » in a step.
_GEN4 = (
    ScreenIcon("Menu", "menu.png", "PC17269"),
    ScreenIcon("File Manager", "file_manager.png", "PC16671"),
    ScreenIcon("Import Data", "import_data.png", "PC17264"),
    ScreenIcon("Export Data", "export_data.png", "PC17264"),
    ScreenIcon("Fields", "fields.png", "PC17260"),
    ScreenIcon("Guidance", "guidance.png", "PC16676"),
    ScreenIcon("Software Manager", "software_manager.png", "PC15346"),
    ScreenIcon("Machine Profiles", "machine_profiles.png", "PC16679"),
    ScreenIcon("Implement Profiles", "implement_profiles.png", "PC16672"),
    ScreenIcon("Layout Manager", "layout_manager.png", "PC16678"),
    ScreenIcon("StarFire", "starfire.png", "PC17388"),
    ScreenIcon("ISOBUS VT", "isobus_vt.png", "PC16682"),
    ScreenIcon("Work Monitor", "work_monitor.png", "PC15317"),
    ScreenIcon("Machine Monitor", "machine_monitor.png", "PC15318"),
    ScreenIcon("Display and Sound", "display_sound.png", "PC16685"),
    ScreenIcon("Language and Units", "language_units.png", "PC16677"),
    ScreenIcon("Date and Time", "date_time.png", "PC16674"),
    ScreenIcon("Diagnostics Center", "diagnostics.png", "PC17272"),
    ScreenIcon("Users & Access", "users_access.png", "PC17262"),
    ScreenIcon("Controls Setup", "controls_setup.png", "PC15326"),
    ScreenIcon("Help Center", "help_center.png", "PC16684"),
    ScreenIcon("Remote Display Access", "remote_display.png", "PC17363"),
)

# The G5 runs the same operating system and the same application icons; John
# Deere's own documentation treats the two together. Sharing the set is a claim
# that they look alike, which is exactly what the compatibility material says.
SCREEN_ICONS: dict[str, tuple[str, tuple[ScreenIcon, ...]]] = {
    "john_deere.gen4": ("john_deere_gen4", _GEN4),
    "john_deere.g5": ("john_deere_gen4", _GEN4),
}

CREDITS = {
    "john_deere_gen4": (
        "Application icons reproduced from the John Deere Generation 4 "
        "CommandCenter operator manual (regulatory model RE338096, edition "
        "080714). John Deere illustration numbers are given so each one can be "
        "found in the original."
    ),
}


def icons_for(monitor_key: str) -> dict[str, ScreenIcon]:
    """Every icon this display has, keyed by lower-cased on-screen label."""
    entry = SCREEN_ICONS.get(monitor_key)
    if not entry:
        return {}
    _folder, icons = entry
    return {icon.label.lower(): icon for icon in icons}


def folder_for(monitor_key: str) -> str:
    entry = SCREEN_ICONS.get(monitor_key)
    return entry[0] if entry else ""


def icon_credit(monitor_key: str) -> str:
    """Who the icons belong to. Shown wherever they are."""
    return CREDITS.get(folder_for(monitor_key), "")
