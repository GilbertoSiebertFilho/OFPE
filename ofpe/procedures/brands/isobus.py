"""ISOBUS terminals: CLAAS, AGCO, Topcon, Kverneland, Mueller, generic."""

from __future__ import annotations

from ..families import (
    _cloud_route,
    _ISOXML_ERRORS,
    _ISOXML_IMPORT_STEPS,
    _isoxml_extras,
    _isoxml_pair,
    _terminal_update,
)
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
#  ISOBUS terminals -- one procedure shape covers the family                  #
# =========================================================================== #

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


_CLAAS_SOURCES = ("CLAAS GPS PILOT CEMIS 1200 documentation",
                  "CLAAS CEMIS 1200 ISOXML tutorials")
_AGCO_SOURCES = ("AGCO Field Data Converter documentation",)
_TOPCON_SOURCES = ("Topcon X family Horizon operator manual",)
_KV_SOURCES = ("Kverneland IsoMatch terminal documentation",)
_ME_SOURCES = ("Müller-Elektronik TRACK-Leader operating instructions, v8",)

_isoxml_extras("claas.cemis_1200", _CLAAS_SOURCES, vocabulary="Reference track")
_isoxml_extras("claas.s10", ("CLAAS S10 task import documentation",),
               vocabulary="Reference track")
_isoxml_extras("agco.fendt_one", _AGCO_SOURCES, vocabulary="Track, under VarioGuide")
_isoxml_extras("agco.valtra_smarttouch", _AGCO_SOURCES,
               vocabulary="Guidance line, under Valtra Guide")
_isoxml_extras("agco.mf_datatronic", _AGCO_SOURCES,
               vocabulary="Guidance line, under MF Guide")
_isoxml_extras("topcon.x_family", _TOPCON_SOURCES, vocabulary="Guideline")
_isoxml_extras("kverneland.isomatch", _KV_SOURCES, vocabulary="Guidance line")
_isoxml_extras("generic.isobus", ("ISO 11783-10",), vocabulary="Guidance pattern")

_terminal_update("claas.cemis_1200", "your CLAAS dealer", _CLAAS_SOURCES, dealer=True)
_terminal_update("claas.s10", "your CLAAS dealer",
                 ("CLAAS S10 documentation",), dealer=True)
_terminal_update("agco.fendt_one", "AGCO / your Fendt dealer", _AGCO_SOURCES,
                 dealer=True)
_terminal_update("agco.valtra_smarttouch", "AGCO / your Valtra dealer",
                 _AGCO_SOURCES, dealer=True)
_terminal_update("agco.mf_datatronic", "AGCO / your Massey Ferguson dealer",
                 _AGCO_SOURCES, dealer=True)
_terminal_update("topcon.x_family", "the myTopcon support portal", _TOPCON_SOURCES)
_terminal_update("kverneland.isomatch", "the Kverneland dealer portal", _KV_SOURCES)
_terminal_update("mueller.track_leader", "the Müller-Elektronik service portal",
                 _ME_SOURCES)

_cloud_route(
    "claas.cemis_1200", "CLAAS TELEMATICS / 365FarmNet", _CLAAS_SOURCES,
    caveat="CLAAS splits telematics and agronomy across two platforms; field "
           "data usually travels through 365FarmNet rather than TELEMATICS.",
)
_cloud_route("agco.fendt_one", "Fendt Connect / AGCO Connectivity Center",
             _AGCO_SOURCES)
_cloud_route("agco.valtra_smarttouch", "Valtra Connect / AGCO Connectivity Center",
             _AGCO_SOURCES)
_cloud_route("agco.mf_datatronic", "MF Connect / AGCO Connectivity Center",
             _AGCO_SOURCES)
_cloud_route("topcon.x_family", "Topcon Agriculture Platform (TAP)", _TOPCON_SOURCES)
_cloud_route("kverneland.isomatch", "IsoMatch FarmCentre", _KV_SOURCES)
_cloud_route(
    "mueller.track_leader", "agrirouter", _ME_SOURCES,
    objectives=("import_prescription", "import_guidance", "export_work_data"),
    caveat="agrirouter is a manufacturer-neutral exchange rather than one "
           "brand's portal: it routes files between systems and does not store "
           "your agronomy.",
)
_cloud_route(
    "generic.isobus", "agrirouter", ("ISO 11783-10", "agrirouter documentation"),
    objectives=("import_prescription", "import_guidance", "export_work_data"),
    caveat="If your terminal has no portal of its own, agrirouter is the "
           "vendor-neutral way to move ISOXML without a stick.",
)

_isoxml_extras("mueller.track_leader", _ME_SOURCES, vocabulary="Guidance line")
