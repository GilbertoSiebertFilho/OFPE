"""The procedure knowledge base: how to get files in and out of a display.

This is the centre of the platform. Generating a guidance line is a side
quest; the thing people actually need at 6am with a USB stick in their hand is
*where exactly does this file go, and which button do I press*.

A procedure is addressed by five coordinates, and the UI asks for them in that
order because each answer narrows the next:

    equipment type -> brand -> monitor -> software version -> objective -> transport

The **version** axis matters more than it looks. The same display with a
different software release moves menus, renames "Data Transfer" to "File
Manager", and in one notable case stops accepting a file format it used to
take. A procedure written for the wrong release sends someone hunting for a
menu that is not there. Where a version genuinely changes the steps there is a
version-specific entry; where it does not, one entry marked ``ANY_VERSION``
covers the lot, and :func:`resolve` reports which one it used so the answer is
never silently generic.

Confidence is recorded per procedure, honestly:

``VERIFIED``
    Format and folder path confirmed against the cited source.
``CONFIRM_ON_MACHINE``
    The structure is right, but the exact menu wording moves between releases.
    Check it against the machine and tell us what it actually said.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from enum import Enum
from typing import Iterable

__all__ = [
    "Direction",
    "Transport",
    "Confidence",
    "EquipmentType",
    "Objective",
    "MonitorVersion",
    "Procedure",
    "ANY_VERSION",
    "OBJECTIVES",
    "MONITOR_VERSIONS",
    "PROCEDURES",
    "resolve",
    "available_objectives",
    "available_transports",
    "versions_for",
    "objective",
]

ANY_VERSION = "*"
"""Version key meaning 'the steps are the same on every release'."""


class Direction(str, Enum):
    """Which way the data is moving. This is the first thing a user knows."""

    TO_MONITOR = "to_monitor"
    """Office to machine: prescriptions, guidance lines, boundaries, setup."""

    FROM_MONITOR = "from_monitor"
    """Machine to office: as-applied, yield, recorded lines and boundaries."""

    ON_MONITOR = "on_monitor"
    """Neither: updating software, preparing media, taking a backup."""

    @property
    def label(self) -> str:
        return {
            Direction.TO_MONITOR: "Put data into the monitor",
            Direction.FROM_MONITOR: "Get data out of the monitor",
            Direction.ON_MONITOR: "Work on the monitor itself",
        }[self]


class Transport(str, Enum):
    """How the data travels."""

    USB = "usb"
    CLOUD = "cloud"
    DESKTOP = "desktop"

    @property
    def label(self) -> str:
        return {
            Transport.USB: "USB flash drive",
            Transport.CLOUD: "Wireless / manufacturer's cloud platform",
            Transport.DESKTOP: "Manufacturer's desktop software",
        }[self]

    @property
    def description(self) -> str:
        return {
            Transport.USB: (
                "A stick you carry to the machine. Works with no connectivity "
                "and is the fallback when anything else fails."
            ),
            Transport.CLOUD: (
                "The file arrives over the air. Needs a connected machine and "
                "an active subscription, but nobody has to walk to the shed."
            ),
            Transport.DESKTOP: (
                "The manufacturer's own PC software writes the display's file. "
                "Slower, but it is the only route for the closed formats."
            ),
        }[self]


class Confidence(str, Enum):
    VERIFIED = "verified"
    CONFIRM_ON_MACHINE = "confirm_on_machine"

    @property
    def label(self) -> str:
        return {
            Confidence.VERIFIED: "Verified against the cited source",
            Confidence.CONFIRM_ON_MACHINE: "Confirm the menu wording on the machine",
        }[self]


class EquipmentType(str, Enum):
    TRACTOR = "tractor"
    COMBINE = "combine"
    SPRAYER = "sprayer"
    PLANTER = "planter"
    SEEDER = "seeder"
    SPREADER = "spreader"
    FORAGE = "forage"
    UNIVERSAL = "universal"

    @property
    def label(self) -> str:
        return {
            EquipmentType.TRACTOR: "Tractor",
            EquipmentType.COMBINE: "Combine harvester",
            EquipmentType.SPRAYER: "Self-propelled sprayer",
            EquipmentType.PLANTER: "Planter",
            EquipmentType.SEEDER: "Seeder / air drill",
            EquipmentType.SPREADER: "Fertiliser spreader",
            EquipmentType.FORAGE: "Forage harvester",
            EquipmentType.UNIVERSAL: "Universal / retrofit display",
        }[self]


@dataclass(frozen=True)
class Objective:
    """Something a person wants to accomplish, in their words not ours."""

    key: str
    label: str
    direction: Direction
    description: str
    typical_formats: str = ""

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "direction": self.direction.value,
            "direction_label": self.direction.label,
            "description": self.description,
            "typical_formats": self.typical_formats,
        }


OBJECTIVES: dict[str, Objective] = {
    o.key: o
    for o in [
        Objective(
            key="import_prescription",
            label="Load a variable-rate prescription",
            direction=Direction.TO_MONITOR,
            description=(
                "A rate map the machine follows: seed, fertiliser, chemical. "
                "The most common file anyone loads."
            ),
            typical_formats="Shapefile (polygon), ISOXML, brand-specific Rx",
        ),
        Objective(
            key="import_guidance",
            label="Load guidance lines (AB / curves)",
            direction=Direction.TO_MONITOR,
            description="Reference lines the autosteer follows.",
            typical_formats="ISOXML, shapefile, brand setup file",
        ),
        Objective(
            key="import_boundary",
            label="Load field boundaries",
            direction=Direction.TO_MONITOR,
            description=(
                "The outline of the field, used for section control, headland "
                "management and area reporting."
            ),
            typical_formats="Shapefile (polygon), ISOXML, KML",
        ),
        Objective(
            key="import_setup",
            label="Load client / farm / field setup",
            direction=Direction.TO_MONITOR,
            description=(
                "The naming structure the machine files its work under. Get it "
                "right and every later export lands in the correct folder."
            ),
            typical_formats="Brand setup file, ISOXML",
        ),
        Objective(
            key="export_work_data",
            label="Pull off work data (yield / as-applied)",
            direction=Direction.FROM_MONITOR,
            description=(
                "What the machine actually did. The record you bill from, map "
                "from and plan next season from."
            ),
            typical_formats="Brand data package, ISOXML task data",
        ),
        Objective(
            key="export_guidance",
            label="Pull off guidance lines",
            direction=Direction.FROM_MONITOR,
            description=(
                "Lines recorded in the cab, so they can be backed up, sent to "
                "another machine, or converted to another brand."
            ),
            typical_formats="Brand setup file, ISOXML, shapefile",
        ),
        Objective(
            key="export_boundary",
            label="Pull off field boundaries",
            direction=Direction.FROM_MONITOR,
            description=(
                "Boundaries recorded by driving the perimeter -- usually the "
                "most accurate outline anyone has of that field."
            ),
            typical_formats="Brand setup file, ISOXML, shapefile",
        ),
        Objective(
            key="export_backup",
            label="Take a full backup of the display",
            direction=Direction.FROM_MONITOR,
            description=(
                "Everything at once, before a software update or before the "
                "machine changes hands."
            ),
            typical_formats="Brand backup package",
        ),
        Objective(
            key="software_update",
            label="Update the display software",
            direction=Direction.ON_MONITOR,
            description="Install a new release on the terminal itself.",
            typical_formats="Manufacturer update package",
        ),
        Objective(
            key="prepare_media",
            label="Prepare the USB stick correctly",
            direction=Direction.ON_MONITOR,
            description=(
                "The step everyone skips, and the reason most imports show an "
                "empty list."
            ),
            typical_formats="n/a",
        ),
    ]
}


@dataclass(frozen=True)
class MonitorVersion:
    """One software release, or an era of them."""

    key: str
    label: str
    notes: str = ""

    def to_dict(self) -> dict:
        return {"key": self.key, "label": self.label, "notes": self.notes}


# Version lists per monitor, oldest first. These are the choices the user picks
# from; a monitor absent from this map offers only "any version".
MONITOR_VERSIONS: dict[str, tuple[MonitorVersion, ...]] = {
    "john_deere.gs3_2630": (
        MonitorVersion("gs3_3x", "GreenStar 3 software 3.x", "The only line still supported"),
    ),
    "john_deere.gen4": (
        MonitorVersion("gen4_10x", "Gen 4 OS 10.x", "Roughly 2016-2019 machines"),
        MonitorVersion("gen4_11x", "Gen 4 OS 11.x", "Roughly 2020-2024"),
        MonitorVersion(
            "gen4_2025_3",
            "2025-3 update or newer",
            "Legacy Apex setup files are no longer accepted directly",
        ),
    ),
    "john_deere.g5": (
        MonitorVersion("g5_base", "G5 OS before the 2025-3 update"),
        MonitorVersion(
            "g5_2025_3",
            "2025-3 update or newer",
            "Legacy Apex setup files are no longer accepted directly",
        ),
    ),
    "case_ih.afs_pro_700": (
        MonitorVersion("pro700_28", "Software 28.x"),
        MonitorVersion("pro700_29", "Software 29.x"),
        MonitorVersion("pro700_30", "Software 30.x or newer"),
    ),
    "case_ih.afs_pro_1200": (
        MonitorVersion("pro1200_all", "AFS Connect software (all releases)"),
    ),
    "new_holland.intelliview_iv": (
        MonitorVersion("iv4_all", "All releases"),
    ),
    "new_holland.intelliview_12": (
        MonitorVersion("iv12_all", "PLM Intelligence software (all releases)"),
    ),
    "trimble.precision_iq": (
        MonitorVersion("piq_all", "Precision-IQ (all releases)"),
    ),
    "trimble.fmx": (
        MonitorVersion("aggps_all", "FmX / AgGPS firmware (all releases)"),
    ),
    "ag_leader.incommand": (
        MonitorVersion("ic_1_3", "Firmware 1.x to 3.x"),
        MonitorVersion("ic_4_9", "Firmware 4.x to 9.x"),
        MonitorVersion("ic_10", "Firmware 10.x or newer", "Needed for InCommand Go"),
    ),
    "raven.viper4": (
        MonitorVersion("ros_3x", "Raven OS 3.x"),
        MonitorVersion("ros_4x", "Raven OS 4.x"),
    ),
    "topcon.x_family": (
        MonitorVersion("horizon_5", "Horizon 5.x"),
        MonitorVersion("horizon_6", "Horizon 6.x or newer"),
    ),
    "claas.cemis_1200": (
        MonitorVersion("cemis_fp1", "FP1"),
        MonitorVersion("cemis_fp2", "FP2 or newer", "Adds direct shapefile import"),
    ),
    "claas.s10": (
        MonitorVersion("s10_all", "All releases"),
    ),
    "agco.fendt_one": (
        MonitorVersion("vario_terminal", "Varioterminal (pre-FendtONE)"),
        MonitorVersion("fendt_one", "FendtONE"),
    ),
    "agco.valtra_smarttouch": (
        MonitorVersion("smarttouch_all", "All releases"),
    ),
    "agco.mf_datatronic": (
        MonitorVersion("datatronic_all", "All releases"),
    ),
    "kverneland.isomatch": (
        MonitorVersion("isomatch_all", "All releases"),
    ),
    "mueller.track_leader": (
        MonitorVersion("tl_7", "TRACK-Leader v7 or older"),
        MonitorVersion("tl_8", "TRACK-Leader v8 or newer", "Writes SHP and KML to USB"),
    ),
    "precision_planting.2020": (
        MonitorVersion("pp_gen12", "20|20 Gen 1 / Gen 2"),
        MonitorVersion("pp_gen3", "20|20 Gen 3"),
    ),
    "teejet.matrix_pro_gs": (
        MonitorVersion("matrix_4x", "Matrix Pro GS v4.x"),
    ),
    "agopengps.aog": (
        MonitorVersion("aog_5", "AgOpenGPS v5"),
        MonitorVersion("aog_6", "AgOpenGPS v6 or newer"),
    ),
    "generic.isobus": (
        MonitorVersion("isobus_all", "Any TC-BAS capable terminal"),
    ),
    "generic.gis": (
        MonitorVersion("gis_all", "Any GIS or farm management software"),
    ),
}


@dataclass(frozen=True)
class Procedure:
    """One answer: this display, this release, this job, this route."""

    monitor_key: str
    objective: str
    transport: Transport
    version_keys: tuple[str, ...] = (ANY_VERSION,)
    """Which releases these steps are written for.

    A set rather than a single key, because software lines share behaviour in
    runs: Case IH 28.x and 29.x take the same menu path and 30.x moved it. The
    alternative -- one entry per release -- leaves holes, and a hole here means
    the wizard silently stops offering a job the machine can definitely do.
    """

    file_format: str = ""
    """What the file must be, in words a person can check."""

    extensions: tuple[str, ...] = ()
    """The files the person physically places on the media.

    Not "formats involved anywhere in the workflow". A shapefile fed into
    Operations Center on the way to a 2630 does not belong here, because the
    operator never copies a .shp to that stick -- listing it would send them
    looking for files that should not be there.
    """

    media_path: str = ""
    """Exact location on the stick. Empty when the transport has no media."""

    filesystem: str = "FAT32"
    minutes: int = 10
    """Rough time to allow, so nobody starts this five minutes before dark."""

    prerequisites: tuple[str, ...] = ()
    steps: tuple[str, ...] = ()
    verify: tuple[str, ...] = ()
    """How to tell it actually worked, before driving away."""

    cautions: tuple[str, ...] = ()
    common_errors: tuple[str, ...] = ()
    confidence: Confidence = Confidence.CONFIRM_ON_MACHINE
    sources: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        obj = OBJECTIVES[self.objective]
        return {
            "monitor_key": self.monitor_key,
            "objective": self.objective,
            "objective_label": obj.label,
            "direction": obj.direction.value,
            "direction_label": obj.direction.label,
            "transport": self.transport.value,
            "transport_label": self.transport.label,
            "version_keys": list(self.version_keys),
            "file_format": self.file_format,
            "extensions": list(self.extensions),
            "media_path": self.media_path,
            "filesystem": self.filesystem,
            "minutes": self.minutes,
            "prerequisites": list(self.prerequisites),
            "steps": list(self.steps),
            "verify": list(self.verify),
            "cautions": list(self.cautions),
            "common_errors": list(self.common_errors),
            "confidence": self.confidence.value,
            "confidence_label": self.confidence.label,
            "sources": list(self.sources),
        }


PROCEDURES: list[Procedure] = []


def _add(**kwargs) -> None:
    if "version_key" in kwargs:
        key = kwargs.pop("version_key")
        kwargs["version_keys"] = (key,) if isinstance(key, str) else tuple(key)
    if isinstance(kwargs.get("transport"), str):
        kwargs["transport"] = Transport(kwargs["transport"])
    if isinstance(kwargs.get("confidence"), str):
        kwargs["confidence"] = Confidence(kwargs["confidence"])
    procedure = Procedure(**kwargs)
    if procedure.objective not in OBJECTIVES:
        raise ValueError(f"unknown objective {procedure.objective!r}")
    PROCEDURES.append(procedure)


# Repeated wording, defined once so a wording fix lands everywhere.
_FAT32 = (
    "Format the stick FAT32 with an MBR partition on a computer before you "
    "start. exFAT, NTFS and sticks over 32 GB are the single most common reason "
    "a display shows an empty import list."
)
_EJECT = (
    "Eject the stick from the display's own menu before pulling it out. Pulling "
    "it mid-write is how half-written data happens."
)
_SHP_SET = (
    "Copy all four shapefile parts (.shp, .shx, .dbf, .prj) with the same base "
    "name. A lone .shp will not import."
)
_NO_ACCENTS = (
    "Keep file names short, with no accents and no spaces. Several displays "
    "silently skip files they cannot render."
)


# =========================================================================== #
#  JOHN DEERE                                                                 #
# =========================================================================== #

_add(
    monitor_key="john_deere.gen4",
    objective="import_prescription",
    transport=Transport.USB,
    file_format="Complete shapefile: .shp + .shx + .dbf + .prj, same base name",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="Rx\\  — at the ROOT of the stick, not inside another folder",
    minutes=10,
    prerequisites=(
        "The prescription must be POLYGON geometry in WGS84, with at least one "
        "NUMERIC column holding the rate.",
    ),
    steps=(
        _FAT32,
        "At the ROOT of the stick create a folder named exactly Rx.",
        "Copy the four shapefile parts into Rx.",
        "With the machine powered up, plug the stick into the display's USB port.",
        "Tap the Menu button, bottom left of the screen.",
        "Open File Manager.",
        "Choose Import Data, select the USB as the source, and tick the prescription.",
        "Confirm and wait for the progress bar to finish.",
        "Go to Work Setup > Field > Prescription, choose the file, then choose "
        "the RATE COLUMN and the UNIT.",
    ),
    verify=(
        "The prescription map draws on the run screen in the right place.",
        "The rate legend shows sensible numbers, not zeros or blanks -- blanks "
        "mean the rate column was read as text.",
    ),
    cautions=(_NO_ACCENTS, _EJECT),
    common_errors=(
        "Missing .prj, so the display has no projection and puts the field in "
        "the wrong place.",
        "Shapefile written in UTM instead of WGS84.",
        "Rate column stored as TEXT rather than a number.",
        "The Rx folder nested inside another folder.",
        "Line or point geometry instead of polygon.",
    ),
    confidence=Confidence.VERIFIED,
    sources=(
        "John Deere StellarSupport, Gen 4 File Manager",
        "Gen 4 CommandCenter release notes",
    ),
)

_add(
    monitor_key="john_deere.gen4",
    objective="export_work_data",
    transport=Transport.USB,
    file_format="Display data package (folders the display creates itself)",
    media_path="Work data -> JD-Data\\   |   Setup data -> JD4600\\",
    minutes=15,
    prerequisites=("End or pause the job so everything is written to disk.",),
    steps=(
        _FAT32,
        "Use ONE stick per display. Mixing machines on one stick overwrites folders.",
        "End or pause the current job.",
        "Plug the stick into the display's USB port.",
        "Menu > File Manager.",
        "Choose Export Data.",
        "Choose Work Data — the display writes into a JD-Data folder.",
        "If you also need the client/farm/field structure, choose Setup Data — "
        "that writes into JD4600.",
        "Wait for the progress bar to finish completely.",
        _EJECT,
    ),
    verify=(
        "On a computer, confirm the JD-Data folder exists and is not empty.",
        "Import it into Operations Center and check the field and date look right.",
    ),
    cautions=(
        "Exporting with the job still open can produce an incomplete file. "
        "Always wait for the on-screen confirmation.",
    ),
    common_errors=(
        "Pulling the stick out early.",
        "Reusing one stick across several displays and overwriting folders.",
        "Formatting the stick exFAT or NTFS.",
    ),
    confidence=Confidence.VERIFIED,
    sources=("John Deere StellarSupport, Generation 4 Displays File Manager",),
)

_add(
    monitor_key="john_deere.gen4",
    objective="import_guidance",
    transport=Transport.USB,
    version_key=("gen4_10x", "gen4_11x"),
    file_format="Setup file exported from Operations Center for a Gen 4 display",
    media_path="JD4600\\  — the setup folder Operations Center writes",
    minutes=20,
    prerequisites=(
        "There is no open guidance-line file for this display. The line has to "
        "pass through Operations Center first.",
    ),
    steps=(
        "In Operations Center, select the client, farm and field, and the "
        "guidance lines you want.",
        "Generate a setup file for a Gen 4 display and download it.",
        "Copy the generated folder to the ROOT of the stick, keeping its "
        "structure exactly as downloaded.",
        "Plug the stick into the display.",
        "Menu > File Manager > Import Data.",
        "Select the setup package and confirm.",
        "Choose REPLACE or MERGE. Choose MERGE unless you are certain.",
        "Open Work Setup > Guidance and select the imported track.",
    ),
    verify=(
        "The track name appears in the guidance list under the right field.",
        "Drive one pass with steering off and confirm the machine tracks it.",
    ),
    cautions=(
        "REPLACE erases setup data already on the display. MERGE is the safe "
        "choice.",
    ),
    common_errors=(
        "Renaming or reorganising the folders inside the package — the display "
        "stops recognising it.",
        "Importing a setup package built for a different display generation.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("John Deere Operations Center / StellarSupport",),
)

_add(
    monitor_key="john_deere.gen4",
    objective="import_guidance",
    transport=Transport.USB,
    version_key="gen4_2025_3",
    file_format="Setup file exported from Operations Center (Current System Display format)",
    media_path="JD4600\\  — the setup folder Operations Center writes",
    minutes=20,
    prerequisites=(
        "From the 2025-3 update onward, setup files built by Apex or by a "
        "legacy display are NO LONGER accepted directly. They must be uploaded "
        "to Operations Center first and re-exported in the current format.",
    ),
    steps=(
        "If your file came from Apex or an older display, upload it to "
        "Operations Center first and let it convert.",
        "In Operations Center, select client, farm, field and the guidance lines.",
        "Generate a setup file in the Current System Display format and download it.",
        "Copy the folder to the ROOT of the stick, unchanged.",
        "Plug the stick into the display.",
        "Menu > File Manager > Import Data.",
        "Select the package, choose MERGE, and confirm.",
        "Open Work Setup > Guidance and select the track.",
    ),
    verify=(
        "The import preview lists your tracks before you confirm. If the "
        "preview is empty, the file is in the old format.",
    ),
    cautions=(
        "If two tracks share a name, the display renames the incoming one — "
        "Track1 becomes Track1(1) rather than overwriting.",
    ),
    common_errors=(
        "Trying to import an Apex-era setup file directly. On this release it "
        "will simply not appear.",
    ),
    confidence=Confidence.VERIFIED,
    sources=(
        "John Deere StellarSupport, Generation 4 and G5 data management, "
        "2025-3 release notes",
    ),
)

_add(
    monitor_key="john_deere.gen4",
    objective="import_prescription",
    transport=Transport.CLOUD,
    file_format="Prescription published in Operations Center, sent over the air",
    media_path="",
    filesystem="n/a — wireless",
    minutes=10,
    prerequisites=(
        "The machine needs an active MTG / JDLink connection and must show as "
        "connected in Operations Center.",
    ),
    steps=(
        "Confirm the machine appears as connected in Operations Center.",
        "Upload the prescription under Files, or build it in Operations Center.",
        "Attach it to the correct client, farm and field.",
        "Use Send to Machine and pick the target machine.",
        "In the cab, accept the incoming transfer notification.",
        "Menu > File Manager to confirm the file arrived.",
        "Work Setup > Prescription: select the file, the rate column and the unit.",
    ),
    verify=("The map draws on the run screen with a sensible rate legend.",),
    cautions=(
        "Wireless transfer needs an active data subscription. If Send to "
        "Machine is greyed out, that is usually why.",
    ),
    common_errors=(
        "Sending to the wrong machine in a fleet with similar names.",
        "The operator never accepting the notification in the cab.",
    ),
    confidence=Confidence.VERIFIED,
    sources=("John Deere Operations Center documentation",),
)

_add(
    monitor_key="john_deere.gen4",
    objective="export_work_data",
    transport=Transport.CLOUD,
    file_format="Automatic sync to Operations Center",
    media_path="",
    filesystem="n/a — wireless",
    minutes=5,
    prerequisites=("MTG / JDLink active and the machine paired to the organisation.",),
    steps=(
        "Confirm the machine is connected in Operations Center.",
        "Confirm Data Sync is enabled on the display: Menu > System > "
        "Wireless Data Transfer.",
        "Work data uploads on its own as the job runs — no operator action.",
        "In Operations Center, open Field Analyzer to see the coverage arrive.",
        "If a job is missing, end the job in the cab to force the final upload.",
    ),
    verify=("The job appears in Operations Center with the expected area.",),
    cautions=(
        "Wireless sync does not remove the need for an occasional USB backup. "
        "A machine that loses connectivity mid-season buffers, but not forever.",
    ),
    common_errors=(
        "Assuming sync is on when it was never enabled on the display.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("John Deere Operations Center / JDLink documentation",),
)

_add(
    monitor_key="john_deere.gen4",
    objective="export_guidance",
    transport=Transport.USB,
    file_format="Setup data package written by the display",
    media_path="JD4600\\",
    minutes=10,
    steps=(
        _FAT32,
        "Plug the stick into the display.",
        "Menu > File Manager > Export Data.",
        "Choose Setup Data (not Work Data) — guidance lines live in setup.",
        "Select the client, farm and fields whose tracks you want.",
        "Wait for the progress bar, then eject from the menu.",
        "At the office, upload the JD4600 folder to Operations Center.",
    ),
    verify=(
        "The JD4600 folder exists on the stick and is not empty.",
        "Operations Center lists the tracks against the right fields after upload.",
    ),
    cautions=(
        "Guidance lines are setup data, not work data. Exporting only Work Data "
        "will not include them, which surprises people.",
    ),
    common_errors=("Exporting Work Data and wondering where the tracks went.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("John Deere StellarSupport, Gen 4 File Manager",),
)

_add(
    monitor_key="john_deere.gs3_2630",
    objective="import_prescription",
    transport=Transport.USB,
    file_format=(
        "A setup profile built by Operations Center. You feed Operations "
        "Center a shapefile; it writes the profile the 2630 reads."
    ),
    media_path="GS3_2630\\<Profile>\\RCD\\",
    minutes=20,
    prerequisites=(
        "The 2630 does not browse a bare stick. Data must sit inside the "
        "GS3_2630 profile structure written by Deere software.",
    ),
    steps=(
        _FAT32,
        "In Operations Center, build a setup file for a Legacy System Display "
        "including the prescription.",
        "Write it to the stick from Operations Center — it creates the "
        "GS3_2630 folder structure for you.",
        "Plug the stick into the 2630.",
        "Menu > GreenStar 3 > Data > Import.",
        "Select the profile and confirm.",
        "Under Field Setup, attach the prescription to the field and choose the "
        "rate column.",
    ),
    verify=("The prescription draws on the map page before you start.",),
    cautions=(
        "Apex is discontinued; use Operations Center.",
        "Do not hand-build the GS3_2630 folder tree — the display validates it.",
    ),
    common_errors=(
        "Copying a loose shapefile to the stick root. The 2630 will not see it.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("John Deere StellarSupport, legacy display data management",),
)

_add(
    monitor_key="john_deere.gs3_2630",
    objective="export_work_data",
    transport=Transport.USB,
    file_format="GS3 data package",
    media_path="GS3_2630\\<Profile>\\RCD\\",
    minutes=15,
    steps=(
        _FAT32,
        "End the job so the last records are written.",
        "Plug the stick into the 2630.",
        "Menu > GreenStar 3 > Data > Export.",
        "Select the profile and confirm.",
        "Wait for the confirmation message before removing the stick.",
        "At the office, upload the whole GS3_2630 folder to Operations Center.",
    ),
    verify=("Operations Center shows the job with the expected area and date.",),
    cautions=("Upload the entire folder, not selected files inside it.",),
    common_errors=("Uploading only the RCD contents without the parent folders.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("John Deere StellarSupport, legacy display data management",),
)

_add(
    monitor_key="john_deere.g5",
    objective="import_prescription",
    transport=Transport.USB,
    file_format="Complete shapefile: .shp + .shx + .dbf + .prj, same base name",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="Rx\\  — at the ROOT of the stick",
    minutes=10,
    prerequisites=("Polygon geometry, WGS84, with a numeric rate column.",),
    steps=(
        _FAT32,
        "Create a folder named exactly Rx at the ROOT of the stick.",
        "Copy the four shapefile parts into it.",
        "Plug the stick into the display.",
        "Menu > System > File Manager > Import Data.",
        "Select the prescription and confirm.",
        "Work Setup > Prescription: pick the file, the rate column and the unit.",
    ),
    verify=("The map draws with a sensible rate legend.",),
    cautions=(_NO_ACCENTS, _EJECT),
    common_errors=(
        "Missing .prj.",
        "Rx folder nested inside another folder.",
    ),
    confidence=Confidence.VERIFIED,
    sources=("John Deere G5 and Generation 4 compatibility chart, StellarSupport",),
)

_add(
    monitor_key="john_deere.g5",
    objective="import_guidance",
    transport=Transport.CLOUD,
    file_format="Guidance line published in Operations Center",
    media_path="",
    filesystem="n/a — wireless",
    minutes=10,
    prerequisites=("Machine connected via JDLink and visible in Operations Center.",),
    steps=(
        "Upload or draw the guidance line in Operations Center and attach it to "
        "the field.",
        "Use Send to Machine and select the machine.",
        "In the cab, accept the incoming transfer.",
        "Work Setup > Guidance: select the track.",
    ),
    verify=("The track appears under the correct field in the guidance list.",),
    cautions=(
        "This is the easiest route into a Deere display by a wide margin. If "
        "the machine has JDLink, use it instead of a USB stick.",
    ),
    confidence=Confidence.VERIFIED,
    sources=("John Deere Operations Center guidance line documentation",),
)


# =========================================================================== #
#  CNH -- Case IH, New Holland                                                #
# =========================================================================== #

_add(
    monitor_key="case_ih.afs_pro_700",
    objective="import_prescription",
    transport=Transport.USB,
    version_key=("pro700_28", "pro700_29"),
    file_format="Complete shapefile, files loose at the drive root",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="Drive root — the display browses the stick itself",
    minutes=15,
    steps=(
        _FAT32,
        _SHP_SET,
        "Leave the files LOOSE at the drive root, not inside a folder.",
        "Plug the stick into the display's USB port.",
        "Go to Toolbox > Data Management.",
        "Choose the shapefile import option.",
        "Select the Grower, Farm and Field the prescription belongs to.",
        "Select the file, then choose the rate column and the unit.",
        "Confirm and wait for the import to finish.",
    ),
    verify=("The prescription draws on the run screen over the right field.",),
    cautions=(
        "Case IH ships a branded USB stick (part 84398840). Any properly "
        "formatted FAT32 stick works, but if one misbehaves that is the "
        "known-good one.",
        _EJECT,
    ),
    common_errors=(
        "Copying only the .shp file.",
        "Leaving the files inside a folder.",
    ),
    confidence=Confidence.VERIFIED,
    sources=("Case IH AFS Pro 700 shapefile import guide",),
)

_add(
    monitor_key="case_ih.afs_pro_700",
    objective="import_prescription",
    transport=Transport.USB,
    version_key="pro700_30",
    file_format="Complete shapefile, files loose at the drive root",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="Drive root",
    minutes=15,
    steps=(
        _FAT32,
        _SHP_SET,
        "Leave the files LOOSE at the drive root.",
        "Plug the stick into the display's USB port.",
        "On this software line the import lives under Toolbox > Swath / Data, "
        "rather than Data Management. If you do not see it, check both.",
        "Choose the shapefile import.",
        "Select Grower, Farm and Field.",
        "Select the file, the rate column and the unit.",
    ),
    verify=("The prescription draws over the right field.",),
    cautions=(
        "Menu wording moved between the 28.x and 30.x software lines. The file "
        "itself is identical — only the path through the menus changed.",
    ),
    common_errors=("Following 28.x instructions and concluding the file is bad.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("Case IH AFS Pro 700 software operating guide",),
)

_add(
    monitor_key="case_ih.afs_pro_700",
    objective="import_guidance",
    transport=Transport.USB,
    file_format="Shapefile lines — the display calls this a Multiswath",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="Drive root",
    minutes=15,
    steps=(
        _FAT32,
        _SHP_SET,
        "Leave the four files loose at the drive root.",
        "Plug the stick in.",
        "Go to Toolbox > Swath.",
        "Choose the shapefile / Multiswath import.",
        "Select the Grower, Farm and Field.",
        "Select the file and import.",
        "On the run screen, pick the swath before engaging the steering.",
    ),
    verify=(
        "The swath draws where you expect on the run screen.",
        "Drive one pass with steering off to confirm the machine tracks it.",
    ),
    cautions=(
        "This display calls an AB line a Swath, and a set of imported lines a "
        "Multiswath. Look for those words, not 'guidance line'.",
    ),
    common_errors=("Copying only the .shp file.",),
    confidence=Confidence.VERIFIED,
    sources=("Case IH AFS Pro 700 shapefile import guide",),
)

_add(
    monitor_key="case_ih.afs_pro_700",
    objective="export_work_data",
    transport=Transport.USB,
    file_format="Display data package written by the AFS software",
    media_path="Drive root — the display creates its own folder tree",
    minutes=15,
    prerequisites=("Close the current task so the last records are written.",),
    steps=(
        _FAT32,
        "Close or pause the running task.",
        "Plug the stick into the display.",
        "Toolbox > Data Management > Export.",
        "Select the Grower / Farm / Field data you want.",
        "Confirm and wait for the transfer to complete.",
        _EJECT,
        "At the office, import the folder into AFS Software or your FMIS.",
    ),
    verify=("The folder on the stick is not empty and carries today's date.",),
    cautions=("Use one stick per machine to avoid overwriting folder trees.",),
    common_errors=("Removing the stick before the transfer finishes.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("Case IH AFS Pro 700 software operating guide",),
)

_add(
    monitor_key="case_ih.afs_pro_1200",
    objective="import_guidance",
    transport=Transport.USB,
    file_format="ISOXML task data (ISO 11783-10)",
    extensions=(".xml",),
    media_path="TASKDATA\\  — folder named exactly that, at the drive ROOT",
    minutes=10,
    steps=(
        _FAT32,
        "Unzip the download at the ROOT of the stick so a folder named exactly "
        "TASKDATA appears, containing TASKDATA.XML.",
        "Plug the stick into the display.",
        "Open the data management / import screen.",
        "Run the ISOXML import and select the task data on the stick.",
        "Confirm the field and its guidance lines appear.",
        "On the run screen, select the line.",
    ),
    verify=("The field and its reference lines are listed after the import.",),
    cautions=(
        "The folder must be named TASKDATA, capitals, at the root. Nested one "
        "level deeper it will not be found.",
        "CNH publishes its own ADAPT plugin for this format, so ISOXML is a "
        "well-supported route here rather than a hopeful one.",
    ),
    common_errors=(
        "Leaving the download zipped on the stick.",
        "A TASKDATA folder inside another TASKDATA folder after unzipping.",
        "Renaming TASKDATA.XML — the name is fixed by the standard.",
    ),
    confidence=Confidence.VERIFIED,
    sources=(
        "CNH developer portal, ISOXML ADAPT plugin guide",
        "Case IH AFS Pro 1200 software operating manual",
    ),
)

_add(
    monitor_key="case_ih.afs_pro_1200",
    objective="import_prescription",
    transport=Transport.USB,
    file_format="ISOXML task data, or a complete shapefile",
    extensions=(".xml", ".shp", ".shx", ".dbf", ".prj"),
    media_path="TASKDATA\\ at the drive ROOT (ISOXML), or the root (shapefile)",
    minutes=10,
    steps=(
        _FAT32,
        "For ISOXML: unzip at the root so TASKDATA\\TASKDATA.XML exists.",
        "For a shapefile: put all four parts loose at the root.",
        "Plug the stick in and open the data management screen.",
        "Run the import and pick the file.",
        "Attach the prescription to the field, then choose the rate column "
        "and unit.",
    ),
    verify=("The rate map draws over the right field with sensible values.",),
    cautions=(_NO_ACCENTS,),
    common_errors=("Mixing an ISOXML TASKDATA folder and loose shapefiles on one stick.",),
    confidence=Confidence.VERIFIED,
    sources=("CNH developer portal, ISOXML ADAPT plugin guide",),
)

_add(
    monitor_key="case_ih.afs_pro_1200",
    objective="export_work_data",
    transport=Transport.USB,
    file_format="ISOXML task data written by the display",
    extensions=(".xml", ".bin"),
    media_path="TASKDATA\\ — created by the display on the stick",
    minutes=15,
    prerequisites=("Close the running task first.",),
    steps=(
        _FAT32,
        "Close the running task.",
        "Plug the stick into the display.",
        "Open data management and choose Export.",
        "Select the tasks or the whole task data set.",
        "Wait for completion, then eject from the menu.",
        "At the office, read the TASKDATA folder with any ISOXML-capable FMIS.",
    ),
    verify=(
        "TASKDATA.XML exists on the stick and there are .bin time-log files "
        "beside it — those hold the recorded data.",
    ),
    cautions=(
        "The .bin files beside TASKDATA.XML are the actual logged data. Copy "
        "the whole folder, not just the XML.",
    ),
    common_errors=("Copying only TASKDATA.XML and losing every logged value.",),
    confidence=Confidence.VERIFIED,
    sources=("CNH developer portal, ISOXML ADAPT plugin guide",),
)

_add(
    monitor_key="case_ih.afs_pro_1200",
    objective="export_work_data",
    transport=Transport.CLOUD,
    file_format="Automatic sync to AFS Connect",
    media_path="",
    filesystem="n/a — wireless",
    minutes=5,
    prerequisites=("An AFS Connect subscription and a connected modem.",),
    steps=(
        "Confirm the machine shows as connected in the AFS Connect portal.",
        "Confirm data sharing is enabled on the display.",
        "Work data uploads automatically as tasks are completed.",
        "In the portal, open the farm and confirm the task has arrived.",
    ),
    verify=("The task appears in AFS Connect with the expected area.",),
    cautions=("Keep taking an occasional USB export as a backup.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("Case IH AFS Connect documentation",),
)

_add(
    monitor_key="new_holland.intelliview_iv",
    objective="import_guidance",
    transport=Transport.USB,
    file_format="Shapefile lines — the display calls this a Multiswath",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="Drive root",
    minutes=15,
    steps=(
        _FAT32,
        _SHP_SET,
        "Leave the four files loose at the drive root.",
        "Plug the stick in.",
        "Toolbox > Swath > import from USB.",
        "Select Grower, Farm and Field, then the file.",
        "Pick the swath on the run screen.",
    ),
    verify=("The swath draws where you expect.",),
    cautions=(
        "IntelliView IV and the Case IH AFS Pro 700 are the same display in "
        "different paint. Anything that imports on one imports on the other.",
    ),
    common_errors=("Copying only the .shp file.",),
    confidence=Confidence.VERIFIED,
    sources=("Case IH / New Holland Voyager display documentation",),
)

_add(
    monitor_key="new_holland.intelliview_iv",
    objective="import_prescription",
    transport=Transport.USB,
    file_format="Complete shapefile, or ISOXML / CN1 on later software",
    extensions=(".shp", ".shx", ".dbf", ".prj", ".xml"),
    media_path="Drive root",
    minutes=15,
    steps=(
        _FAT32,
        _SHP_SET,
        "Plug the stick in.",
        "Toolbox > Data Management > Import.",
        "Select Grower, Farm and Field.",
        "Select the prescription, then the rate column and unit.",
    ),
    verify=("The rate map draws over the right field.",),
    cautions=("Later IntelliView IV software also accepts ISOXML and CN1 format.",),
    common_errors=("Rate column stored as text.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("New Holland IntelliView IV documentation",),
)

_add(
    monitor_key="new_holland.intelliview_12",
    objective="import_guidance",
    transport=Transport.USB,
    file_format="ISOXML task data (ISO 11783-10)",
    extensions=(".xml",),
    media_path="TASKDATA\\ at the drive ROOT",
    minutes=10,
    steps=(
        _FAT32,
        "Unzip at the root so a TASKDATA folder appears with TASKDATA.XML inside.",
        "Plug the stick in and open data management.",
        "Run the ISOXML import.",
        "Select the field, then pick the swath on the run screen.",
    ),
    verify=("The field and its lines are listed after the import.",),
    cautions=(
        "IntelliView 12 and AFS Pro 1200 are the same display; both read and "
        "write ISO 11783-10.",
    ),
    common_errors=("Leaving the file zipped.", "A nested TASKDATA folder."),
    confidence=Confidence.VERIFIED,
    sources=("CNH developer portal, ISOXML ADAPT plugin guide",),
)

_add(
    monitor_key="new_holland.intelliview_12",
    objective="export_work_data",
    transport=Transport.USB,
    file_format="ISOXML task data written by the display",
    extensions=(".xml", ".bin"),
    media_path="TASKDATA\\ — created by the display",
    minutes=15,
    steps=(
        _FAT32,
        "Close the running task.",
        "Plug the stick in, open data management, choose Export.",
        "Select the task data and confirm.",
        "Wait for completion and eject from the menu.",
    ),
    verify=("TASKDATA.XML plus .bin log files are on the stick.",),
    cautions=("Copy the whole TASKDATA folder — the .bin files hold the data.",),
    confidence=Confidence.VERIFIED,
    sources=("New Holland IntelliView 12 operating system guide",),
)


# =========================================================================== #
#  TRIMBLE                                                                    #
# =========================================================================== #

_add(
    monitor_key="trimble.precision_iq",
    objective="import_prescription",
    transport=Transport.USB,
    file_format="Complete shapefile, files loose inside the Prescriptions folder",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="AgData\\Prescriptions\\  — at the drive root",
    minutes=10,
    steps=(
        _FAT32,
        "At the root of the stick create a folder named AgData.",
        "Inside AgData create a folder named Prescriptions.",
        "Put the four shapefile parts LOOSE inside Prescriptions — not in a "
        "further subfolder.",
        "Plug the stick into the display.",
        "Open Data Transfer.",
        "Select the USB and import the prescription.",
        "Attach it to the field and choose the rate column and unit.",
    ),
    verify=("The rate map draws over the right field.",),
    cautions=(
        "Prescriptions genuinely are loose shapefiles in AgData\\Prescriptions. "
        "Guidance lines are NOT — those go through Trimble Ag Software.",
        _NO_ACCENTS,
    ),
    common_errors=(
        "Putting the shapefile in AgData directly instead of "
        "AgData\\Prescriptions.",
        "Nesting the files one folder deeper.",
    ),
    confidence=Confidence.VERIFIED,
    sources=("Trimble Precision-IQ data management documentation",),
)

_add(
    monitor_key="trimble.precision_iq",
    objective="import_guidance",
    transport=Transport.DESKTOP,
    file_format="Shapefile into Trimble Ag Software, which writes the display file",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="AgData\\ — written by Trimble Ag Software, do not hand-build it",
    minutes=30,
    prerequisites=(
        "Trimble's own .agdata container is AES encrypted and cloud-keyed. No "
        "third party can write one. This route is not a workaround; it is the "
        "supported path.",
    ),
    steps=(
        "Import the shapefile into Trimble Ag Software, desktop or web.",
        "Attach it to the matching client / farm / field as a guidance line.",
        "If the machine has connectivity, sync over the air and stop here.",
        "Otherwise export from Trimble Ag Software onto a USB stick — it "
        "writes the AgData folder for you.",
        "Plug the stick into the display.",
        "Open Data Transfer, select the USB, and import the field.",
        "Select the line on the run screen.",
    ),
    verify=("The line appears under the correct field in Precision-IQ.",),
    cautions=(
        "Do not try to hand-build an AgData folder. The display validates it "
        "and will reject it.",
    ),
    common_errors=("Expecting a loose shapefile to import as a guidance line.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("Trimble Ag Software desktop release notes",),
)

_add(
    monitor_key="trimble.precision_iq",
    objective="export_work_data",
    transport=Transport.USB,
    file_format="AgData package written by the display (encrypted container)",
    media_path="AgData\\ — created by the display",
    minutes=15,
    steps=(
        _FAT32,
        "Close the running task.",
        "Plug the stick into the display.",
        "Open Data Transfer.",
        "Choose to export data to the USB.",
        "Select the fields or the whole data set.",
        "Wait for completion and eject.",
        "At the office, import the AgData folder into Trimble Ag Software.",
    ),
    verify=("Trimble Ag Software lists the job after import.",),
    cautions=(
        "The exported .agdata is encrypted. It can only be opened by Trimble "
        "Ag Software or the Trimble cloud — no third-party tool will read it.",
    ),
    common_errors=(
        "Expecting to open the export in QGIS or Excel. Export from Trimble Ag "
        "Software to shapefile first if you need that.",
    ),
    confidence=Confidence.VERIFIED,
    sources=("Trimble Precision-IQ data management documentation",),
)

_add(
    monitor_key="trimble.fmx",
    objective="import_prescription",
    transport=Transport.USB,
    file_format="Complete shapefile in the AgGPS structure",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="AgGPS\\Prescriptions\\  — note AgGPS, not AgData",
    minutes=15,
    steps=(
        _FAT32,
        "Create AgGPS\\Prescriptions at the root of the stick.",
        "Put the four shapefile parts loose inside Prescriptions.",
        "Plug the stick into the display.",
        "Data > USB > read from the stick.",
        "Attach the prescription to the field and set the rate column.",
    ),
    verify=("The rate map draws over the right field.",),
    cautions=(
        "This generation uses AgGPS, the newer GFX/TMX uses AgData. Files from "
        "one will not drop straight into the other.",
    ),
    common_errors=("Using an AgData folder on an FmX.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("Trimble legacy display data management documentation",),
)


# =========================================================================== #
#  AG LEADER                                                                  #
# =========================================================================== #

_add(
    monitor_key="ag_leader.incommand",
    objective="import_prescription",
    transport=Transport.USB,
    version_key=("ic_1_3", "ic_4_9", "ic_10"),
    file_format=".agsetup exported from SMS, or a complete shapefile",
    extensions=(".agsetup", ".shp", ".shx", ".dbf", ".prj"),
    media_path="Drive root",
    minutes=15,
    steps=(
        _FAT32,
        "Put the .agsetup file, or the four shapefile parts, at the drive root.",
        "Plug the stick into the display.",
        "Tap the status indicator in the top right corner.",
        "Choose Data Transfer from the drop-down.",
        "Tap Import Setup and find the file on the stick.",
        "Confirm the import.",
        "Attach the prescription to the field and choose the rate column.",
    ),
    verify=("The rate map draws over the right field.",),
    cautions=(
        ".agsetup files are forward compatible but not backward. A file written "
        "by newer software may not open on an older display.",
    ),
    common_errors=("Copying only the .shp file when importing a shapefile.",),
    confidence=Confidence.VERIFIED,
    sources=(
        "Ag Leader support portal, AgSetup file supported uses",
        "Ag Leader InCommand display user guide",
    ),
)

_add(
    monitor_key="ag_leader.incommand",
    objective="import_guidance",
    transport=Transport.DESKTOP,
    file_format="Shapefile into SMS, which exports the .agsetup the display reads",
    extensions=(".agsetup",),
    media_path="Drive root",
    minutes=30,
    prerequisites=(
        "The .agsetup container is Ag Leader's own and is not publicly "
        "documented, so it cannot be written directly by third-party software.",
    ),
    steps=(
        "Import the shapefile into SMS Software, Basic or Advanced.",
        "Attach it to the field as a guidance pattern.",
        "Export an .agsetup file from SMS to a USB stick, or push it through "
        "AgFiniti.",
        "Plug the stick into the display.",
        "Tap the status indicator, top right.",
        "Choose Data Transfer, then Import Setup.",
        "Select the .agsetup and confirm.",
        "Select the pattern on the run screen.",
    ),
    verify=("The pattern appears in the guidance list for that field.",),
    cautions=(
        "This display calls an AB line a Pattern. Look for Pattern, A+ heading, "
        "Adaptive Curve or SmartPath.",
    ),
    common_errors=("Expecting a loose shapefile to import as a guidance pattern.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("Ag Leader support portal, AgSetup file supported uses",),
)

_add(
    monitor_key="ag_leader.incommand",
    objective="export_work_data",
    transport=Transport.USB,
    file_format=".agdata — the logged operation data",
    extensions=(".agdata",),
    media_path="Drive root",
    minutes=15,
    prerequisites=("End the operation so the last records are written.",),
    steps=(
        _FAT32,
        "End the running operation.",
        "Plug the stick into the display.",
        "Tap the status indicator, top right.",
        "Choose Data Transfer.",
        "Tap Export and choose the logged data.",
        "Wait for completion and eject.",
        "At the office, import the .agdata into SMS.",
    ),
    verify=("SMS lists the operation with the expected area after import.",),
    cautions=(
        ".agsetup carries setup — fields, boundaries, patterns. .agdata carries "
        "what the machine did. They are different files and you usually want both.",
    ),
    common_errors=("Exporting only setup and losing the season's records.",),
    confidence=Confidence.VERIFIED,
    sources=("Ag Leader InCommand display user guide",),
)

_add(
    monitor_key="ag_leader.incommand",
    objective="export_guidance",
    transport=Transport.USB,
    file_format=".agsetup — guidance patterns live in setup, not in data",
    extensions=(".agsetup",),
    media_path="Drive root",
    minutes=10,
    steps=(
        _FAT32,
        "Plug the stick into the display.",
        "Tap the status indicator, top right, then Data Transfer.",
        "Choose Export Setup (not Export Data).",
        "Select the fields whose patterns you want.",
        "Wait for completion and eject.",
        "Open the .agsetup in SMS to view or convert the patterns.",
    ),
    verify=("SMS lists the patterns under the right fields.",),
    cautions=("Guidance patterns are setup data. Exporting only .agdata misses them.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("Ag Leader support portal, AgSetup file supported uses",),
)


# =========================================================================== #
#  RAVEN                                                                      #
# =========================================================================== #

_add(
    monitor_key="raven.viper4",
    objective="import_guidance",
    transport=Transport.USB,
    file_format="Guidance line files inside the GFF folder tree",
    extensions=(".ab",),
    media_path="Raven\\GFF\\<Grower>\\<Farm>\\<Field>\\abLines\\",
    minutes=15,
    prerequisites=(
        "The Grower / Farm / Field folder names should match what is already on "
        "the display, or the lines land under a newly created field.",
    ),
    steps=(
        _FAT32,
        "Build the folder tree on the stick: "
        "Raven\\GFF\\<Grower>\\<Farm>\\<Field>\\abLines",
        "Put the line files in the abLines folder.",
        "Plug the stick into the display.",
        "Open the USB manager / file manager.",
        "Select Guidance Lines from the file type drop-down.",
        "Touch Next, bottom right.",
        "Browse to the abLines folder.",
        "Tick the lines you want, or use Select All, and import.",
    ),
    verify=("The imported lines appear in the guidance list for that field.",),
    cautions=(
        "The folder tree is documented in Raven's manual; the internal layout "
        "of a .ab file is not something we have been able to confirm. If the "
        "import lists nothing, use a shapefile instead and tell us.",
    ),
    common_errors=(
        "Grower / farm / field names that do not match the display, creating a "
        "duplicate field.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("Raven Viper installation and operator's manual, import guidance lines",),
)

_add(
    monitor_key="raven.viper4",
    objective="export_work_data",
    transport=Transport.USB,
    file_format="Field operation files in the GFF tree",
    media_path="Raven\\GFF\\<Grower>\\<Farm>\\<Field>\\",
    minutes=15,
    steps=(
        _FAT32,
        "Plug the stick into the display.",
        "Open the USB manager.",
        "Choose to export field operation files.",
        "Select the grower, farm and field.",
        "Confirm and wait for the transfer.",
        "At the office, read the GFF tree, or upload through Slingshot.",
    ),
    verify=("The Raven\\GFF tree on the stick contains the field folder.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("Raven Viper installation and operator's manual",),
)


# =========================================================================== #
#  ISOBUS terminals -- one procedure shape covers the family                  #
# =========================================================================== #

_ISOXML_IMPORT_STEPS = (
    _FAT32,
    "Unzip the download at the ROOT of the stick so a folder named exactly "
    "TASKDATA sits at the top level, containing TASKDATA.XML.",
    "Plug the stick into the terminal.",
    "Open the ISOBUS task controller / data import screen.",
    "Run the ISOXML import.",
    "Confirm the field appears with its reference lines.",
    "Select the line you want on the run screen.",
)

_ISOXML_ERRORS = (
    "Leaving the file zipped on the stick.",
    "A TASKDATA folder nested inside another folder.",
    "Renaming TASKDATA.XML — the name is fixed by the standard.",
)


def _isoxml_pair(monitor_key: str, sources: tuple[str, ...], *, version_key=ANY_VERSION,
                 vocabulary: str = "") -> None:
    """Add the import and export ISOXML procedures for one ISOBUS terminal.

    The ISOBUS family genuinely does behave the same way, so writing these out
    by hand twenty times would be twenty chances to introduce a difference that
    is not real.
    """
    note = (
        (f"This terminal calls an AB line a {vocabulary}.",) if vocabulary else ()
    )
    _add(
        monitor_key=monitor_key,
        objective="import_guidance",
        transport=Transport.USB,
        version_key=version_key,
        file_format="ISOXML task data (ISO 11783-10)",
        extensions=(".xml",),
        media_path="TASKDATA\\ at the drive ROOT",
        minutes=10,
        steps=_ISOXML_IMPORT_STEPS,
        verify=("The field and its reference lines are listed after the import.",),
        cautions=note
        + (
            "Any terminal advertising TC-BAS should read this file. If yours is "
            "not listed by name, this procedure still applies.",
        ),
        common_errors=_ISOXML_ERRORS,
        confidence=Confidence.VERIFIED,
        sources=sources,
    )
    _add(
        monitor_key=monitor_key,
        objective="export_work_data",
        transport=Transport.USB,
        version_key=version_key,
        file_format="ISOXML task data written by the terminal",
        extensions=(".xml", ".bin"),
        media_path="TASKDATA\\ — created by the terminal on the stick",
        minutes=15,
        prerequisites=("Close the running task so the last records are written.",),
        steps=(
            _FAT32,
            "Close the running task.",
            "Plug the stick into the terminal.",
            "Open the task controller data screen and choose the export or "
            "synchronise option.",
            "Wait for the write to finish.",
            _EJECT,
            "At the office, read the TASKDATA folder with any ISOXML-capable FMIS.",
        ),
        verify=(
            "TASKDATA.XML exists on the stick with .bin time-log files beside it.",
        ),
        cautions=(
            "The .bin files beside TASKDATA.XML hold the recorded values. Copy "
            "the whole folder.",
        ),
        common_errors=("Copying only TASKDATA.XML and losing every logged value.",),
        confidence=Confidence.VERIFIED,
        sources=sources,
    )


_isoxml_pair(
    "claas.cemis_1200",
    ("CLAAS GPS PILOT CEMIS 1200 documentation", "CLAAS CEMIS 1200 ISOXML tutorials"),
    vocabulary="Reference track",
)
_isoxml_pair("claas.s10", ("CLAAS S10 task import documentation",),
             vocabulary="Reference track")
_isoxml_pair(
    "agco.fendt_one",
    ("Fendt Field Data Converter documentation", "Fendt VarioDoc / Task Doc"),
    vocabulary="Track, under VarioGuide",
)
_isoxml_pair("agco.valtra_smarttouch", ("AGCO Field Data Converter documentation",),
             vocabulary="Guidance line, under Valtra Guide")
_isoxml_pair("agco.mf_datatronic", ("AGCO Field Data Converter documentation",),
             vocabulary="Guidance line, under MF Guide")
_isoxml_pair("topcon.x_family",
             ("Topcon X family Horizon operator manual", "Topcon Horizon OS datasheet"),
             vocabulary="Guideline")
_isoxml_pair("kverneland.isomatch", ("Kverneland IsoMatch terminal documentation",),
             vocabulary="Guidance line")
_isoxml_pair("generic.isobus", ("ISO 11783-10",), vocabulary="Guidance pattern")

_add(
    monitor_key="claas.cemis_1200",
    objective="import_prescription",
    transport=Transport.USB,
    version_key=("cemis_fp2",),
    file_format="ISOXML task data, or a complete shapefile on FP2 and newer",
    extensions=(".xml", ".shp", ".shx", ".dbf", ".prj"),
    media_path="TASKDATA\\ at the root (ISOXML), or the root (shapefile)",
    minutes=10,
    steps=(
        _FAT32,
        "For ISOXML: unzip at the root so TASKDATA\\TASKDATA.XML exists.",
        "For a shapefile: put the four parts at the root. Direct shapefile "
        "import arrived with the FP2 software line.",
        "Plug the stick in and open the import screen.",
        "Select the file and attach it to the field.",
        "Choose the rate column and unit.",
    ),
    verify=("The rate map draws over the right field.",),
    cautions=(
        "On FP1 software, use the ISOXML route — direct shapefile import was "
        "added later.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("CLAAS CEMIS 1200 software update documentation",),
)

_add(
    monitor_key="claas.cemis_1200",
    objective="import_prescription",
    transport=Transport.USB,
    version_key=("cemis_fp1",),
    file_format="ISOXML task data — FP1 software has no direct shapefile import",
    extensions=(".xml",),
    media_path="TASKDATA\\ at the drive ROOT",
    minutes=15,
    prerequisites=(
        "Direct shapefile import arrived with the FP2 software line. On FP1 the "
        "prescription has to be converted to ISOXML first, in your FMIS or in "
        "any ISOXML converter.",
    ),
    steps=(
        _FAT32,
        "Convert the prescription to ISOXML in your farm management software.",
        "Unzip at the ROOT of the stick so a TASKDATA folder appears with "
        "TASKDATA.XML inside.",
        "Plug the stick into the terminal.",
        "Open the ISOBUS task controller and run the ISOXML import.",
        "Select the task and confirm the rate map is attached to the right field.",
    ),
    verify=("The rate map draws over the right field before you start.",),
    cautions=(
        "If you have been handed a bare shapefile and the terminal will not see "
        "it, this is why — check whether the machine is on FP1 or FP2.",
    ),
    common_errors=_ISOXML_ERRORS,
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("CLAAS CEMIS 1200 software update documentation",),
)

_add(
    monitor_key="agco.fendt_one",
    objective="import_guidance",
    transport=Transport.DESKTOP,
    version_key=("vario_terminal", "fendt_one"),
    file_format="ISOXML 2.0-4.3, shapefile in WGS84, or AGCO KML",
    extensions=(".xml", ".shp", ".kml"),
    media_path="TASKDATA\\ at the drive ROOT, after conversion",
    minutes=20,
    steps=(
        "Open the AGCO Field Data Converter on a PC.",
        "Load your file — it accepts ISOXML 2.0 through 4.3, shapefile in "
        "WGS84, and AGCO KML, and handles A-B lines and curves.",
        "Convert to the format the terminal expects and write it to the stick.",
        "Plug the stick into the terminal and import from the data screen.",
        "Select the field, then pick the track under VarioGuide.",
    ),
    verify=("The track is listed under the right field in VarioGuide.",),
    cautions=(
        "Some Fendt workflows expect the archive named TASKDATA.zip. If the "
        "terminal will not see the folder, try importing the zip as-is.",
    ),
    confidence=Confidence.VERIFIED,
    sources=("Fendt Field Data Converter documentation",),
)

_add(
    monitor_key="mueller.track_leader",
    objective="import_guidance",
    transport=Transport.USB,
    version_key=("tl_7", "tl_8"),
    file_format="ISOXML task data, or a shapefile in an SHP folder",
    extensions=(".xml", ".shp", ".shx", ".dbf", ".prj"),
    media_path="TASKDATA\\ at the root (ISOXML)  |  SHP\\ at the root (shapefile)",
    minutes=10,
    steps=(
        _FAT32,
        "For ISOXML: unzip at the root so a TASKDATA folder appears.",
        "For a shapefile: create a folder named SHP at the root and put the "
        "four parts inside it. That is where TRACK-Leader looks.",
        "Plug the stick into the terminal and run the import.",
        "Select the line on the run screen.",
    ),
    verify=("The line appears in the guidance list.",),
    cautions=(
        "TRACK-Leader's own store is an ngstore database, and ngstore folders "
        "only move between terminals of the same type. Do not hand-copy one; "
        "import through ISOXML or shapefile instead.",
        "From v8 the terminal writes shp and kml into an SHP folder when you "
        "synchronise to USB — a good way to see the naming it expects.",
    ),
    common_errors=_ISOXML_ERRORS,
    confidence=Confidence.VERIFIED,
    sources=("Müller-Elektronik TRACK-Leader operating instructions, v8",),
)

_add(
    monitor_key="mueller.track_leader",
    objective="export_work_data",
    transport=Transport.USB,
    file_format="ngstore database, plus SHP and KML on v8 and newer",
    media_path="ngstore\\ and SHP\\ at the drive root",
    minutes=15,
    steps=(
        _FAT32,
        "Plug the stick into the terminal.",
        "Open TRACK-Leader and choose to save or synchronise to USB.",
        "On v8 and newer the terminal also writes shp and kml into an SHP folder.",
        "Wait for completion and eject.",
        "At the office, read the SHP folder — the ngstore database is only "
        "readable by another terminal of the same type.",
    ),
    verify=("The SHP folder on the stick contains readable shapefiles.",),
    cautions=(
        "Do not rely on the ngstore folder for archiving. Use the SHP or ISOXML "
        "output, which anything can read.",
    ),
    confidence=Confidence.VERIFIED,
    sources=("Müller-Elektronik TRACK-Leader operating instructions, v8",),
)


# =========================================================================== #
#  Planter and sprayer specialists                                            #
# =========================================================================== #

_add(
    monitor_key="precision_planting.2020",
    objective="import_prescription",
    transport=Transport.USB,
    file_format="Complete shapefile, or a .2020 prescription file",
    extensions=(".shp", ".shx", ".dbf", ".prj", ".2020"),
    media_path="Drive root, or a folder named exactly SendTo2020",
    minutes=10,
    steps=(
        _FAT32,
        _SHP_SET,
        "Put the files either LOOSE at the drive root, or inside a folder named "
        "exactly SendTo2020. Nothing deeper than that.",
        "Plug the stick into the USB port on the upper left of the display.",
        "From the Home screen press Setup, bottom right.",
        "Press Data, bottom right.",
        "Press Import, top right, then Prescriptions.",
        "Select the file and assign it to the right field.",
    ),
    verify=("The prescription draws on the map before you start planting.",),
    cautions=(
        "The 20|20 is fussy about folder depth. Files buried in nested folders "
        "simply will not be listed.",
    ),
    common_errors=(
        "Burying the files two or three folders deep.",
        "Copying only the .shp file.",
    ),
    confidence=Confidence.VERIFIED,
    sources=("Precision Planting 20|20 import documentation and help centre",),
)

_add(
    monitor_key="precision_planting.2020",
    objective="import_boundary",
    transport=Transport.USB,
    file_format="Complete shapefile, polygon geometry",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="Drive root, or SendTo2020\\",
    minutes=10,
    steps=(
        _FAT32,
        "Put the four shapefile parts at the drive root or in SendTo2020.",
        "Plug the stick into the display.",
        "Home > Setup > Data > Import.",
        "Choose Boundaries.",
        "Assign each boundary to the correct field.",
    ),
    verify=("The boundary draws around the field on the map page.",),
    common_errors=("Line geometry instead of polygon.",),
    confidence=Confidence.VERIFIED,
    sources=("Precision Planting 20|20 import documentation",),
)

_add(
    monitor_key="teejet.matrix_pro_gs",
    objective="import_guidance",
    transport=Transport.USB,
    file_format="Job data containing the guideline",
    media_path="Drive root, under the console's job data folder",
    minutes=15,
    steps=(
        _FAT32,
        "Copy the job data onto the stick.",
        "Plug the stick into the console.",
        "Go to Configuration > Data > Job Data > Transfer.",
        "Copy the job in from USB Storage.",
        "Open the job and confirm the guideline is drawn.",
    ),
    verify=("The guideline is drawn when the job opens.",),
    cautions=(
        "The Matrix moves whole jobs rather than bare lines, so the line "
        "arrives attached to a job.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("TeeJet Matrix Pro GS user manual and release notes",),
)

_add(
    monitor_key="teejet.matrix_pro_gs",
    objective="export_work_data",
    transport=Transport.USB,
    file_format="Job data, plus SHP / KML / PDF reports",
    extensions=(".shp", ".kml", ".pdf"),
    media_path="Drive root",
    minutes=10,
    steps=(
        _FAT32,
        "Plug the stick into the console.",
        "Configuration > Data > Job Data > Transfer.",
        "Copy the job out to USB Storage.",
        "For a readable copy, also export the SHP, KML or PDF report.",
    ),
    verify=("The exported files open on a computer.",),
    cautions=(
        "Exporting shp and kml from the console is a good way to see exactly "
        "what naming and structure it expects on the way back in.",
    ),
    confidence=Confidence.VERIFIED,
    sources=("TeeJet Matrix Pro GS user manual",),
)


_add(
    monitor_key="agopengps.aog",
    objective="import_guidance",
    transport=Transport.USB,
    file_format="AgOpenGPS field folder (ABLines.txt, Boundary.txt, Field.txt)",
    extensions=(".txt", ".kml"),
    media_path="The field folder under your AgOpenGPS Fields directory",
    filesystem="any — this is a PC, not an embedded display",
    minutes=5,
    steps=(
        "Copy the field folder into your AgOpenGPS Fields directory, so it "
        "sits alongside your existing fields.",
        "Start AgOpenGPS and open the field.",
        "The lines appear in the line picker.",
        "If they are missing or look rotated, open the Field.kml supplied in "
        "the same folder to check the geometry is right, then re-enter the "
        "line by hand.",
    ),
    verify=("The line picker lists the imported lines and they draw correctly.",),
    cautions=(
        "AgOpenGPS is open source, so its coordinate convention is known: "
        "metres east and north of the origin recorded in Field.txt. The field "
        "ORDER inside ABLines.txt has changed between releases, so treat a "
        "generated file as best effort and keep Field.kml as the check.",
    ),
    common_errors=("Dropping the folder next to the Fields directory rather than inside it.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=("AgOpenGPS field directory layout",),
)

_add(
    monitor_key="agopengps.aog",
    objective="export_work_data",
    transport=Transport.USB,
    file_format="The field folder itself — plain text plus KML",
    extensions=(".txt", ".kml"),
    media_path="AgOpenGPS Fields\\<field name>\\",
    filesystem="any",
    minutes=5,
    steps=(
        "Close the field in AgOpenGPS so everything is written to disk.",
        "Copy the whole field folder out of the Fields directory.",
        "Open Field.kml in Google Earth or QGIS to read the geometry, or read "
        "the .txt files directly — they are plain text.",
    ),
    verify=("Field.kml opens and shows the coverage where you expect.",),
    cautions=(
        "Everything AgOpenGPS records is plain text and readable, which makes "
        "it the easiest system of all to archive and audit.",
    ),
    confidence=Confidence.VERIFIED,
    sources=("AgOpenGPS field directory layout",),
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


# --------------------------------------------------------------------------- #
#  Lookup                                                                      #
# --------------------------------------------------------------------------- #

# Built once at import: procedure lookup is the hottest path in the app, since
# every wizard step re-queries what is still reachable.
_BY_MONITOR: dict[str, list[Procedure]] = {}
for _p in PROCEDURES:
    _BY_MONITOR.setdefault(_p.monitor_key, []).append(_p)


def objective(key: str) -> Objective:
    try:
        return OBJECTIVES[key]
    except KeyError:
        raise KeyError(
            f"unknown objective {key!r}. Known: {', '.join(sorted(OBJECTIVES))}"
        ) from None


def _version_label(monitor_key: str, version_key: str) -> str:
    for version in versions_for(monitor_key):
        if version.key == version_key:
            return version.label
    return version_key


def versions_for(monitor_key: str) -> tuple[MonitorVersion, ...]:
    return MONITOR_VERSIONS.get(monitor_key, ())


def available_objectives(
    monitor_key: str, version_key: str | None = None
) -> list[Objective]:
    """Objectives this display can actually do, in the order people want them.

    Filtered by version so the wizard never offers a job that has no procedure
    behind it -- an empty result page is worse than a shorter menu.
    """
    keys: set[str] = set()
    for procedure in _BY_MONITOR.get(monitor_key, []):
        if _version_matches(procedure, version_key):
            keys.add(procedure.objective)
    return [o for o in OBJECTIVES.values() if o.key in keys]


def available_transports(
    monitor_key: str, objective_key: str, version_key: str | None = None
) -> list[Transport]:
    found: list[Transport] = []
    for procedure in _BY_MONITOR.get(monitor_key, []):
        if procedure.objective != objective_key:
            continue
        if not _version_matches(procedure, version_key):
            continue
        if procedure.transport not in found:
            found.append(procedure.transport)
    return [t for t in Transport if t in found]


def _version_matches(procedure: Procedure, version_key: str | None) -> bool:
    if ANY_VERSION in procedure.version_keys:
        return True
    if version_key in (None, "", ANY_VERSION):
        # No version chosen: a version-specific procedure is still reachable,
        # it just will not be preferred.
        return True
    return version_key in procedure.version_keys


@dataclass
class Resolution:
    """A resolved procedure plus how it was found."""

    procedure: Procedure | None
    matched_version: bool
    """True when a procedure written for exactly this release was found."""

    alternatives: list[Procedure] = dc_field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "found": self.procedure is not None,
            "procedure": self.procedure.to_dict() if self.procedure else None,
            "matched_version": self.matched_version,
            "message": self.message,
            "alternatives": [
                {
                    "objective": p.objective,
                    "objective_label": OBJECTIVES[p.objective].label,
                    "transport": p.transport.value,
                    "transport_label": p.transport.label,
                    "version_key": p.version_key,
                }
                for p in self.alternatives
            ],
        }


def resolve(
    monitor_key: str,
    objective_key: str,
    transport: Transport | str,
    version_key: str | None = None,
) -> Resolution:
    """Find the procedure for one exact question.

    Prefers a procedure written for the chosen release; falls back to the
    version-independent one and *says so*, because "these steps are generic"
    is information the reader needs before they go looking for a menu that may
    have been renamed.
    """
    if isinstance(transport, str):
        transport = Transport(transport)
    if objective_key not in OBJECTIVES:
        raise KeyError(f"unknown objective {objective_key!r}")

    candidates = [
        p
        for p in _BY_MONITOR.get(monitor_key, [])
        if p.objective == objective_key and p.transport == transport
    ]

    exact = [
        p
        for p in candidates
        if version_key and version_key in p.version_keys
        and ANY_VERSION not in p.version_keys
    ]
    if exact:
        return Resolution(
            procedure=exact[0],
            matched_version=True,
            message="These steps were written for the software version you selected.",
        )

    generic = [p for p in candidates if ANY_VERSION in p.version_keys]
    if generic:
        version_specific = [p for p in candidates if ANY_VERSION not in p.version_keys]
        note = (
            "These steps are the same on every software version of this display."
        )
        matched = True
        if version_specific:
            named = sorted(
                {
                    _version_label(monitor_key, key)
                    for p in version_specific
                    for key in p.version_keys
                }
            )
            note = (
                "These are the general steps for this display. Separate "
                "instructions exist for " + ", ".join(named) + " -- if your "
                "release is one of those, go back and pick it."
            )
            matched = False
        return Resolution(procedure=generic[0], matched_version=matched, message=note)

    if candidates:
        # Only version-specific procedures exist, and none covers this release.
        other = candidates[0]
        label = ", ".join(
            _version_label(monitor_key, key) for key in other.version_keys
        )
        return Resolution(
            procedure=other,
            matched_version=False,
            message=(
                f"No procedure is recorded for the version you selected. These "
                f"steps were written for {label} and are the closest we have — "
                f"treat the menu names as a guide rather than exact."
            ),
        )

    alternatives = [
        p
        for p in _BY_MONITOR.get(monitor_key, [])
        if _version_matches(p, version_key)
    ]
    return Resolution(
        procedure=None,
        matched_version=False,
        alternatives=alternatives,
        message=(
            "We have no procedure recorded for that combination yet. The other "
            "jobs listed below are documented for this display."
        ),
    )


def coverage() -> dict:
    """Counts for the docs and for spotting gaps."""
    by_objective: dict[str, int] = {}
    by_transport: dict[str, int] = {}
    by_confidence: dict[str, int] = {}
    for p in PROCEDURES:
        by_objective[p.objective] = by_objective.get(p.objective, 0) + 1
        by_transport[p.transport.value] = by_transport.get(p.transport.value, 0) + 1
        by_confidence[p.confidence.value] = by_confidence.get(p.confidence.value, 0) + 1
    return {
        "total": len(PROCEDURES),
        "monitors": len(_BY_MONITOR),
        "by_objective": by_objective,
        "by_transport": by_transport,
        "by_confidence": by_confidence,
        "version_specific": sum(
            1 for p in PROCEDURES if ANY_VERSION not in p.version_keys
        ),
    }


def iter_procedures() -> Iterable[Procedure]:
    return iter(PROCEDURES)
