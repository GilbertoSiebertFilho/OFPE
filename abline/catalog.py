"""Brand / monitor / file-format catalog.

This is the research half of the platform. For every terminal we know about it
records what file the terminal will actually swallow, where on the stick that
file has to sit, and what the operator taps to get it in.

The single most important field here is :class:`SupportLevel`. There is no
universal AB line file. Roughly half the installed base runs a closed format
that no third party can write, and pretending otherwise would send a producer to
the field with a USB stick that does nothing. Every entry states plainly which
of five situations it is in, and the producer-facing UI shows that verdict
before the download button.

Sources are recorded per entry so a claim can be re-checked when firmware moves.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from enum import Enum
from typing import Iterable

__all__ = [
    "SupportLevel",
    "FileFormat",
    "MonitorProfile",
    "FORMATS",
    "MONITORS",
    "BRANDS",
    "get_monitor",
    "monitors_for_brand",
    "iter_monitors",
    "format_of",
]


class SupportLevel(str, Enum):
    """How well we can serve a given terminal, most to least direct."""

    NATIVE = "native"
    """The terminal reads a published open format and we write it in full.
    Put the file on the stick, import it, drive. ISOXML terminals live here."""

    STRUCTURAL = "structural"
    """The terminal reads a standard format (usually shapefile) but only from a
    specific folder. We write the file and build the folder tree. The format is
    right; the menu wording drifts between firmware versions."""

    DESKTOP_BRIDGE = "desktop_bridge"
    """The terminal's own format is closed, but the vendor's desktop or cloud
    software imports something open and re-exports the closed file. We produce
    the open file and document the two-step. It works, it is just not one hop."""

    NEEDS_SAMPLE = "needs_sample"
    """We know the folder layout from vendor documentation but have not
    confirmed the byte layout of the payload file. We emit our best effort plus
    a shapefile fallback, and flag it. One real export from a customer machine
    promotes this to NATIVE or STRUCTURAL."""

    API_ONLY = "api_only"
    """No file path exists at all. The only supported route is the vendor's
    cloud API, which needs a developer account and the customer's consent.
    Out of scope for the file-based release; the entry documents the manual
    fallback so a producer is never left with nothing."""

    @property
    def is_downloadable(self) -> bool:
        """Whether we produce a file the producer can actually use."""
        return self in (
            SupportLevel.NATIVE,
            SupportLevel.STRUCTURAL,
            SupportLevel.DESKTOP_BRIDGE,
            SupportLevel.NEEDS_SAMPLE,
        )

    @property
    def headline(self) -> str:
        return {
            SupportLevel.NATIVE: "Direct import",
            SupportLevel.STRUCTURAL: "Direct import (check menu wording)",
            SupportLevel.DESKTOP_BRIDGE: "Two steps, via desktop software",
            SupportLevel.NEEDS_SAMPLE: "Best effort, unverified",
            SupportLevel.API_ONLY: "No file route",
        }[self]


@dataclass(frozen=True)
class FileFormat:
    """An output format the writers know how to produce."""

    key: str
    label: str
    extension: str
    description: str
    spec: str
    """Where the format is defined, or 'proprietary'/'observed' when it is not."""


FORMATS: dict[str, FileFormat] = {
    f.key: f
    for f in [
        FileFormat(
            key="isoxml",
            label="ISOXML (ISO 11783-10)",
            extension=".zip",
            description=(
                "TASKDATA.XML holding the field as a Partfield (PFD), the swath "
                "spacing as a Guidance Group (GGP) and each line as a Guidance "
                "Pattern (GPN). The only genuinely cross-brand guidance format."
            ),
            spec="ISO 11783-10 (ISOBUS part 10), guidance elements from v4.x",
        ),
        FileFormat(
            key="shapefile",
            label="ESRI Shapefile (polyline)",
            extension=".zip",
            description=(
                "The .shp/.shx/.dbf/.prj set, WGS84 geographic. Lines carry "
                "name, pattern, swath width and heading as attributes."
            ),
            spec="ESRI Shapefile Technical Description 98-126",
        ),
        FileFormat(
            key="kml",
            label="Google Earth KML",
            extension=".kml",
            description=(
                "Human-checkable geometry. Good for verifying a line sits where "
                "you think before anyone drives it, and the import path for "
                "several European terminals."
            ),
            spec="OGC KML 2.2",
        ),
        FileFormat(
            key="agco_kml",
            label="AGCO KML",
            extension=".kml",
            description=(
                "KML shaped the way the AGCO Field Data Converter expects, so "
                "Fendt / Valtra / Massey Ferguson terminals take it through the "
                "converter alongside plain ISOXML."
            ),
            spec="AGCO Field Data Converter accepted input",
        ),
        FileFormat(
            key="geojson",
            label="GeoJSON",
            extension=".geojson",
            description=(
                "For your own GIS, FMIS or QGIS. Not a terminal format -- it is "
                "the interchange format for the office side."
            ),
            spec="RFC 7946",
        ),
        FileFormat(
            key="raven_gff",
            label="Raven GFF folder",
            extension=".zip",
            description=(
                "The Raven/GFF/<Grower>/<Farm>/<Field>/abLines tree that a "
                "Viper 4 browses when importing guidance lines."
            ),
            spec="Raven Viper 4 operator manual, observed folder layout",
        ),
        FileFormat(
            key="agopengps",
            label="AgOpenGPS",
            extension=".zip",
            description=(
                "ABLines.txt and Field.kml in the layout AgOpenGPS reads from a "
                "field directory."
            ),
            spec="AgOpenGPS field directory format, observed",
        ),
        FileFormat(
            key="cnh_multiswath",
            label="Case IH / New Holland Multiswath",
            extension=".zip",
            description=(
                "Shapefile lines laid out for the AFS Pro 700 and IntelliView "
                "IV shapefile import, which the display calls a Multiswath."
            ),
            spec="Case IH AFS Pro 700 shapefile import guide",
        ),
        FileFormat(
            key="sendto2020",
            label="Precision Planting SendTo2020",
            extension=".zip",
            description=(
                "Shapefiles at the USB root or in a SendTo2020 folder, which is "
                "where a 20|20 looks."
            ),
            spec="Precision Planting 20|20 import documentation",
        ),
        FileFormat(
            key="reference_bundle",
            label="Reference bundle",
            extension=".zip",
            description=(
                "Shapefile plus KML plus GeoJSON plus a printable instruction "
                "sheet. What we hand over when the terminal's own format is "
                "closed to us -- enough for the vendor's own software, or for a "
                "manual rebuild, to reproduce the line exactly."
            ),
            spec="n/a -- our own bundle",
        ),
    ]
}


@dataclass(frozen=True)
class MonitorProfile:
    """One terminal (or one family of near-identical terminals)."""

    key: str
    brand: str
    model: str
    aka: tuple[str, ...] = ()
    generations: str = ""
    support: SupportLevel = SupportLevel.API_ONLY
    primary_format: str = "reference_bundle"
    also_offer: tuple[str, ...] = ()
    media: str = "USB flash drive"
    filesystem: str = "FAT32"
    usb_path: str = ""
    """Where on the stick the payload goes. Empty means the drive root."""

    guidance_vocabulary: str = ""
    """What this brand calls an AB line, so the producer recognises the menu."""

    steps: tuple[str, ...] = ()
    caveats: tuple[str, ...] = ()
    common_errors: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()

    @property
    def formats(self) -> tuple[str, ...]:
        """Primary format first, then the extras, without duplicates."""
        seen: list[str] = [self.primary_format]
        for key in self.also_offer:
            if key not in seen:
                seen.append(key)
        return tuple(seen)

    @property
    def label(self) -> str:
        return f"{self.brand} {self.model}"

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "brand": self.brand,
            "model": self.model,
            "label": self.label,
            "aka": list(self.aka),
            "generations": self.generations,
            "support": self.support.value,
            "support_headline": self.support.headline,
            "downloadable": self.support.is_downloadable,
            "primary_format": self.primary_format,
            "formats": [
                {
                    "key": k,
                    "label": FORMATS[k].label,
                    "extension": FORMATS[k].extension,
                    "description": FORMATS[k].description,
                }
                for k in self.formats
                if k in FORMATS
            ],
            "media": self.media,
            "filesystem": self.filesystem,
            "usb_path": self.usb_path,
            "guidance_vocabulary": self.guidance_vocabulary,
            "steps": list(self.steps),
            "caveats": list(self.caveats),
            "common_errors": list(self.common_errors),
            "sources": list(self.sources),
        }


# Repeated verbatim across every USB-based terminal, so it lives in one place.
_USB_PREP = (
    "Format the USB stick FAT32 on a computer before you start. Exotic "
    "filesystems (exFAT, NTFS) and sticks larger than 32 GB are the single most "
    "common reason a display shows an empty import list."
)
_USB_EJECT = (
    "Eject the stick from the display's own menu before pulling it out. Yanking "
    "it mid-write is how half-written field data happens."
)


MONITORS: dict[str, MonitorProfile] = {}


def _add(profile: MonitorProfile) -> None:
    if profile.key in MONITORS:
        raise ValueError(f"duplicate monitor key {profile.key!r}")
    MONITORS[profile.key] = profile


# --------------------------------------------------------------------------- #
#  John Deere                                                                  #
# --------------------------------------------------------------------------- #
# Deere does not publish a guidance-line file format, and since the 25.3
# software update the display will not even take a setup file built by the older
# Apex desktop software. The supported route is Operations Center, either
# through the web UI (a producer can do this) or the Guidance Lines API (a
# platform integration, which needs a Deere developer account). Everything we
# ship for Deere is therefore a bridge into Operations Center.

_add(
    MonitorProfile(
        key="john_deere.gs3_2630",
        brand="John Deere",
        model="GreenStar 3 2630",
        aka=("GS3 2630", "2630"),
        generations="GS3 3.x",
        support=SupportLevel.DESKTOP_BRIDGE,
        primary_format="reference_bundle",
        also_offer=("shapefile", "kml", "geojson"),
        usb_path=r"GS3_2630\<profile>\RCD  (setup data written by Deere software)",
        guidance_vocabulary="Straight Track, AB Curve, Circle Track, Adaptive Curve",
        steps=(
            "Upload the shapefile from this bundle to John Deere Operations "
            "Center (Land > Boundaries/Guidance, or Files).",
            "In Operations Center, turn the imported line into a guidance line "
            "on the matching field.",
            "Build a setup file for a Legacy System Display and write it to the "
            "USB stick from Operations Center.",
            "Put the stick in the 2630, open Menu > GreenStar 3 > Data, and "
            "import the profile.",
            _USB_EJECT,
        ),
        caveats=(
            "There is no open file format for a 2630 guidance line. The line has "
            "to pass through Deere software; this bundle is what you feed it.",
            "Apex is discontinued. Use Operations Center.",
        ),
        common_errors=(
            "Copying a shapefile straight onto the stick and expecting the 2630 "
            "to see it -- it will not. The 2630 reads its own RCD profile only.",
        ),
        sources=(
            "John Deere StellarSupport, Gen 4 / legacy display data management",
            "Operations Center guidance line documentation",
        ),
    )
)

_add(
    MonitorProfile(
        key="john_deere.gen4",
        brand="John Deere",
        model="Gen 4 CommandCenter (4240 / 4600 / 4640)",
        aka=("Gen4", "4240", "4600", "4640 Universal"),
        generations="Gen 4 OS 10.x and 11.x",
        support=SupportLevel.DESKTOP_BRIDGE,
        primary_format="reference_bundle",
        also_offer=("shapefile", "kml", "geojson"),
        usb_path=(
            "Setup files at the drive root, written by Operations Center. "
            "(Prescriptions -- a different thing -- go in an 'Rx' folder at the "
            "root; guidance lines do not.)"
        ),
        guidance_vocabulary="Track, Straight Track, AB Curve, Circle Track, Adaptive Curve",
        steps=(
            "Upload the shapefile from this bundle into John Deere Operations "
            "Center and attach it to the right field as a guidance line.",
            "Send it to the machine wirelessly if the machine has JDLink, which "
            "skips the USB stick entirely -- this is the easiest route.",
            "Otherwise export a setup file from Operations Center onto a USB "
            "stick (8-32 GB).",
            "In the display: Menu > System > File Manager > Import Data, pick "
            "the profile, and confirm the preview lists your tracks.",
            _USB_EJECT,
        ),
        caveats=(
            "Deere's guidance file format is closed. Operations Center is the "
            "supported path, and it is a genuinely good one if the machine has "
            "JDLink -- the line arrives over the air.",
            "Since the 25.3 update, setup files from Apex or a legacy display "
            "cannot be imported directly; they must go through Operations "
            "Center first.",
            "If two tracks share a name, the display renames the incoming one "
            "-- 'Track1' becomes 'Track1(1)' rather than overwriting.",
        ),
        common_errors=(
            "Putting guidance lines in the 'Rx' folder. That folder is for "
            "prescriptions only.",
            "Using a USB stick larger than 32 GB.",
        ),
        sources=(
            "John Deere display simulator, File Manager > Import Data",
            "Gen 4 CommandCenter new-features release notes",
            "developer.deere.com, Operations Center Guidance Lines API",
        ),
    )
)

_add(
    MonitorProfile(
        key="john_deere.g5",
        brand="John Deere",
        model="G5 (G5e / G5 / G5Plus)",
        aka=("G5Plus", "G5e", "G5 Universal"),
        generations="G5 OS (shares the Gen 4 data model)",
        support=SupportLevel.DESKTOP_BRIDGE,
        primary_format="reference_bundle",
        also_offer=("shapefile", "kml", "geojson"),
        usb_path="Setup files at the drive root, written by Operations Center.",
        guidance_vocabulary="Track, Straight Track, AB Curve, Circle Track, Adaptive Curve",
        steps=(
            "Same as Gen 4: shapefile into Operations Center, attach to the "
            "field, then push wirelessly or export a setup file to USB.",
            "In the display: Menu > System > File Manager > Import Data.",
            _USB_EJECT,
        ),
        caveats=(
            "G5 and Gen 4 share setup-file handling, so anything that works for "
            "one works for the other.",
        ),
        sources=("John Deere G5 and Generation 4 compatibility chart",),
    )
)

# --------------------------------------------------------------------------- #
#  CNH -- Case IH, New Holland, Steyr                                          #
# --------------------------------------------------------------------------- #
# The split here is generational and sharp. The Voyager-era displays (Pro 700,
# IntelliView IV) take guidance lines as shapefiles, which the display calls a
# Multiswath. The current displays (Pro 1200, IntelliView 12) are ISOXML native
# -- CNH publishes its own ADAPT plugin for the format.

_add(
    MonitorProfile(
        key="case_ih.afs_pro_700",
        brand="Case IH",
        model="AFS Pro 700",
        aka=("Pro 700", "AFS Pro 600"),
        generations="Voyager-based software, v28 and later",
        support=SupportLevel.STRUCTURAL,
        primary_format="cnh_multiswath",
        also_offer=("shapefile", "kml", "geojson"),
        usb_path="Drive root (the display browses the stick for shapefiles)",
        guidance_vocabulary="Swath, Multiswath, Straight, Curve, Pivot, Headland",
        steps=(
            _USB_PREP,
            "Unzip this bundle so the .shp, .shx, .dbf and .prj files sit "
            "loose on the stick -- all four, same base name, not in a subfolder.",
            "Put the stick in the display's USB port.",
            "Go to Toolbox > Swath (or Data Management on some builds) and "
            "choose the shapefile import.",
            "Pick the Grower / Farm / Field the swath belongs to, then select "
            "the file and import.",
            "Check the swath is drawn where you expect on the run screen before "
            "engaging the steering.",
            _USB_EJECT,
        ),
        caveats=(
            "A shapefile is only complete with all four sidecar files. Copy the "
            "whole set or the display will not list it.",
            "Case IH ships its own branded USB stick (part 84398840). Any "
            "properly formatted FAT32 stick works, but if a stick misbehaves, "
            "that is the known-good one.",
            "Menu wording moved between software versions -- confirm against "
            "the operator manual for the version actually on the machine.",
        ),
        common_errors=(
            "Copying only the .shp file.",
            "Leaving the files inside a folder rather than at the drive root.",
        ),
        sources=(
            "Case IH AFS Pro 700 shapefile (.shp) import guide",
            "AFS Pro 700 software operating guide",
        ),
    )
)

_add(
    MonitorProfile(
        key="new_holland.intelliview_iv",
        brand="New Holland",
        model="IntelliView IV",
        aka=("IntelliView 4", "IV IV"),
        generations="Voyager-based software (same platform as AFS Pro 700)",
        support=SupportLevel.STRUCTURAL,
        primary_format="cnh_multiswath",
        also_offer=("shapefile", "kml", "geojson"),
        usb_path="Drive root",
        guidance_vocabulary="Swath, Multiswath, Straight, Curve, Pivot, Headland",
        steps=(
            _USB_PREP,
            "Unzip so all four shapefile parts sit loose at the drive root.",
            "Insert the stick, then Toolbox > Swath > import from USB.",
            "Select Grower / Farm / Field, then the file.",
            _USB_EJECT,
        ),
        caveats=(
            "IntelliView IV and the AFS Pro 700 are the same display in "
            "different paint. Anything that imports on one imports on the other.",
        ),
        sources=("Case IH / New Holland Voyager display documentation",),
    )
)

_add(
    MonitorProfile(
        key="case_ih.afs_pro_1200",
        brand="Case IH",
        model="AFS Pro 1200",
        aka=("Pro 1200",),
        generations="AFS Connect generation",
        support=SupportLevel.NATIVE,
        primary_format="isoxml",
        also_offer=("shapefile", "kml", "geojson"),
        usb_path="TASKDATA folder at the drive root",
        guidance_vocabulary="Swath, Guidance line, AB line, Curve, Pivot",
        steps=(
            _USB_PREP,
            "Unzip this bundle at the root of the stick so you end up with a "
            "folder literally named TASKDATA containing TASKDATA.XML.",
            "Insert the stick and open the data management / import screen.",
            "Choose the ISOXML import and select the task data on the stick.",
            "Confirm the field and its guidance lines appear, then select the "
            "line on the run screen.",
            _USB_EJECT,
        ),
        caveats=(
            "The folder must be named TASKDATA exactly, in capitals, at the "
            "root. Nested inside another folder, it will not be found.",
            "CNH publishes an ADAPT plugin for its ISOXML conventions, so this "
            "is a well-supported path rather than a hopeful one.",
        ),
        common_errors=(
            "Leaving the download zipped on the stick -- unzip it first.",
            "A TASKDATA folder inside another TASKDATA folder after unzipping.",
        ),
        sources=(
            "CNH developer portal, ISOXML ADAPT plugin guide",
            "Case IH AFS Pro 1200 software operating manual",
        ),
    )
)

_add(
    MonitorProfile(
        key="new_holland.intelliview_12",
        brand="New Holland",
        model="IntelliView 12",
        aka=("IV12", "IntelliView XII"),
        generations="PLM Intelligence generation",
        support=SupportLevel.NATIVE,
        primary_format="isoxml",
        also_offer=("shapefile", "kml", "geojson"),
        usb_path="TASKDATA folder at the drive root",
        guidance_vocabulary="Swath, Guidance line, AB line, Curve, Pivot",
        steps=(
            _USB_PREP,
            "Unzip at the root of the stick so a TASKDATA folder appears.",
            "Insert the stick, open data management and run the ISOXML import.",
            "Select the field, then pick the swath on the run screen.",
            _USB_EJECT,
        ),
        caveats=(
            "IntelliView 12 and AFS Pro 1200 are the same display; both export "
            "and import ISO 11783-10.",
        ),
        sources=(
            "CNH developer portal, ISOXML ADAPT plugin guide",
            "New Holland IntelliView 12 operating system guide",
        ),
    )
)

# --------------------------------------------------------------------------- #
#  Trimble                                                                     #
# --------------------------------------------------------------------------- #
# Trimble's own container, .agdata, is AES encrypted and only the Trimble cloud
# holds the key. No third party writes it. What does work is Trimble Ag
# Software: it imports shapefiles and syncs to the display, so we aim there.

_add(
    MonitorProfile(
        key="trimble.precision_iq",
        brand="Trimble",
        model="GFX-350 / GFX-750 / GFX-1060 / GFX-1260 / TMX-2050",
        aka=("Precision-IQ", "GFX", "TMX"),
        generations="Precision-IQ",
        support=SupportLevel.DESKTOP_BRIDGE,
        primary_format="reference_bundle",
        also_offer=("shapefile", "kml", "geojson"),
        usb_path="AgData folder at the drive root (Trimble's own layout)",
        guidance_vocabulary="Line, AB line, A+ line, Curve, Pivot, Headland",
        steps=(
            "Import the shapefile from this bundle into Trimble Ag Software "
            "(desktop or web).",
            "Attach it to the matching client / farm / field as a guidance line.",
            "Sync the display: over the air if the machine has connectivity, "
            "otherwise export from Trimble Ag Software onto a USB stick, which "
            "writes the AgData folder for you.",
            "In Precision-IQ: Data Transfer, select the USB, import the field.",
            _USB_EJECT,
        ),
        caveats=(
            "The .agdata container is AES encrypted and cloud-keyed. We cannot "
            "write one, and neither can anyone else outside Trimble. The route "
            "through Trimble Ag Software is the supported one.",
            "Prescriptions are different: those genuinely are loose shapefiles "
            "in AgData/Prescriptions. Guidance lines are not.",
        ),
        common_errors=(
            "Trying to hand-build an AgData folder. The display validates it.",
        ),
        sources=(
            "Trimble Ag Software desktop release notes",
            "Trimble Precision-IQ data management documentation",
        ),
    )
)

_add(
    MonitorProfile(
        key="trimble.fmx",
        brand="Trimble",
        model="FmX Integrated / CFX-750 / FM-1000",
        aka=("FMX", "CFX750"),
        generations="AgGPS generation (pre Precision-IQ)",
        support=SupportLevel.DESKTOP_BRIDGE,
        primary_format="reference_bundle",
        also_offer=("shapefile", "kml", "geojson"),
        usb_path="AgGPS folder at the drive root",
        guidance_vocabulary="Line, AB line, A+ line, Curve, Pivot, Headland",
        steps=(
            "Import the shapefile into Trimble Ag Software (or the legacy "
            "Farm Works desktop) and attach it to the field.",
            "Export to USB, which writes the AgGPS folder structure.",
            "In the display: Data > USB > read from the stick.",
            _USB_EJECT,
        ),
        caveats=(
            "This generation uses AgGPS rather than AgData, so files from a "
            "GFX/TMX will not drop straight onto an FmX.",
        ),
        sources=("Trimble legacy display data management documentation",),
    )
)

# --------------------------------------------------------------------------- #
#  Ag Leader                                                                   #
# --------------------------------------------------------------------------- #

_add(
    MonitorProfile(
        key="ag_leader.incommand",
        brand="Ag Leader",
        model="InCommand 800 / 1200 / InCommand Go",
        aka=("InCommand", "Integra", "Versa"),
        generations="InCommand firmware 10.x and later",
        support=SupportLevel.DESKTOP_BRIDGE,
        primary_format="reference_bundle",
        also_offer=("shapefile", "kml", "geojson"),
        usb_path="Drive root (.agsetup files, written by Ag Leader software)",
        guidance_vocabulary="Pattern, AB line, A+ heading, Adaptive Curve, Pivot, SmartPath",
        steps=(
            "Import the shapefile from this bundle into SMS Software (Basic or "
            "Advanced) and attach it to the field as a guidance pattern.",
            "Export an .agsetup file from SMS onto a USB stick, or push it "
            "through AgFiniti.",
            "In the display: tap the status indicator top-right, choose Data "
            "Transfer, then Import Setup, and pick the .agsetup.",
            _USB_EJECT,
        ),
        caveats=(
            "The .agsetup container is Ag Leader's own and is not publicly "
            "documented, so we cannot write one directly. SMS is the bridge.",
            ".agsetup files are forward compatible but not backward -- a file "
            "written by newer software may not open on an older display.",
            "If you can send us a real .agsetup export we will look at whether "
            "we can write it directly and skip the SMS step.",
        ),
        sources=(
            "Ag Leader support portal, AgSetup file supported uses",
            "Ag Leader InCommand display user guide",
        ),
    )
)

# --------------------------------------------------------------------------- #
#  Raven                                                                       #
# --------------------------------------------------------------------------- #
# The folder tree is documented in the Viper 4 manual right down to the
# 'abLines' leaf. What is not documented is what is inside the .ab file, so this
# entry is deliberately marked NEEDS_SAMPLE rather than sold as working.

_add(
    MonitorProfile(
        key="raven.viper4",
        brand="Raven",
        model="Viper 4 / Viper 4+",
        aka=("Viper4", "Viper 4 Plus"),
        generations="Raven Operating Software (ROS)",
        support=SupportLevel.NEEDS_SAMPLE,
        primary_format="raven_gff",
        also_offer=("shapefile", "kml", "geojson"),
        usb_path=r"Raven\GFF\<Grower>\<Farm>\<Field>\abLines",
        guidance_vocabulary="Guidance line, AB line, Pivot, Last Pass",
        steps=(
            _USB_PREP,
            "Unzip this bundle at the root of the stick. You should end up with "
            "Raven\\GFF\\<Grower>\\<Farm>\\<Field>\\abLines.",
            "Insert the stick and open the USB manager / file manager.",
            "Choose Guidance Lines from the file type list, then Next.",
            "Browse to the abLines folder, tick the lines you want (or Select "
            "All), and import.",
            _USB_EJECT,
        ),
        caveats=(
            "We have the folder tree from Raven's manual but have not verified "
            "the internal byte layout of a .ab file. The bundle therefore also "
            "contains the same lines as a shapefile. If the .ab import does not "
            "list your lines, use the shapefile and tell us -- one real .ab "
            "export from your machine is all we need to fix this properly.",
            "Grower / farm / field folder names must match what is already on "
            "the display, or the lines land under a new field.",
        ),
        sources=("Raven Viper installation and operator's manual, import guidance lines",),
    )
)

# --------------------------------------------------------------------------- #
#  ISOBUS terminals -- one exporter covers all of these                        #
# --------------------------------------------------------------------------- #

_ISOXML_STEPS = (
    _USB_PREP,
    "Unzip this bundle at the root of the stick so a folder named TASKDATA "
    "sits at the top level, containing TASKDATA.XML.",
    "Insert the stick in the terminal.",
    "Open the ISOBUS task controller / data import screen and run the ISOXML "
    "import.",
    "Confirm the field appears with its reference lines, then select the line "
    "you want on the run screen.",
    _USB_EJECT,
)

_ISOXML_ERRORS = (
    "Leaving the file zipped on the stick.",
    "A TASKDATA folder nested inside another folder.",
    "Renaming TASKDATA.XML -- the name is fixed by the standard.",
)

_add(
    MonitorProfile(
        key="claas.cemis_1200",
        brand="CLAAS",
        model="CEMIS 1200",
        aka=("CEMIS1200",),
        generations="CEMIS 1200 (replaced the S10 universal terminal)",
        support=SupportLevel.NATIVE,
        primary_format="isoxml",
        also_offer=("shapefile", "kml", "geojson"),
        usb_path="TASKDATA folder at the drive root",
        guidance_vocabulary="Reference track, A-B line, Contour, Circle",
        steps=_ISOXML_STEPS,
        caveats=(
            "CLAAS documents TC-BAS as importing and exporting tasks together "
            "with reference tracks and field boundaries, which is exactly what "
            "this file carries.",
            "Recent CEMIS 1200 firmware also takes shapefiles directly, so the "
            "shapefile in this bundle is a working fallback.",
        ),
        common_errors=_ISOXML_ERRORS,
        sources=(
            "CLAAS GPS PILOT CEMIS 1200 product documentation",
            "CLAAS CEMIS 1200 ISOXML import tutorials",
        ),
    )
)

_add(
    MonitorProfile(
        key="claas.s10",
        brand="CLAAS",
        model="S10 / GPS PILOT S10",
        aka=("S10",),
        generations="Legacy universal terminal",
        support=SupportLevel.NATIVE,
        primary_format="isoxml",
        also_offer=("shapefile", "kml", "geojson"),
        usb_path="TASKDATA folder at the drive root",
        guidance_vocabulary="Reference track, A-B line, Contour, Circle",
        steps=_ISOXML_STEPS,
        caveats=(
            "Extract the TASKDATA folder out of the zip onto the stick -- the "
            "S10 does not open archives.",
        ),
        common_errors=_ISOXML_ERRORS,
        sources=("CLAAS S10 task import documentation",),
    )
)

_add(
    MonitorProfile(
        key="agco.fendt_one",
        brand="Fendt",
        model="FendtONE / Varioterminal 10.4",
        aka=("Fendt One", "Varioterminal", "VarioGuide"),
        generations="FendtONE and Varioterminal",
        support=SupportLevel.NATIVE,
        primary_format="isoxml",
        also_offer=("agco_kml", "shapefile", "kml", "geojson"),
        usb_path="TASKDATA folder at the drive root",
        guidance_vocabulary="Track, A-B line, Contour track, Circle track",
        steps=(
            _USB_PREP,
            "Unzip at the root of the stick so a TASKDATA folder appears.",
            "Optionally run the file through the AGCO Field Data Converter "
            "first -- it accepts ISOXML 2.0 through 4.3, shapefile in WGS84, "
            "and AGCO KML, all of which are in this bundle.",
            "Insert the stick and import from the terminal's data screen.",
            "Select the field, then pick the track under VarioGuide.",
            _USB_EJECT,
        ),
        caveats=(
            "AGCO's own Field Data Converter explicitly handles A-B lines and "
            "curves, which makes this one of the better-supported brands.",
            "Some Fendt workflows expect the archive named TASKDATA.zip. If the "
            "terminal will not see the folder, try importing the zip as-is.",
        ),
        common_errors=_ISOXML_ERRORS,
        sources=(
            "Fendt Field Data Converter documentation",
            "Fendt task documentation systems (VarioDoc / VarioDoc Pro / Task Doc)",
        ),
    )
)

_add(
    MonitorProfile(
        key="agco.valtra_smarttouch",
        brand="Valtra",
        model="SmartTouch",
        aka=("Valtra Guide",),
        generations="SmartTouch armrest terminal",
        support=SupportLevel.NATIVE,
        primary_format="isoxml",
        also_offer=("agco_kml", "shapefile", "kml", "geojson"),
        usb_path="TASKDATA folder at the drive root",
        guidance_vocabulary="Guidance line, A-B line, Curve, Circle",
        steps=_ISOXML_STEPS,
        caveats=("Shares the AGCO data platform with Fendt and Massey Ferguson.",),
        common_errors=_ISOXML_ERRORS,
        sources=("AGCO connectivity / Field Data Converter documentation",),
    )
)

_add(
    MonitorProfile(
        key="agco.mf_datatronic",
        brand="Massey Ferguson",
        model="Datatronic 5 / 9000-series terminal",
        aka=("MF Guide", "Datatronic"),
        generations="AGCO terminal family",
        support=SupportLevel.NATIVE,
        primary_format="isoxml",
        also_offer=("agco_kml", "shapefile", "kml", "geojson"),
        usb_path="TASKDATA folder at the drive root",
        guidance_vocabulary="Guidance line, A-B line, Curve, Circle",
        steps=_ISOXML_STEPS,
        common_errors=_ISOXML_ERRORS,
        sources=("AGCO Field Data Converter documentation",),
    )
)

_add(
    MonitorProfile(
        key="topcon.x_family",
        brand="Topcon",
        model="X35 / X25 / XD / XD+",
        aka=("Horizon", "X35"),
        generations="Horizon OS",
        support=SupportLevel.NATIVE,
        primary_format="isoxml",
        also_offer=("shapefile", "kml", "geojson"),
        usb_path="TASKDATA folder at the drive root",
        guidance_vocabulary="Guideline, AB line, A+ line, Identical curve, Pivot",
        steps=(
            "Format the stick blank on a PC first -- Topcon specifically "
            "recommends a freshly quick-formatted 8-16 GB stick.",
            "Unzip at the root so a TASKDATA folder appears.",
            "Insert the stick and import from the Horizon data screen.",
            "Select the field, then choose the guideline group on the run screen.",
            "Eject the USB from the display using the eject icon before removing it.",
        ),
        caveats=(
            "Horizon is ISOBUS-native, so ISOXML is the right target. Topcon "
            "also has its own TAP cloud platform if the machine is connected.",
        ),
        common_errors=_ISOXML_ERRORS,
        sources=(
            "Topcon X family Horizon operator manual",
            "Topcon Horizon OS datasheet",
        ),
    )
)

_add(
    MonitorProfile(
        key="kverneland.isomatch",
        brand="Kverneland / Kubota",
        model="IsoMatch Tellus GO / PRO",
        aka=("IsoMatch", "Kubota K-Monitor"),
        generations="IsoMatch terminal family",
        support=SupportLevel.NATIVE,
        primary_format="isoxml",
        also_offer=("shapefile", "kml", "geojson"),
        usb_path="TASKDATA folder at the drive root",
        guidance_vocabulary="Guidance line, A-B line, Curve, Circle",
        steps=_ISOXML_STEPS,
        caveats=(
            "Kubota's K-Monitor is the same terminal family rebadged, so the "
            "same file works.",
        ),
        common_errors=_ISOXML_ERRORS,
        sources=("Kverneland IsoMatch terminal documentation",),
    )
)

_add(
    MonitorProfile(
        key="mueller.track_leader",
        brand="Müller-Elektronik",
        model="TOUCH 800 / TOUCH 1200 / BASIC Terminal (TRACK-Leader)",
        aka=("TRACK-Leader", "Horsch Touch 800", "Lemken CCI"),
        generations="TRACK-Leader v8 and later",
        support=SupportLevel.NATIVE,
        primary_format="isoxml",
        also_offer=("shapefile", "kml", "geojson"),
        usb_path="TASKDATA folder at the drive root; shapefiles in an SHP folder",
        guidance_vocabulary="Guidance line, A-B line, Contour, Circle",
        steps=(
            _USB_PREP,
            "For the ISOXML route, unzip at the root so a TASKDATA folder "
            "appears, then import from the terminal.",
            "For the shapefile route, put the shapefile set in a folder named "
            "SHP at the root -- that is where TRACK-Leader looks.",
            "Import, then select the line on the run screen.",
            _USB_EJECT,
        ),
        caveats=(
            "TRACK-Leader's own store is an 'ngstore' database, and ngstore "
            "folders only move between terminals of the same type -- so do not "
            "try to hand-copy one. Import through ISOXML or shapefile instead.",
            "From v8 the terminal writes shp and kml into an SHP directory on "
            "the stick when you synchronise, which is a good way to see the "
            "naming it expects.",
        ),
        common_errors=_ISOXML_ERRORS,
        sources=("Müller-Elektronik TRACK-Leader operating instructions, v8",),
    )
)

# --------------------------------------------------------------------------- #
#  Sprayer / planter specialists and open systems                              #
# --------------------------------------------------------------------------- #

_add(
    MonitorProfile(
        key="precision_planting.2020",
        brand="Precision Planting",
        model="20|20 (Gen 1 / 2 / 3)",
        aka=("2020", "SeedSense"),
        generations="20|20 firmware",
        support=SupportLevel.STRUCTURAL,
        primary_format="sendto2020",
        also_offer=("shapefile", "kml", "geojson"),
        usb_path="Drive root, or a folder named SendTo2020",
        guidance_vocabulary="Guidance line, AB line, Pivot, Boundary",
        steps=(
            _USB_PREP,
            "Unzip so the shapefile set is either loose at the drive root or "
            "inside a folder named exactly SendTo2020.",
            "Insert the stick in the USB port on the upper left of the display.",
            "Home > Setup > Data > Import, then choose the file.",
            "Assign it to the right field.",
            _USB_EJECT,
        ),
        caveats=(
            "20|20 is fussy about depth -- files must not be buried in nested "
            "folders.",
            "The display's own prescription container is .2020; guidance and "
            "boundary geometry go in as shapefiles.",
        ),
        sources=("Precision Planting 20|20 import documentation and help centre",),
    )
)

_add(
    MonitorProfile(
        key="teejet.matrix_pro_gs",
        brand="TeeJet",
        model="Matrix Pro 570GS / 840GS / Aeros 9040",
        aka=("Matrix Pro GS", "Aeros"),
        generations="Matrix Pro GS v4.x",
        support=SupportLevel.STRUCTURAL,
        primary_format="shapefile",
        also_offer=("kml", "geojson", "isoxml"),
        usb_path="Drive root, under the console's job data folder",
        guidance_vocabulary="Guideline, Straight AB, Curved AB, Adaptive Curve, Pivot",
        steps=(
            _USB_PREP,
            "Unzip the shapefile set onto the stick.",
            "Insert the stick, then Configuration > Data > Job Data > Transfer.",
            "Copy the job in from USB Storage.",
            "Open the job and confirm the guideline is drawn.",
            _USB_EJECT,
        ),
        caveats=(
            "The Matrix moves whole jobs rather than bare lines, so the line "
            "arrives attached to a job. It exports shp, kml and pdf, which is a "
            "good way to confirm the shape it expects.",
        ),
        sources=("TeeJet Matrix Pro GS user manual and release notes",),
    )
)

_add(
    MonitorProfile(
        key="agopengps.aog",
        brand="AgOpenGPS",
        model="AgOpenGPS",
        aka=("AOG",),
        generations="AgOpenGPS v5 and later",
        support=SupportLevel.NEEDS_SAMPLE,
        primary_format="agopengps",
        also_offer=("kml", "shapefile", "geojson", "isoxml"),
        usb_path="The field folder under the AgOpenGPS Fields directory",
        guidance_vocabulary="AB line, AB curve, Contour",
        steps=(
            "Unzip the bundle into your AgOpenGPS Fields directory, so the "
            "field folder sits alongside your other fields.",
            "Start AgOpenGPS and open the field.",
            "The AB lines appear in the line picker. If they do not, or if they "
            "appear rotated, use the Field.kml in the same folder instead and "
            "tell us -- see the caveat below.",
        ),
        caveats=(
            "AgOpenGPS is open source, so its geometry convention is known: "
            "coordinates are metres east and north of the field origin recorded "
            "in Field.txt. What we have NOT been able to confirm is the field "
            "order within each line of ABLines.txt, and that ordering has "
            "changed between AgOpenGPS versions. If the lines come in rotated "
            "or in the wrong place, send us one ABLines.txt written by your own "
            "AgOpenGPS and we will match it exactly.",
            "Field.kml is written alongside and is unambiguous, so there is "
            "always a working route.",
        ),
        sources=(
            "AgOpenGPS field directory layout (x = easting, y = northing, "
            "relative to the origin in Field.txt)",
        ),
    )
)

_add(
    MonitorProfile(
        key="generic.isobus",
        brand="Generic",
        model="Any ISOBUS terminal (TC-BAS or better)",
        aka=("ISOBUS", "ISOXML", "TASKDATA"),
        generations="ISO 11783-10",
        support=SupportLevel.NATIVE,
        primary_format="isoxml",
        also_offer=("shapefile", "kml", "geojson"),
        usb_path="TASKDATA folder at the drive root",
        guidance_vocabulary="Guidance pattern, reference line, A-B line",
        steps=_ISOXML_STEPS,
        caveats=(
            "If your terminal is not listed by name, try this. Any terminal "
            "advertising TC-BAS should read the file.",
        ),
        common_errors=_ISOXML_ERRORS,
        sources=("ISO 11783-10",),
    )
)

_add(
    MonitorProfile(
        key="generic.gis",
        brand="Generic",
        model="Office GIS / FMIS (QGIS, ArcGIS, farm software)",
        aka=("GIS", "QGIS", "FMIS"),
        generations="n/a",
        support=SupportLevel.NATIVE,
        primary_format="shapefile",
        also_offer=("geojson", "kml", "isoxml"),
        usb_path="n/a",
        guidance_vocabulary="Polyline",
        steps=(
            "Unzip and open the .shp in your GIS, or drop the .geojson straight "
            "in.",
            "Coordinates are WGS84 geographic (EPSG:4326).",
        ),
        caveats=(
            "This is the office format, not a terminal format. Use it to check "
            "geometry, or to hand a line to software we do not cover yet.",
        ),
        sources=(),
    )
)


BRANDS: list[str] = sorted({m.brand for m in MONITORS.values()})


def get_monitor(key: str) -> MonitorProfile:
    try:
        return MONITORS[key]
    except KeyError:
        raise KeyError(
            f"unknown monitor {key!r}. Known keys: {', '.join(sorted(MONITORS))}"
        ) from None


def monitors_for_brand(brand: str) -> list[MonitorProfile]:
    return [m for m in MONITORS.values() if m.brand.lower() == brand.lower()]


def iter_monitors() -> Iterable[MonitorProfile]:
    return MONITORS.values()


def format_of(key: str) -> FileFormat:
    try:
        return FORMATS[key]
    except KeyError:
        raise KeyError(
            f"unknown format {key!r}. Known keys: {', '.join(sorted(FORMATS))}"
        ) from None
