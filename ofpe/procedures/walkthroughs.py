"""Procedures photographed in a real cab, press by press.

Everything else in this package is written from documentation. This module is
written from evidence: somebody sat in the machine, did the job, and
photographed each screen on the way through. A manual says what a display is
documented to do; a photograph says what it actually showed, on that software,
on that day -- and that is what somebody holding a stick in one hand needs.

Two kinds of walk-through live here and they attach in different places.

A *version* walk-through hangs off question three of the wizard, which is where
people stall: everything before it you can answer from where you are standing,
and then it asks for a number four presses deep in a menu nobody visits.

A *procedure* walk-through hangs off one answer -- this display, this job, this
route -- and it owns that procedure's steps rather than sitting beside them.
Two lists of the same instructions would drift within a season, so the
photographed one is the only one, and the procedure reads its text from here.

Coverage is one display and growing, which is the honest position: the rest are
written from manuals and say so. The fix is more cabs, one at a time.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "WalkStep",
    "VersionStep",
    "VersionHelp",
    "ProcedureWalk",
    "VERSION_HELP",
    "WALKTHROUGHS",
    "version_help_for",
    "walkthrough_for",
]


@dataclass(frozen=True)
class WalkStep:
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


VersionStep = WalkStep  # the name it had when only versions were covered


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


# --------------------------------------------------------------------------- #
#  Procedures photographed end to end                                          #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ProcedureWalk:
    """One job on one display, photographed the whole way through.

    This owns the procedure's steps. The entry in the brand module reads its
    text from here rather than repeating it, because two copies of the same ten
    instructions would drift apart inside a season and nobody would notice
    which one was stale.
    """

    monitor_key: str
    objective: str
    transport: str
    folder: str
    evidence: str
    steps: tuple[WalkStep, ...]

    def step_texts(self) -> tuple[str, ...]:
        """What the procedure's `steps` should be. One source of truth."""
        return tuple(step.text for step in self.steps)


_GS3_2630_EXPORT = ProcedureWalk(
    monitor_key="john_deere.gs3_2630",
    objective="export_work_data",
    transport="usb",
    folder="john_deere_gs3_2630",
    evidence=(
        "Photographed on a John Deere combine, GS3 2630 build 3.36.1073, "
        "exporting a season's harvest data. The whole job took about three "
        "minutes on the clock in the corner of the screen."
    ),
    steps=(
        WalkStep(
            text=(
                "Empty the stick first, on a computer. Not \"tidy it up\" — "
                "delete everything off it."
            ),
        ),
        WalkStep(
            text=(
                "Format it FAT32 while you are there, and use one of 32 GB or "
                "less."
            ),
        ),
        WalkStep(
            text=(
                "In the cab, finish or close the job so the last of the work is "
                "written before you copy anything."
            ),
        ),
        WalkStep(
            text=(
                "Plug the stick into the display. Do NOT go hunting through the "
                "menus — the «Data Transfer» page comes up on its own within a "
                "few seconds."
            ),
            button="row_export.jpg",
            screen_name="Data Transfer",
            screen="data_transfer.jpg",
            look_for=(
                "Four rows. «Export Data» is the top one, and its picture shows "
                "the display pointing at a USB stick — data leaving the "
                "machine. «Import Data» underneath points the other way."
            ),
        ),
        WalkStep(
            text="Press «Export Data», the top row.",
        ),
        WalkStep(
            text=(
                "The «Export Profile Name» box already holds today's date, like "
                "Oct92025. That is a perfectly good name — leave it."
            ),
            button="box_name.jpg",
            screen_name="Export Data",
            screen="export_named.jpg",
            look_for=(
                "The box is filled in for you. Press it only if you want your "
                "own name — the second photo shows one typed in by hand."
            ),
        ),
        WalkStep(
            text=(
                "If you would rather name it yourself, press the box and type. "
                "Keep it short and plain, and put the machine or the field in "
                "it so you know what it is in March."
            ),
            screen_name="A name typed in",
            screen="export_typed.jpg",
            look_for=(
                "Same screen with «export test» typed into the box instead of "
                "the date. Either way works."
            ),
        ),
        WalkStep(
            text=(
                "Read the small note: «Note: Data remains on the display.» "
                "Exporting copies your data — it does not empty the monitor."
            ),
            button="note_remains.jpg",
        ),
        WalkStep(
            text="Press «Begin Transfer».",
            button="btn_begin.jpg",
        ),
        WalkStep(
            text=(
                "Now leave it alone. The red warning means it: do not switch "
                "off and do not pull the stick out. Allow two or three minutes."
            ),
            button="warn_donot.jpg",
            screen_name="Transferring Files",
            screen="transferring.jpg",
            look_for=(
                "A green bar and red text — «The external memory is in use», "
                "«Do NOT disconnect power or remove the USB device». The bar "
                "moves slowly; that is normal."
            ),
        ),
        WalkStep(
            text=(
                "«Data Transfer Complete» comes up when it is done. Press "
                "«Accept»."
            ),
            button="btn_accept.jpg",
            screen_name="Data Transfer Complete",
            screen="complete.jpg",
            look_for=(
                "The message tells you to remove the USB device to continue "
                "display operation. That is not a suggestion — see the next "
                "step."
            ),
        ),
        WalkStep(
            text=(
                "Pull the stick out. The display will not run GreenStar with a "
                "stick plugged in, so leaving it there stops you working."
            ),
            button="note_greenstar.jpg",
        ),
        WalkStep(
            text=(
                "Back at the office, copy the whole folder off the stick before "
                "you use it again anywhere."
            ),
        ),
    ),
)


