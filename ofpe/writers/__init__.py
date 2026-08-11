"""Export: turn our canonical objects into somebody else's file.

:func:`build_download` is the single entry point the web layer calls. Give it a
monitor and some lines and it returns a ready-to-serve file with the right name,
the right internal folder structure, and an instruction sheet inside.

Each monitor's *primary* format is the one its profile names; every download
also carries the fallbacks that profile lists, so a producer whose native import
misbehaves has a shapefile in the same zip rather than a second trip to the
office.
"""

from __future__ import annotations

import hashlib
import io
import re
import zipfile
from dataclasses import dataclass

from ..catalog import FORMATS, MonitorProfile, SupportLevel, get_monitor
from ..models import FieldRecord, GuidanceLine, Machine, PatternType
from . import instructions as instructions_writer
from . import isoxml as isoxml_writer
from . import shp as shp_writer
from . import simple as simple_writer

__all__ = ["Download", "build_download", "build_format"]


@dataclass
class Download:
    """A file ready to hand to a browser."""

    filename: str
    media_type: str
    data: bytes
    notes: list[str]

    @property
    def size(self) -> int:
        return len(self.data)


def _digest(blob: bytes) -> str:
    """Content fingerprint, used only to spot duplicate files within a bundle."""
    return hashlib.sha256(blob).hexdigest()


