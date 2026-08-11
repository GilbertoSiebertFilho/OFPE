"""Machinery for the procedure knowledge base: types, registry, resolver.

The knowledge itself lives in :mod:`abline.procedures.brands`. This module
holds only the vocabulary it is expressed in and the lookup over it, so a
brand module reads as pure fact with no plumbing in the way.

Original overview:

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
    "Resolution",
    "resolve",
    "available_objectives",
    "available_transports",
    "versions_for",
    "objective",
    "coverage",
    "iter_procedures",
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

    platform: str = ""
    """The manufacturer's platform this route goes through, if any.

    "John Deere Operations Center", "AFS Connect", "AgFiniti". Named because a
    cloud route is useless advice without saying *which* portal to log into,
    and because several brands have two (a telematics portal and an agronomy
    one) that do different jobs.
    """

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
            "platform": self.platform,
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
def _mirror(
    source_monitor: str,
    target_monitor: str,
    objectives: Iterable[tuple[str, "Transport"]],
    *,
    extra_cautions: tuple[str, ...] = (),
    extra_sources: tuple[str, ...] = (),
) -> None:
    """Register a rebadged display's procedures by copying another's.

    Several displays in this catalog are the same hardware in different paint:
    the New Holland IntelliView IV and the Case IH AFS Pro 700, the John Deere
    G5 and the Gen 4, the AGCO terminals across Fendt, Valtra and Massey
    Ferguson.

    They are copied rather than aliased so that every answer stays
    self-contained. When one of them eventually diverges -- and they do -- the
    fix is editing one entry, not unpicking a shared one and working out which
    displays the change was supposed to reach.
    """
    wanted = set(objectives)
    found: set[tuple[str, Transport]] = set()
    for procedure in list(PROCEDURES):
        if procedure.monitor_key != source_monitor:
            continue
        key = (procedure.objective, procedure.transport)
        if key not in wanted:
            continue
        found.add(key)
        PROCEDURES.append(
            Procedure(
                **{
                    **procedure.__dict__,
                    "monitor_key": target_monitor,
                    "cautions": procedure.cautions + extra_cautions,
                    "sources": procedure.sources + extra_sources,
                }
            )
        )
    missing = wanted - found
    if missing:
        raise ValueError(
            f"cannot mirror {source_monitor} -> {target_monitor}: no such "
            f"procedure for {sorted((o, t.value) for o, t in missing)}"
        )


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



# --------------------------------------------------------------------------- #
#  Lookup                                                                      #
# --------------------------------------------------------------------------- #

# Procedure lookup is the hottest path in the app -- every wizard step asks
# what is still reachable -- so it runs off an index rather than a scan.
#
# The index is built on first use, not at import, because the brand modules
# that fill PROCEDURES are imported *after* this one. Rebuilding whenever the
# registry has grown means a newly added brand module can never be silently
# missing from the index, which would look exactly like a documentation gap.
_INDEX: dict[str, list[Procedure]] = {}
_INDEXED_COUNT = -1


def _by_monitor() -> dict[str, list[Procedure]]:
    global _INDEXED_COUNT
    if _INDEXED_COUNT != len(PROCEDURES):
        _INDEX.clear()
        for procedure in PROCEDURES:
            _INDEX.setdefault(procedure.monitor_key, []).append(procedure)
        _INDEXED_COUNT = len(PROCEDURES)
    return _INDEX


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
    for procedure in _by_monitor().get(monitor_key, []):
        if _version_matches(procedure, version_key):
            keys.add(procedure.objective)
    return [o for o in OBJECTIVES.values() if o.key in keys]


def available_transports(
    monitor_key: str, objective_key: str, version_key: str | None = None
) -> list[Transport]:
    found: list[Transport] = []
    for procedure in _by_monitor().get(monitor_key, []):
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


def _summarise(procedure: Procedure) -> dict:
    """The short form used for cross-links, without the whole step list."""
    return {
        "objective": procedure.objective,
        "objective_label": OBJECTIVES[procedure.objective].label,
        "direction": OBJECTIVES[procedure.objective].direction.value,
        "transport": procedure.transport.value,
        "transport_label": procedure.transport.label,
        "version_keys": list(procedure.version_keys),
    }


@dataclass
class Resolution:
    """A resolved procedure plus how it was found."""

    procedure: Procedure | None
    matched_version: bool
    """True when a procedure written for exactly this release was found."""

    alternatives: list[Procedure] = dc_field(default_factory=list)
    """Other jobs documented for this display, offered when the asked-for one
    is not. A dead end that points somewhere is not a dead end."""

    related: list[Procedure] = dc_field(default_factory=list)
    """What someone doing this usually needs next.

    Loading a prescription is rarely the whole errand -- the same trip to the
    machine is the moment to pull last week's work data off it. Surfacing that
    saves a second walk to the shed.
    """

    message: str = ""

    def to_dict(self) -> dict:
        return {
            "found": self.procedure is not None,
            "procedure": self.procedure.to_dict() if self.procedure else None,
            "matched_version": self.matched_version,
            "message": self.message,
            "alternatives": [_summarise(p) for p in self.alternatives],
            "related": [_summarise(p) for p in self.related],
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
        for p in _by_monitor().get(monitor_key, [])
        if p.objective == objective_key and p.transport == transport
    ]

    related = _related(monitor_key, objective_key, version_key)

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
            related=related,
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
        return Resolution(
            procedure=generic[0],
            matched_version=matched,
            related=related,
            message=note,
        )

    if candidates:
        # Only version-specific procedures exist, and none covers this release.
        other = candidates[0]
        label = ", ".join(
            _version_label(monitor_key, key) for key in other.version_keys
        )
        return Resolution(
            procedure=other,
            matched_version=False,
            related=related,
            message=(
                f"No procedure is recorded for the version you selected. These "
                f"steps were written for {label} and are the closest we have — "
                f"treat the menu names as a guide rather than exact."
            ),
        )

    alternatives = [
        p
        for p in _by_monitor().get(monitor_key, [])
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


# The order people actually work in: get set up, do the job, take the record
# away. Used to sort the "you might also need" links so they read as a workflow
# rather than as an alphabetical dump.
_RELATED_ORDER = [
    "prepare_media",
    "import_setup",
    "import_boundary",
    "import_guidance",
    "import_prescription",
    "export_work_data",
    "export_guidance",
    "export_boundary",
    "export_backup",
    "software_update",
]


def _related(
    monitor_key: str, objective_key: str, version_key: str | None, limit: int = 4
) -> list[Procedure]:
    """Other jobs on this display worth doing while you are standing there."""
    seen: set[str] = set()
    out: list[Procedure] = []
    for key in _RELATED_ORDER:
        if key == objective_key or key in seen:
            continue
        for procedure in _by_monitor().get(monitor_key, []):
            if procedure.objective != key:
                continue
            if not _version_matches(procedure, version_key):
                continue
            out.append(procedure)
            seen.add(key)
            break
        if len(out) >= limit:
            break
    return out


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
        "monitors": len(_by_monitor()),
        "by_objective": by_objective,
        "by_transport": by_transport,
        "by_confidence": by_confidence,
        "version_specific": sum(
            1 for p in PROCEDURES if ANY_VERSION not in p.version_keys
        ),
    }


def iter_procedures() -> Iterable[Procedure]:
    return iter(PROCEDURES)