_GS3_2630_LATLON = ProcedureWalk(
    monitor_key="john_deere.gs3_2630",
    objective="import_guidance",
    transport="manual",
    folder="john_deere_gs3_2630",
    evidence=(
        "Photographed on a John Deere combine, GS3 2630 build 3.36.1073, "
        "typing an AB line in as coordinates. The line in the photos runs "
        "almost due north: both ends share a longitude and only the latitude "
        "changes."
    ),
    steps=(
        WalkStep(
            text=(
                "Have the four numbers written down before you climb in: "
                "latitude and longitude for the A end, and for the B end. "
                "Decimal degrees, minus signs included."
            ),
        ),
        WalkStep(
            text=(
                "On the GreenStar run page, set «Client», «Farm» and «Field» "
                "first. The line is filed under them, and a line saved to the "
                "wrong field is lost until you go looking."
            ),
            button="ab_cfa.jpg",
            screen_name="The GreenStar run page",
            screen="ab_run_page.jpg",
            look_for=(
                "The right-hand column: «Client», «Farm», «Field», then "
                "«Tracking Mode», then the «Set Track 0» button underneath."
            ),
        ),
        WalkStep(
            text="Set «Tracking Mode» to «Straight Track».",
            button="ab_mode.jpg",
        ),
        WalkStep(
            text="Press «Set Track 0».",
            button="ab_settrack.jpg",
        ),
        WalkStep(
            text=(
                "Press «New» to start a fresh track. Skip this only if you "
                "mean to overwrite the track already in the «Current Track 0» "
                "box."
            ),
            button="ab_new.jpg",
            screen_name="Set Track 0",
            screen="ab_set_track.jpg",
            look_for=(
                "«Current Track 0» and «Method» across the top, the four "
                "coordinate boxes below, «Cancel» and «Accept» at the bottom."
            ),
        ),
        WalkStep(
            text=(
                "Open the «Method» list and choose «Lat/Lon». That is the one "
                "that lets you type all four numbers."
            ),
            button="ab_method.jpg",
            screen_name="The Method list",
            screen="ab_methods.jpg",
            look_for=(
                "Five methods: «A + B», «A + Heading», «Lat/Lon», «Auto B», "
                "«Lat/Lon + Heading». The first two need you to drive the line; "
                "«Lat/Lon» does not."
            ),
        ),
        WalkStep(
            text=(
                "Four boxes appear — «Lat.» and «Lon.» under «Point A», and the "
                "same pair under «Point B». Press the first one."
            ),
            button="ab_points.jpg",
        ),
        WalkStep(
            text=(
                "A keyboard opens with the current value in it. The same "
                "keyboard serves all four boxes — only the number it is filling "
                "changes, so check you are on the box you meant."
            ),
            screen_name="The keyboard",
            screen="ab_keyboard.jpg",
            look_for=(
                "The value sits at the top. «C» clears it, the arrow rubs out "
                "one character. «Accept», bottom right, puts it in the box."
            ),
        ),
        WalkStep(
            text=(
                "Type the number and press «Accept». The minus sign is on the "
                "number row, just right of the 0 — you need it for south "
                "latitudes and west longitudes."
            ),
            button="ab_minus.jpg",
        ),
        WalkStep(
            text=(
                "Do the other three boxes the same way: Point A «Lon.», then "
                "Point B «Lat.» and «Lon.»."
            ),
        ),
        WalkStep(
            text=(
                "Check the readout before you commit. «Heading» is the "
                "direction the line came out at, and «Point A Lat» and "
                "«Point A Lon» repeat what you typed."
            ),
            button="ab_readout.jpg",
        ),
        WalkStep(
            text=(
                "Set «Track Spacing» to your working width. The passes either "
                "side of the line are spaced by this, and it is the number "
                "people forget."
            ),
        ),
        WalkStep(
            text="Press «Accept».",
        ),
        WalkStep(
            text=(
                "If it asks «You are about to overwrite the current track 0. "
                "Continue?», read it properly. «Accept» replaces that field's "
                "Track 0 and the old one is gone; «Cancel» backs out."
            ),
            button="ab_overwrite.jpg",
            screen_name="The overwrite warning",
            screen="ab_overwrite_screen.jpg",
            look_for=(
                "It only appears when the field already has a Track 0. If you "
                "pressed «New» earlier and still see this, you are about to "
                "replace a line somebody drove."
            ),
        ),
    ),
)


WALKTHROUGHS: tuple[ProcedureWalk, ...] = (_GS3_2630_EXPORT, _GS3_2630_LATLON)

_BY_PROCEDURE = {
    (w.monitor_key, w.objective, w.transport): w for w in WALKTHROUGHS
}


def walkthrough_for(
    monitor_key: str, objective: str, transport: str
) -> ProcedureWalk | None:
    """The photographed version of this answer, if somebody has shot it."""
    return _BY_PROCEDURE.get((monitor_key, objective, transport))
