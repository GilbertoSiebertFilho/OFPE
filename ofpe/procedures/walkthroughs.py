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

Coverage is two displays and growing -- the GreenStar 3 2630 and the New
Holland IntelliView IV -- which is the honest position: the rest are written
from manuals and say so. The fix is more cabs, one at a time.
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
                "You need FOUR numbers, not two. Write them down before you "
                "climb in: Lat A, Long A, Lat B, Long B."
            ),
        ),
        WalkStep(
            text=(
                "A and B are the two ends of the line. Lat A and Long A fix "
                "where it starts; Lat B and Long B fix where it points. Miss "
                "one and the display has no line."
            ),
        ),
        WalkStep(
            text=(
                "All four in decimal degrees, minus signs included — like "
                "-27.845123 and -54.477456."
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


_GS3_2630_IMPORT_LINES = ProcedureWalk(
    monitor_key="john_deere.gs3_2630",
    objective="import_guidance",
    transport="usb",
    folder="john_deere_gs3_2630",
    evidence=(
        "Photographed on a John Deere combine, GS3 2630 build 3.36.1073, "
        "importing a profile called AB_Test_Combine off a stick."
    ),
    steps=(
        WalkStep(
            text=(
                "This route needs a USB stick with the lines already on it. If "
                "you have coordinates on paper and no stick, use the "
                "type-it-in route instead."
            ),
        ),
        WalkStep(
            text=(
                "The stick must carry a profile — the folder structure John "
                "Deere software writes. Loose files will not be seen."
            ),
        ),
        WalkStep(
            text=(
                "Plug the stick in. The «Data Transfer» page comes up on its "
                "own; you do not go hunting for it."
            ),
            screen_name="Data Transfer",
            screen="gl_data_transfer.jpg",
            look_for=(
                "Four rows. «Import Guidance Lines» is the bottom one. Do not "
                "press «Import Data» above it — that brings in everything, not "
                "just the lines."
            ),
        ),
        WalkStep(
            text="Press «Import Guidance Lines», the bottom row.",
            button="gl_row_import.jpg",
        ),
        WalkStep(
            text=(
                "«Import Profile Name (On USB)» lists the profiles it found on "
                "the stick. Pick yours."
            ),
            button="gl_box_profile.jpg",
            screen_name="Import Guidance Lines",
            screen="gl_profile.jpg",
            look_for=(
                "The box says (On USB) — this list is the stick's contents, "
                "not the display's. An empty list means the stick is wrong, "
                "not the display."
            ),
        ),
        WalkStep(
            text=(
                "Read the note about boundaries. Anything that comes in with "
                "the lines is worth checking on the map before you rely on "
                "section control."
            ),
            button="gl_note_boundary.jpg",
        ),
        WalkStep(
            text="Press «Begin Transfer».",
            button="gl_begin.jpg",
        ),
        WalkStep(
            text=(
                "A filter appears: «Client», «Farm», «Field» and "
                "«Tracking Mode». Narrow it down, or leave any of them on "
                "«<All>» to take the lot."
            ),
            screen_name="The filter",
            screen="gl_filter.jpg",
            look_for=(
                "«Reset» clears the filter back to «<All>». Watch "
                "«Available Tracks» at the bottom — it counts what your filter "
                "actually matches."
            ),
        ),
        WalkStep(
            text=(
                "«Tracking Mode» sorts by the kind of line: «AB Curves», "
                "«Adaptive Curves», «Circle Track», «Straight Track»."
            ),
            screen_name="The line types",
            screen="gl_modes.jpg",
            look_for=(
                "Useful when a field has years of lines on it and you only "
                "want the straight ones."
            ),
        ),
        WalkStep(
            text=(
                "Check «Available Tracks» before you go on. Zero means the "
                "filter is too tight, not that the stick is empty."
            ),
            button="gl_available.jpg",
        ),
        WalkStep(
            text="Press «Accept».",
        ),
        WalkStep(
            text=(
                "Now the tracks themselves, each with a tick box. They are "
                "named by date, so the newest is usually the one you want."
            ),
            button="gl_tracklist.jpg",
            screen_name="The track list",
            screen="gl_tracks.jpg",
            look_for=(
                "The header repeats the Client, Farm, Field and Tracking Mode "
                "you filtered on. «Selected» at the bottom counts your ticks."
            ),
        ),
        WalkStep(
            text=(
                "Tick what you want. «Select All» takes everything listed, "
                "«Clear All» unticks it again."
            ),
            button="gl_selectall.jpg",
        ),
        WalkStep(
            text="Press «Accept» to bring them in.",
        ),
        WalkStep(
            text=(
                "«Data Transfer Complete» appears. Press «Accept» and pull the "
                "stick out — the display will not run GreenStar with it in."
            ),
            screen_name="Data Transfer Complete",
            screen="gl_complete.jpg",
            look_for=(
                "The USB port is on the right-hand side of the display, behind "
                "the flap."
            ),
        ),
        WalkStep(
            text=(
                "On the run page, set the field and pick your track from the "
                "guidance list before you engage the steering."
            ),
        ),
    ),
)


# --------------------------------------------------------------------------- #
#  New Holland IntelliView IV                                                  #
# --------------------------------------------------------------------------- #
#
# Photographed on a New Holland combine at Olds College on 11 September 2026:
# an AB line typed in twice (once with a wrong turn into «Mark B», once clean
# with a finger on every press), the same kind of line brought in off a stick
# as ISOXML, and the yield data taken off. 88 photographs; the ones used here
# are cut by tools/extract_iv4_photos.py.
#
# Where a sentence says the same thing as the 2630's, it is the 2630's --
# taken from that walk-through, not retyped. The physics of four numbers does
# not change with the badge on the display, and identical text shares one
# recording of the spoken step.
#
# Nothing in these steps says "in the photo". The Case IH AFS Pro 700 is the
# same display in different paint and takes these steps word for word, without
# the pictures -- so the text has to stand on its own.

_IV4_FOLDER = "new_holland_intelliview_iv"
_IV4_WHERE = (
    "a New Holland combine with an IntelliView IV (software © 2010–2021), "
    "at Olds College on 11 September 2026"
)

_IV4_LATLON = ProcedureWalk(
    monitor_key="new_holland.intelliview_iv",
    objective="import_guidance",
    transport="manual",
    folder=_IV4_FOLDER,
    evidence=(
        f"Photographed on {_IV4_WHERE}, typing an AB line in as coordinates. "
        "The first line in the photos runs almost due south — both ends share "
        "a longitude to three decimals, and the display worked the heading "
        "out as 177.9°."
    ),
    steps=(
        *_GS3_2630_LATLON.steps[:3],
        WalkStep(
            text=(
                "Press the «FARM» tab along the bottom of the run screen, and "
                "set «Grower», «Farm» and «Field» first. The line is filed "
                "under that field."
            ),
            button="btn_tab_farm.jpg",
            screen_name="The FARM page",
            screen="farm_page.jpg",
            look_for=(
                "«Grower», «Farm» and «Field» down the middle, «Operator» and "
                "«Crop Type» beside them. Each one is a box you press. (The "
                "operator's name is blurred.)"
            ),
        ),
        WalkStep(
            text=(
                "Press a box to change it. «Select» picks a name the display "
                "already has; «New» makes one, and a keyboard opens for the "
                "letters. «Enter» saves."
            ),
            button="btn_grower_menu.jpg",
            screen_name="Grower",
            screen="grower_menu.jpg",
            look_for=(
                "«Select», «Edit Name», «New». Farm and Field may offer fewer "
                "choices — a farm with nothing under it yet only offers «New»."
            ),
        ),
        WalkStep(
            text=(
                "Now press the «GPS» tab. This is the guidance page: «Auto "
                "Guidance» and «Nudge» at the top, the swath map in the "
                "middle, «Swath 1 Recorder» and «Type» along the bottom."
            ),
            button="btn_tab_gps.jpg",
            screen_name="The GPS page",
            screen="gps_page.jpg",
            look_for=(
                "«Swath 1 Recorder» is the empty box, bottom left, with «Type» "
                "beside it. «Swath Select» on the right names the line the "
                "steering follows — empty until you make one."
            ),
        ),
        WalkStep(
            text=(
                "Check «Type» reads «Straight». If it does not, press it and "
                "pick «Straight» — that is the one for an AB line from two "
                "points."
            ),
            button="btn_type_straight.jpg",
            screen_name="The Type list",
            screen="swath_type.jpg",
            look_for=(
                "«Straight», «Heading», «Circle», «Curve», «Spiral», «Field». "
                "Curves and circles have to be driven; they cannot be typed."
            ),
        ),
        WalkStep(
            text=(
                "Press the «Swath 1 Recorder» box, then «New». The display "
                "names the line itself — Straight 1, Straight 2 — and you can "
                "rename it afterwards."
            ),
            button="btn_new.jpg",
            screen_name="Swath 1 Recorder",
            screen="recorder_new.jpg",
            look_for="One choice, «New». It starts a fresh line.",
        ),
        WalkStep(
            text=(
                "Two buttons appear on the right: «Enter A» and «Mark A». "
                "Press «Enter A»."
            ),
            button="btn_enter_a.jpg",
            screen_name="Ready for point A",
            screen="ready_a.jpg",
            look_for=(
                "The recorder box now carries the new name, Straight 2. "
                "«Enter A» is for typing the point; «Mark A» is for driving to "
                "it."
            ),
        ),
        WalkStep(
            text=(
                "Not «Mark A». Mark takes the spot the machine is standing on, "
                "and without a correction signal it only answers «No DGPS»."
            ),
            button="warn_nodgps.jpg",
            screen_name="No DGPS",
            screen="no_dgps.jpg",
            look_for=(
                "What «Mark B» said when it was pressed by mistake: «Cannot "
                "mark B». «Cancel» backs out, and nothing is lost."
            ),
        ),
        WalkStep(
            text=(
                "A number pad opens, titled «Latitude (A)». Type Lat A and "
                "press «Enter». «Del» rubs out one digit; the minus is the key "
                "bottom right."
            ),
            button="btn_keypad.jpg",
            screen_name="Latitude (A)",
            screen="lat_a.jpg",
            look_for=(
                "The title says which of the four numbers it wants — read it "
                "before you type. Here 51. is on its way in."
            ),
        ),
        WalkStep(
            text=(
                "«Longitude (A)» opens straight after. Type Long A with its "
                "minus sign and press «Enter». In Canada every longitude is "
                "negative; the latitude is not."
            ),
            screen_name="Longitude (A)",
            screen="lon_a.jpg",
            look_for="-113. going in — the minus goes first.",
        ),
        WalkStep(
            text="The buttons change to «Enter B» and «Mark B». Press «Enter B».",
            button="btn_enter_b.jpg",
        ),
        WalkStep(
            text=(
                "«Latitude (B)» and «Longitude (B)» open one after the other. "
                "Type them the same way."
            ),
            screen_name="Latitude (B)",
            screen="lat_b.jpg",
            look_for=(
                "The same pad with a new title. The letter in brackets is the "
                "only thing that tells the four apart."
            ),
        ),
        WalkStep(
            text=(
                "«Swath Source» asks where the line came from. Press "
                "«Intelliview»."
            ),
            button="btn_intelliview.jpg",
            screen_name="Swath Source",
            screen="swath_source.jpg",
            look_for=(
                "«Intelliview», «Non-Intelliview 1», «Non-Intelliview 2», "
                "«Information». The line was made on this display, so it is "
                "«Intelliview»."
            ),
        ),
        WalkStep(
            text=(
                "The line now shows under «Swath Select». That is the line the "
                "steering will follow."
            ),
            button="btn_swath_select.jpg",
            screen_name="The line, ready",
            screen="line_ready.jpg",
            look_for=(
                "«Swath Select» reads Straight 2, and «Swath 1 Recorder» is "
                "empty again, ready for the next line."
            ),
        ),
        WalkStep(
            text=(
                "Check it before you drive: press «Swath Select», then «Info». "
                "It repeats point A and point B, and the next page gives the "
                "heading."
            ),
            button="btn_swath_menu.jpg",
            screen_name="Info",
            screen="info.jpg",
            look_for=(
                "Name, then A and B with the numbers that were typed, then "
                "«Source: Intelliview» and «Type: Straight». The arrow on the "
                "right turns to the page with the date, the correction signal "
                "and the heading."
            ),
        ),
        WalkStep(
            text=(
                "«Map» in the same list draws the line over the field. A line "
                "in the wrong field shows up at a glance."
            ),
            screen_name="Map Management",
            screen="map_line.jpg",
            look_for=(
                "The line runs from the green dot, A, to the red star, B. "
                "«Field» and «Swath» underneath name what you are looking at."
            ),
        ),
    ),
)


_IV4_IMPORT_LINES = ProcedureWalk(
    monitor_key="new_holland.intelliview_iv",
    objective="import_guidance",
    transport="usb",
    folder=_IV4_FOLDER,
    evidence=(
        f"Photographed on {_IV4_WHERE}, bringing in a line made in Ag Leader "
        "SMS for the Kinsella 2026 wheat trial."
    ),
    steps=(
        _GS3_2630_IMPORT_LINES.steps[0],
        WalkStep(
            text=(
                "The stick must carry a TASKDATA folder at its root — the "
                "ISOXML that farm software writes. This route reads ISOXML; a "
                "shapefile is a different import."
            ),
        ),
        WalkStep(
            text=(
                "At the office, in Ag Leader SMS, use «Export to Selected "
                "Display»: pick «ISO11783 Displays», then «Generic ISO11783 "
                "(v3) - Type 1». That is the one this display loaded."
            ),
            button="sms_v3.jpg",
            screen_name="SMS: Setup for Display Export",
            screen="sms_export.jpg",
            look_for=(
                "Makers on the left — «ISO11783 Displays» is near the bottom. "
                "Formats on the right, with «Generic ISO11783 (v3) - Type 1» "
                "highlighted. The v4 lines above it are for newer terminals."
            ),
        ),
        WalkStep(
            text=(
                "Plug the stick in. The port is on the back of the display, "
                "under a rubber flap."
            ),
            screen_name="The USB port",
            screen="usb_port.jpg",
            look_for=(
                "The flap lifts and the stick goes straight in. The one in the "
                "photo is 4 GB, which is plenty."
            ),
        ),
        WalkStep(
            text=(
                "On the run screen press «Back», bottom left, to reach the main "
                "menu."
            ),
            button="btn_back.jpg",
        ),
        WalkStep(
            text="Press «Data Management».",
            button="btn_data_mgmt.jpg",
            screen_name="The main menu",
            screen="main_menu.jpg",
            look_for=(
                "Ten icons. «Data Management» is top right. «Run Screens» takes "
                "you back to the run screen when you are done."
            ),
        ),
        WalkStep(
            text=(
                "Tabs run along the bottom: «Import», «Filter», «Delete», «Map», "
                "«Import2», «Export». Press «Import2» — lines come in there, "
                "not under «Import»."
            ),
            button="btn_tab_import2.jpg",
            screen_name="The Import tab — not this one",
            screen="import_tab.jpg",
            look_for=(
                "«Import» only offers crop settings and screen layouts. The "
                "lines are one tab along, under «Import2»."
            ),
        ),
        WalkStep(
            text=(
                "Press «Source» and pick «ISOXML». It is only in the list when "
                "the display can see the stick."
            ),
            button="btn_src_isoxml.jpg",
            screen_name="Source",
            screen="source_isoxml.jpg",
            look_for=(
                "«ISOXML», «Non-Intelliview 1», «Non-Intelliview 2», "
                "«Shapefile». No «ISOXML» means no stick — push it in and look "
                "again."
            ),
        ),
        WalkStep(
            text="Press «Data Type» and pick «Guidance Lines».",
            button="btn_dt_guidance.jpg",
            screen_name="Data Type",
            screen="data_type_import.jpg",
            look_for=(
                "Everything a file can carry, from boundaries to "
                "prescriptions. «Guidance Lines» is the one for AB lines; "
                "«All» takes everything on the stick."
            ),
        ),
        WalkStep(
            text=(
                "Set «Grower», «Farm» and «Field». The lists show what is in "
                "the file, so pick the trial field by its name."
            ),
            button="gff_isoxml.jpg",
            screen_name="Set and ready",
            screen="gff_file.jpg",
            look_for=(
                "Grower Kinsella_2026_Wheat, Farm Kinsella, Field Wheat — the "
                "names written into the file at the office."
            ),
        ),
        WalkStep(
            text="Press «Import», top right.",
            button="btn_import_top.jpg",
        ),
        WalkStep(
            text=(
                "«Confirm Import» asks «Import selected information?». Press "
                "«Import»."
            ),
            button="btn_import_confirm.jpg",
            screen_name="Confirm Import",
            screen="confirm_import.jpg",
            look_for="«Import» bottom left, «Cancel» bottom right.",
        ),
        WalkStep(
            text=(
                "«Import Complete» appears. Press «OK». The CN1 counts read 0, "
                "and that is normal — CN1 is a different kind of file, and "
                "your line came in as ISOXML."
            ),
            button="note_cn1.jpg",
            screen_name="Import Complete",
            screen="import_complete.jpg",
            look_for=(
                "Behind it the next screen is already waiting: «Swath Datum "
                "Mismatch Warning», with «Ignore», «Replace» and «Copy» along "
                "the bottom."
            ),
        ),
        WalkStep(
            text=(
                "If «Swath Datum Mismatch Warning» comes up, the line was saved "
                "with a different correction signal from the one this machine "
                "uses. Press «Copy»."
            ),
            button="btn_copy.jpg",
        ),
        WalkStep(
            text=(
                "«Swath Copy Info» explains the copy: it takes this machine's "
                "correction signal, and its name gets the signal added on the "
                "end. Press «Yes»."
            ),
            button="btn_yes.jpg",
            screen_name="Swath Copy Info",
            screen="copy_info.jpg",
            look_for=(
                "The names a copy can be tagged with — RTK, RTX, OmniSTAR, "
                "SBAS (WAAS/EGNOS) and the rest. «Yes» bottom left, «No» "
                "bottom right."
            ),
        ),
        WalkStep(
            text=(
                "If it answers «Swath copy has failed. Swath is already "
                "present.», the line is already on the display. Press «OK»."
            ),
            screen_name="Already present",
            screen="copy_failed.jpg",
            look_for=(
                "Not a failure to worry about. It means the display already "
                "holds this line, so there was nothing to copy."
            ),
        ),
        WalkStep(
            text=(
                "Back on the «GPS» run page, press «Swath Select», then «List», "
                "and pick the line you brought in."
            ),
            screen_name="Swath Select",
            screen="swath_select_menu.jpg",
            look_for=(
                "«List» to pick it by name, «Map» to see it drawn over the "
                "field before you drive it."
            ),
        ),
    ),
)


_IV4_EXPORT = ProcedureWalk(
    monitor_key="new_holland.intelliview_iv",
    objective="export_work_data",
    transport="usb",
    folder=_IV4_FOLDER,
    evidence=(
        f"Photographed on {_IV4_WHERE}, taking the yield map off on a 4 GB "
        "stick."
    ),
    steps=(
        *_GS3_2630_EXPORT.steps[:3],
        _IV4_IMPORT_LINES.steps[3],   # the port, under the flap
        _IV4_IMPORT_LINES.steps[4],   # «Back» to the main menu
        _IV4_IMPORT_LINES.steps[5],   # «Data Management»
        WalkStep(
            text="Press «Export», the last tab along the bottom.",
            button="btn_tab_export.jpg",
            screen_name="Export",
            screen="export_page.jpg",
            look_for=(
                "«Target», «Data Type», then «Grower», «Farm» and «Field». The "
                "small «Export» button top right only lights up once the "
                "display has found the stick."
            ),
        ),
        WalkStep(
            text=(
                "«Target» is «ISOXML». It is the only choice here, and it is "
                "what office software reads."
            ),
            screen_name="Target",
            screen="target_list.jpg",
            look_for="One entry. Nothing to decide.",
        ),
        WalkStep(
            text=(
                "Press «Data Type». «All» takes everything on the display; "
                "«Yield Map» takes only the harvest; «AsApplied Map» is for "
                "spraying and seeding."
            ),
            button="btn_dt_yield.jpg",
            screen_name="Data Type",
            screen="data_type_export.jpg",
            look_for=(
                "Guidance lines, boundaries and field marks are in the list "
                "too — «All» brings them along."
            ),
        ),
        WalkStep(
            text=(
                "Leave «Grower», «Farm» and «Field» on «All», or narrow them to "
                "the trial field."
            ),
        ),
        WalkStep(
            text="Press «Export», top right.",
            button="btn_export_top.jpg",
        ),
        WalkStep(
            text=(
                "«Confirm Export» says «Export selected information». Press "
                "«Export»."
            ),
            button="btn_export_confirm.jpg",
            screen_name="Confirm Export",
            screen="confirm_export.jpg",
            look_for="«Export» bottom left, «Cancel» bottom right.",
        ),
        WalkStep(
            text=(
                "Wait for «Export Complete», then press «OK». The CN1 counts "
                "read 0 — CN1 is a different kind of file, and this export is "
                "ISOXML."
            ),
            screen_name="Export Complete",
            screen="export_complete.jpg",
            look_for=(
                "«Expected CN1 Datatypes: 0», «Exported CN1 Datatypes: 0». The "
                "ISOXML is on the stick; check it on a computer."
            ),
        ),
        WalkStep(
            text=(
                "Pull the stick out, and copy the whole TASKDATA folder to a "
                "computer before you use the stick for anything else."
            ),
        ),
        WalkStep(
            text=(
                "When you switch the machine off, the display says «Your data "
                "is being saved». Leave the key alone until the screen goes "
                "dark."
            ),
            screen_name="Shutting down",
            screen="shutdown.jpg",
            look_for=(
                "«Please do not turn off battery key while display is shutting "
                "down.» Cutting the power here can cost you the work you just "
                "did."
            ),
        ),
    ),
)


WALKTHROUGHS: tuple[ProcedureWalk, ...] = (
    _GS3_2630_EXPORT,
    _GS3_2630_LATLON,
    _GS3_2630_IMPORT_LINES,
    _IV4_LATLON,
    _IV4_IMPORT_LINES,
    _IV4_EXPORT,
)

_BY_PROCEDURE = {
    (w.monitor_key, w.objective, w.transport): w for w in WALKTHROUGHS
}


def walkthrough_for(
    monitor_key: str, objective: str, transport: str
) -> ProcedureWalk | None:
    """The photographed version of this answer, if somebody has shot it."""
    return _BY_PROCEDURE.get((monitor_key, objective, transport))
