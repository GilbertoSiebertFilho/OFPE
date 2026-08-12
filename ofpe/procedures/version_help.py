"""How to find the software version, verified against a real machine.

The wizard asks for a software version third, and that is the question people
stall on. Everything before it is knowable from where you are standing -- the
machine is a combine, the display says John Deere on the bezel -- and then it
asks for a number that is four presses deep in a menu nobody visits.

So the question carries its own answer. Not a link to a manual: the presses, in
order, each with a photograph of the button as it appears on that display, and
the screen it leads to.

These come from photographs of a working machine, which makes them the firmest
thing in this guide. A manual says what a display is documented to do. A photo
of the cab says what it actually showed, on that software, on that day -- and
that is what somebody comparing it against their own screen needs.

One display is covered so far. The others still say "look under diagnostics or
about", which is honest and nearly useless, and the fix is more cabs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "VersionStep",
    "VersionHelp",
    "VERSION_HELP",
    "version_help_for",
]


@dataclass(frozen=True)
class VersionStep:
    """One press, with the evidence for it."""

    text: str
    """The instruction. On-screen wording in « », as everywhere else."""

    button: str = ""
    """Crop of the button itself, shown inline at the size of a word."""

    screen: str = ""
    """The whole screen this step lands on, for the reader to compare."""

    look_for: str = ""
    """What to notice in that screen. Without this a photo is decoration."""

    screen_name: str = ""
    """What this screen is called, so five photos of one display are telling
    apart at thumbnail size."""


@dataclass(frozen=True)
class VersionHelp:
    """Finding the version on one display."""

    monitor_key: str
    folder: str
    """Folder under assets/photos/ holding the images."""

    field_label: str
    """The exact wording of the line that carries the number."""

    example: str
    """A real value, so the reader knows the shape of what they are hunting."""

    steps: tuple[VersionStep, ...]

    reads_as: str = ""
    """How to turn what the screen says into the answer this wizard wants."""

    evidence: str = ""
    """Where the pictures came from. Named, because it is the whole claim."""

    also_shows: tuple[str, ...] = field(default_factory=tuple)
    """Other useful numbers on the same screen, worth writing down once."""


_GS3_2630 = VersionHelp(
    monitor_key="john_deere.gs3_2630",
    folder="john_deere_gs3_2630",
    field_label="Application Software Build",
    example="3.36.1073",
    reads_as=(
        "Every 2630 still in service runs a 3.x build, so whatever number you "
        "find, pick the 3.x option. Write the full number down anyway — a "
        "dealer will ask for it, and it is four presses away next time."
    ),
    evidence=(
        "Photographed on a John Deere combine running GS3 2630 build "
        "3.36.1073. Every button below is a crop of that machine's screen."
    ),
    also_shows=(
        "Display — confirms the model, so you know you are on the right page.",
        "Hardware Part Number — what a dealer asks for when ordering.",
        "Hardware Serial Number — worth a photo for your own records.",
    ),
    steps=(
        VersionStep(
            text=(
                "Start on the run page — the one with the map and the totals. "
                "Bottom right there are two buttons; press the right-hand one, "
                "with the green arrow and the grid."
            ),
            button="btn_menu.jpg",
            screen_name="The run page",
            screen="run_page.jpg",
            look_for=(
                "The green arrow-and-grid button, bottom right of the screen. "
                "The house button beside it goes the other way, back to the "
                "run page."
            ),
        ),
        VersionStep(
            text=(
                "The menu opens as a list lettered A to J. Press «Display» — "
                "it is F, top of the right-hand column, and its picture is a "
                "little screen."
            ),
            button="btn_display.jpg",
            screen_name="The menu, A to J",
            screen="menu.jpg",
            look_for=(
                "Every entry carries a letter in its corner. «Display» is F. "
                "Do not confuse it with «GreenStar» at E, which is where the "
                "field work lives."
            ),
        ),
        VersionStep(
            text=(
                "You land on «Display - Main», with brightness and volume. "
                "Down the right-hand side is another lettered column: press "
                "«Diagnostics», at I, the book-and-spanner."
            ),
            button="btn_diagnostics.jpg",
            screen_name="Display - Main",
            screen="display_main.jpg",
            look_for=(
                "The page title, top left, reads Display - Main. The column on "
                "the right runs Remote, Main, Settings, Aux Ctrls, "
                "Diagnostics, Controls."
            ),
        ),
        VersionStep(
            text=(
                "Four tabs appear across the top. Press the last one, «About»."
            ),
            button="btn_about.jpg",
            screen_name="Display - Diagnostics",
            screen="diagnostics.jpg",
            look_for=(
                "The tabs read Readings, Tests, Multiple Displays, About. The "
                "one you are on turns blue."
            ),
        ),
        VersionStep(
            text=(
                "Ignore the copyright text filling the page. The numbers are "
                "in small print at the very bottom. Read the line "
                "«Application Software Build»."
            ),
            button="the_answer.jpg",
            screen_name="The About tab",
            screen="about.jpg",
            look_for=(
                "Four lines, bottom centre. Display: GS3 2630. Application "
                "Software Build: 3.36.1073 — that middle number is your "
                "version."
            ),
        ),
    ),
)


VERSION_HELP: dict[str, VersionHelp] = {
    _GS3_2630.monitor_key: _GS3_2630,
}


def version_help_for(monitor_key: str) -> VersionHelp | None:
    """The photographed walk-through for this display, if we have one."""
    return VERSION_HELP.get(monitor_key)