def _slug(text: str, fallback: str = "field") -> str:
    """A filename component that survives Windows, macOS and a display's FAT32."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", (text or "").strip())
    cleaned = cleaned.strip("._-")
    return cleaned[:48] or fallback


def _line_rows(lines: list[GuidanceLine], machine: Machine | None):
    """Line geometry plus attributes, shared by every shapefile-shaped output."""
    rows = []
    for line in lines:
        paths = simple_writer.expand_for_export(line)
        if not paths:
            continue
        heading = line.computed_heading()
        rows.append(
            (
                line.name or "Line",
                paths,
                {
                    "PATTERN": line.pattern.value,
                    "WIDTH_M": line.swath_width_m,
                    "HEADING": heading if heading is not None else 0.0,
                    "SOURCE": line.source.value,
                    "MACHINE": machine.name if machine else "",
                    "LENGTH_M": line.length_m(),
                },
            )
        )
    return rows


def _shapefile_parts(
    field: FieldRecord, lines: list[GuidanceLine], machine: Machine | None, stem: str
) -> dict[str, bytes]:
    """The guidance shapefile, plus a boundary shapefile when there is one."""
    files: dict[str, bytes] = {}
    rows = _line_rows(lines, machine)
    if rows:
        for ext, blob in shp_writer.write_lines(rows).items():
            files[f"{stem}{ext}"] = blob
    if field.has_boundary:
        boundary = shp_writer.write_polygons(
            [
                (
                    field.name or "Boundary",
                    field.boundary,
                    {
                        "FARM": field.farm,
                        "GROWER": field.grower,
                        "AREA_HA": field.area_ha(),
                    },
                )
            ]
        )
        for ext, blob in boundary.items():
            files[f"{stem}_boundary{ext}"] = blob
    return files


def build_format(
    format_key: str,
    field: FieldRecord,
    lines: list[GuidanceLine],
    *,
    machine: Machine | None = None,
    stem: str = "guidance",
) -> dict[str, bytes]:
    """Produce the raw files for one format, keyed by their path inside a zip.

    Paths are relative and may contain folders -- that is how the vendor-specific
    layouts (TASKDATA, Raven/GFF, SendTo2020) are expressed.
    """
    if format_key == "isoxml":
        return {
            "TASKDATA/TASKDATA.XML": isoxml_writer.build_taskdata(
                field, lines, machine=machine
            )
        }

    if format_key in ("shapefile", "cnh_multiswath"):
        return _shapefile_parts(field, lines, machine, stem)

    if format_key == "sendto2020":
        return {
            f"SendTo2020/{name}": blob
            for name, blob in _shapefile_parts(field, lines, machine, stem).items()
        }

    if format_key == "raven_gff":
        grower = _slug(field.grower, "Grower")
        farm = _slug(field.farm, "Farm")
        field_name = _slug(field.name, "Field")
        base = f"Raven/GFF/{grower}/{farm}/{field_name}"
        files: dict[str, bytes] = {}
        # The shapefile copy is the part we are confident in; it goes in the
        # field folder where the display's file browser will also see it.
        for name, blob in _shapefile_parts(field, lines, machine, stem).items():
            files[f"{base}/{name}"] = blob
        # And the abLines folder Raven documents, one KML per line, so the
        # names and geometry are at least present and readable.
        for line in lines:
            single = simple_writer.build_kml(
                field, [line], machine=machine, document_name=line.name
            )
            files[f"{base}/abLines/{_slug(line.name, 'line')}.kml"] = single
        return files

    if format_key == "agopengps":
        field_dir = _slug(field.name, "Field")
        return {
            f"{field_dir}/{name}": blob
            for name, blob in simple_writer.build_agopengps(field, lines).items()
        }

    if format_key == "kml":
        return {f"{stem}.kml": simple_writer.build_kml(field, lines, machine=machine)}

    if format_key == "agco_kml":
        return {
            f"{stem}_agco.kml": simple_writer.build_agco_kml(
                field, lines, machine=machine
            )
        }

    if format_key == "geojson":
        return {
            f"{stem}.geojson": simple_writer.build_geojson(
                field, lines, machine=machine
            )
        }

    if format_key == "reference_bundle":
        files = _shapefile_parts(field, lines, machine, stem)
        files[f"{stem}.kml"] = simple_writer.build_kml(field, lines, machine=machine)
        files[f"{stem}.geojson"] = simple_writer.build_geojson(
            field, lines, machine=machine
        )
        return files

    raise KeyError(
        f"unknown format {format_key!r}. Known: {', '.join(sorted(FORMATS))}"
    )


def build_download(
    monitor_key: str,
    field: FieldRecord,
    lines: list[GuidanceLine],
    *,
    machine: Machine | None = None,
    format_key: str | None = None,
    include_fallbacks: bool = True,
) -> Download:
    """Build the file a producer downloads for one machine.

    Raises ``ValueError`` if any line will not survive export -- better to fail
    at the desk with a message than to hand over a file that imports as an empty
    list.
    """
    monitor = get_monitor(monitor_key)
    chosen = format_key or monitor.primary_format
    if chosen not in FORMATS:
        raise KeyError(f"unknown format {chosen!r}")
    if format_key and format_key not in monitor.formats:
        raise ValueError(
            f"{monitor.label} is not offered in {FORMATS[chosen].label}. "
            f"Available: {', '.join(FORMATS[k].label for k in monitor.formats)}"
        )

    if not lines:
        raise ValueError("no guidance lines selected")

    problems: list[str] = []
    for line in lines:
        for problem in line.validate():
            problems.append(f"{line.name or 'unnamed line'}: {problem}")
    if problems:
        raise ValueError("cannot export -- " + "; ".join(problems))

    notes: list[str] = []
    stem = _slug(field.name, "guidance")
    files = dict(build_format(chosen, field, lines, machine=machine, stem=stem))

    if include_fallbacks:
        # Formats overlap: a reference bundle already contains the shapefile,
        # KML and GeoJSON that are also listed as fallbacks, so adding them
        # again would hand the producer three byte-identical copies of every
        # file and no way to tell which one to use.
        #
        # The skip decision is made per *format*, not per file. Deduplicating
        # individual files looks tidier and is wrong: two shapefile sets in one
        # bundle share an identical .prj and .cpg, and dropping the second copy
        # leaves a .shp without its projection -- which is exactly the broken
        # half-set this platform exists to stop people receiving.
        for fallback in monitor.formats:
            if fallback == chosen:
                continue
            try:
                extra = build_format(
                    fallback, field, lines, machine=machine, stem=stem
                )
            except (KeyError, ValueError) as exc:
                notes.append(f"fallback {fallback} skipped: {exc}")
                continue
            # Content, not path: the Raven layout already carries the shapefile
            # deep inside Raven/GFF/..., and adding the plain shapefile fallback
            # would put a second identical copy at the root.
            present = {_digest(blob) for blob in files.values()}
            if extra and all(_digest(blob) in present for blob in extra.values()):
                continue  # already in the bundle, whole and unchanged
            for name, blob in extra.items():
                target = name if name not in files else f"alternative_formats/{name}"
                files.setdefault(target, blob)

    sheet = instructions_writer.build_instructions(
        monitor,
        field,
        lines,
        machine=machine,
        format_key=chosen,
        file_list=list(files),
    )
    files["HOW-TO-IMPORT.txt"] = sheet.encode("utf-8")

    if monitor.support is SupportLevel.DESKTOP_BRIDGE:
        notes.append(
            f"{monitor.brand} guidance files are closed. This download feeds "
            f"{monitor.brand}'s own software, which then writes the display file."
        )
    if monitor.support is SupportLevel.NEEDS_SAMPLE:
        notes.append(
            "The native file layout for this display is unverified. A shapefile "
            "copy is included in the same download as a fallback."
        )
    if any(line.pattern is PatternType.PIVOT for line in lines) and chosen != "isoxml":
        notes.append(
            "Pivot patterns are stored as a centre and a radius. Formats other "
            "than ISOXML cannot express that, so the circle is written out as a "
            "dense ring instead."
        )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, blob in sorted(files.items()):
            archive.writestr(name, blob)

    filename = f"{_slug(monitor.key.replace('.', '_'))}_{stem}.zip"
    return Download(
        filename=filename,
        media_type="application/zip",
        data=buffer.getvalue(),
        notes=notes,
    )
