"""Planter and sprayer specialists, plus AgOpenGPS."""

from __future__ import annotations

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
        "Plug the stick into the USB port on the left side of the display.",
        "From the Home screen press «Setup», bottom right.",
        "Press «Data», bottom right.",
        "Press «Import», top right.",
        "Press «Prescriptions», top centre.",
        "Choose which system the prescription is for: «Seeding», «Liquid», "
        "«Granular» or «Depth».",
        "A list of the files on the stick comes up. Tap each one you want, then "
        "press «Import».",
        "Now assign each prescription to the field it belongs to. Importing "
        "alone does not attach it to anything.",
    ),
    verify=("The prescription draws on the map before you start planting.",),
    cautions=(
        "The 20|20 is fussy about folder depth. Files buried in nested folders "
        "simply will not be listed.",
    ),
    common_errors=(
        "Burying the files two or three folders deep.",
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
        "From the Home screen press «Setup», then «Data», then «Import».",
        "Choose «Boundaries».",
        "Tap the files you want and press «Import».",
        "Assign each boundary to the correct field.",
    ),
    verify=("The boundary draws around the field on the map page.",),
    common_errors=("The file draws the field as an outline rather than an area. It imports "
        "and then behaves as if there is no boundary at all.",),
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
        "Open «Configuration», then «Data», then «Job Data», then «Transfer».",
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
        "Open «Configuration», then «Data», then «Job Data», then «Transfer».",
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


# --------------------------------------------------------------------------- #
#  The rest of the specialist jobs                                             #
# --------------------------------------------------------------------------- #

from ..families import _cloud_route, _terminal_update  # noqa: E402

_PP_SOURCES = ("Precision Planting 20|20 import documentation and help centre",)
_TJ_SOURCES = ("TeeJet Matrix Pro GS user manual and release notes",)
_AOG_SOURCES = ("AgOpenGPS field directory layout",)

_add(
    monitor_key="precision_planting.2020",
    objective="import_guidance",
    transport=Transport.USB,
    file_format="Complete shapefile, line geometry",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="Drive root, or a folder named exactly SendTo2020",
    minutes=10,
    steps=(
        _FAT32,
        _SHP_SET,
        "Put the files loose at the drive root, or inside SendTo2020. Nothing "
        "deeper.",
        "Plug the stick into the USB port on the upper left of the display.",
        "From the Home screen press «Setup», then «Data», then «Import».",
        "Select the guidance file and assign it to the right field.",
    ),
    verify=("The line draws on the map page before you start planting.",),
    cautions=("The 20|20 will not find files buried in nested folders.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=_PP_SOURCES,
)

_add(
    monitor_key="precision_planting.2020",
    objective="export_work_data",
    transport=Transport.USB,
    file_format="20|20 data export",
    media_path="Drive root",
    minutes=15,
    prerequisites=("Finish the job so the last passes are written.",),
    steps=(
        _FAT32,
        "Plug the stick into the USB port on the upper left.",
        "From the Home screen press «Setup», then «Data», then «Export».",
        "Select the field data to export.",
        "Wait for the transfer to complete before removing the stick.",
        "At the office, read it with your FMIS or upload to Panorama.",
    ),
    verify=("The export appears on the stick with today's date.",),
    cautions=(
        "Planting data is the record you compare every yield map against next "
        "autumn. Pull it off the same day the planter comes out of the field.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=_PP_SOURCES,
)

_add(
    monitor_key="precision_planting.2020",
    objective="export_backup",
    transport=Transport.USB,
    file_format="Full 20|20 data export",
    media_path="Drive root",
    minutes=20,
    steps=(
        _FAT32,
        "From the Home screen press «Setup», then «Data», then «Export».",
        "Select everything rather than one field.",
        "Wait for completion and copy the result somewhere backed up.",
    ),
    verify=("The export contains every field you worked this season.",),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=_PP_SOURCES,
)

_terminal_update("precision_planting.2020", "the Precision Planting dealer portal",
                 _PP_SOURCES)
_cloud_route(
    "precision_planting.2020", "Panorama", _PP_SOURCES,
    objectives=("import_prescription", "export_work_data"),
)

_add(
    monitor_key="teejet.matrix_pro_gs",
    objective="import_prescription",
    transport=Transport.USB,
    file_format="Complete shapefile, polygon geometry with a numeric rate column",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="Drive root",
    minutes=15,
    steps=(
        _FAT32,
        _SHP_SET,
        "Copy the files onto the stick.",
        "Plug the stick into the console.",
        "Open «Configuration», then «Data», then «Job Data», then «Transfer», "
        "and copy the job in.",
        "Open the job and attach the prescription, then set the rate column "
        "and unit.",
    ),
    verify=("The rate map draws over the right field.",),
    cautions=(
        "The Matrix works in whole jobs, so the prescription arrives attached "
        "to a job rather than on its own.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=_TJ_SOURCES,
)

_add(
    monitor_key="teejet.matrix_pro_gs",
    objective="import_boundary",
    transport=Transport.USB,
    file_format="Complete shapefile, polygon geometry",
    extensions=(".shp", ".shx", ".dbf", ".prj"),
    media_path="Drive root",
    minutes=15,
    steps=(
        _FAT32,
        _SHP_SET,
        "Plug the stick into the console.",
        "Open «Configuration», then «Data», then «Job Data», then «Transfer».",
        "Copy the job in from USB Storage and open it.",
        "Confirm the boundary and any no-spray zones are drawn.",
    ),
    verify=("The boundary and no-spray zones draw on the run screen.",),
    cautions=(
        "This console treats no-spray zones as their own geometry. Check both "
        "came across, not just the outer boundary.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=_TJ_SOURCES,
)

_add(
    monitor_key="teejet.matrix_pro_gs",
    objective="export_boundary",
    transport=Transport.USB,
    file_format="SHP and KML exported by the console",
    extensions=(".shp", ".kml"),
    media_path="Drive root",
    minutes=10,
    steps=(
        _FAT32,
        "Plug the stick into the console.",
        "Open «Configuration», then «Data», then «Job Data», then «Transfer».",
        "Export the job, and also export the SHP / KML report.",
        "Open the KML in Google Earth to check it before filing it.",
    ),
    verify=("The exported shapefile or KML opens and looks right.",),
    cautions=(
        "Exporting shp and kml from the console is the quickest way to learn "
        "exactly what naming and structure it expects on the way back in.",
    ),
    confidence=Confidence.VERIFIED,
    sources=_TJ_SOURCES,
)

_terminal_update("teejet.matrix_pro_gs", "the TeeJet support site", _TJ_SOURCES)

_add(
    monitor_key="agopengps.aog",
    objective="import_boundary",
    transport=Transport.USB,
    file_format="Boundary.txt inside the field folder, plus Field.kml to check it",
    extensions=(".txt", ".kml"),
    media_path="The field folder under your AgOpenGPS Fields directory",
    filesystem="any — this is a PC, not an embedded display",
    minutes=5,
    steps=(
        "Copy the field folder into your AgOpenGPS Fields directory.",
        "Start AgOpenGPS and open the field.",
        "Confirm the boundary draws where you expect.",
        "If it looks wrong, open Field.kml in Google Earth to check the "
        "geometry itself before blaming the import.",
    ),
    verify=("The boundary draws correctly and section control respects it.",),
    cautions=(
        "AgOpenGPS works in metres east and north of the origin in Field.txt. "
        "A boundary copied into a field folder with a different origin will "
        "appear in the wrong place — keep the folder intact.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=_AOG_SOURCES,
)

_add(
    monitor_key="agopengps.aog",
    objective="export_boundary",
    transport=Transport.USB,
    file_format="Boundary.txt and Field.kml — plain text either way",
    extensions=(".txt", ".kml"),
    media_path="AgOpenGPS Fields\\<field name>\\",
    filesystem="any",
    minutes=5,
    steps=(
        "Close the field in AgOpenGPS so everything is written to disk.",
        "Copy the field folder out of the Fields directory.",
        "Open Field.kml in Google Earth or QGIS, or read Boundary.txt directly.",
    ),
    verify=("Field.kml opens and the outline is where you expect.",),
    cautions=(
        "Everything AgOpenGPS records is plain text, which makes it the easiest "
        "system in this catalog to archive and audit.",
    ),
    confidence=Confidence.VERIFIED,
    sources=_AOG_SOURCES,
)

_add(
    monitor_key="agopengps.aog",
    objective="export_guidance",
    transport=Transport.USB,
    file_format="ABLines.txt and CurveLines.txt, plus Field.kml",
    extensions=(".txt", ".kml"),
    media_path="AgOpenGPS Fields\\<field name>\\",
    filesystem="any",
    minutes=5,
    steps=(
        "Close the field so the line files are written.",
        "Copy ABLines.txt and CurveLines.txt out of the field folder.",
        "Open Field.kml alongside them to see the geometry.",
    ),
    verify=("The .txt files list the lines you recorded.",),
    cautions=(
        "The field order inside these files has changed between AgOpenGPS "
        "releases. If you send us one written by your own version, we can match "
        "it exactly rather than treating our writer as best effort.",
    ),
    confidence=Confidence.CONFIRM_ON_MACHINE,
    sources=_AOG_SOURCES,
)


from ..families import _point_routes  # noqa: E402

_point_routes("precision_planting.2020", _PP_SOURCES,
              vocabulary="Marker", file_kind="shapefile",
              media_path="Drive root, or a folder named exactly SendTo2020")
_point_routes("teejet.matrix_pro_gs", _TJ_SOURCES,
              vocabulary="Marker", file_kind="shapefile")
_point_routes("agopengps.aog", _AOG_SOURCES,
              vocabulary="Flag", file_kind="shapefile",
              media_path="The field folder under your AgOpenGPS Fields directory",
              filesystem="any — this is a PC, not an embedded display")
