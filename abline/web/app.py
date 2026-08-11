"""FastAPI application: the operations API and the producer API.

Two audiences, one process. ``/api/...`` is the operations side -- machines,
fields, line generation, imports. ``/api/producer/...`` is deliberately narrow:
list what is published, download it, read the instructions. The producer surface
is read-only by construction rather than by permission check, which is the
simplest way to keep an open, no-login tab from becoming a way to edit the
library.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field as PField

from .. import catalog as catalog_module
from ..db import DEFAULT_DB_PATH, Database
from ..fitting import fit_guidance_from_track
from ..generate import (
    expand_swaths,
    line_from_boundary,
    make_a_plus_line,
    make_ab_line,
    make_curve_line,
    make_headland,
    make_pivot_line,
    optimize_heading,
)
from ..geo import LatLon
from ..models import (
    FieldRecord,
    GuidanceLine,
    LineSource,
    Machine,
    MachineCategory,
    PatternType,
)
from ..readers import read_any
from ..writers import build_download

STATIC_DIR = Path(__file__).resolve().parent / "static"

# A single database for the process. Tests override it with an in-memory one
# through the dependency below rather than by reaching into module state.
_database: Database | None = None


def get_db() -> Database:
    global _database
    if _database is None:
        _database = Database(os.environ.get("ABLINE_DB", DEFAULT_DB_PATH))
    return _database


def set_db(database: Database) -> None:
    global _database
    _database = database


# --------------------------------------------------------------------------- #
#  Request models                                                              #
# --------------------------------------------------------------------------- #


class MachineIn(BaseModel):
    id: str | None = None
    name: str
    brand: str = ""
    model: str = ""
    category: str = "other"
    working_width_m: float = PField(gt=0)
    overlap_m: float = 0.0
    section_count: int = 1
    lateral_offset_m: float = 0.0
    inline_offset_m: float = 0.0
    monitor_key: str = ""
    notes: str = ""


class FieldIn(BaseModel):
    id: str | None = None
    name: str
    farm: str = ""
    grower: str = ""
    boundary: list[list[list[float]]] = PField(default_factory=list)
    notes: str = ""


class LineIn(BaseModel):
    field_id: str
    machine_id: str = ""
    name: str = ""
    pattern: Literal["AB", "A_PLUS", "CURVE", "PIVOT"] = "AB"
    points: list[list[float]] = PField(default_factory=list)
    heading_deg: float | None = None
    radius_m: float | None = None
    swath_width_m: float | None = None
    publish: bool = True


class FromBoundaryIn(BaseModel):
    field_id: str
    machine_id: str
    strategy: Literal["min_passes", "longest_edge"] = "min_passes"
    name: str = ""
    headland_passes: int = 0
    publish: bool = True


class DownloadIn(BaseModel):
    monitor_key: str
    line_ids: list[str]
    machine_id: str = ""
    format_key: str | None = None
    include_fallbacks: bool = True


def _latlon_list(raw: list[list[float]]) -> list[LatLon]:
    out: list[LatLon] = []
    for item in raw:
        if len(item) < 2:
            raise HTTPException(422, "each point needs a latitude and a longitude")
        lat, lon = float(item[0]), float(item[1])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise HTTPException(
                422,
                f"point ({lat}, {lon}) is out of range. Points are [latitude, "
                "longitude] -- check they are not swapped.",
            )
        out.append(LatLon(lat, lon))
    return out


def _require_field(db: Database, field_id: str) -> FieldRecord:
    field = db.get_field(field_id)
    if field is None:
        raise HTTPException(404, f"no field with id {field_id!r}")
    return field


def _require_machine(db: Database, machine_id: str) -> Machine:
    machine = db.get_machine(machine_id)
    if machine is None:
        raise HTTPException(404, f"no machine with id {machine_id!r}")
    return machine


# --------------------------------------------------------------------------- #
#  Routes                                                                      #
# --------------------------------------------------------------------------- #

api = APIRouter(prefix="/api")


@api.get("/health")
def health(db: Database = Depends(get_db)) -> dict[str, Any]:
    return {"status": "ok", **db.stats()}


@api.get("/catalog/monitors")
def list_monitors() -> dict[str, Any]:
    return {
        "brands": catalog_module.BRANDS,
        "monitors": [m.to_dict() for m in catalog_module.iter_monitors()],
        "formats": [
            {
                "key": f.key,
                "label": f.label,
                "extension": f.extension,
                "description": f.description,
                "spec": f.spec,
            }
            for f in catalog_module.FORMATS.values()
        ],
        "support_levels": [
            {"key": level.value, "headline": level.headline,
             "downloadable": level.is_downloadable}
            for level in catalog_module.SupportLevel
        ],
    }


@api.get("/catalog/monitors/{monitor_key}")
def get_monitor(monitor_key: str) -> dict[str, Any]:
    try:
        return catalog_module.get_monitor(monitor_key).to_dict()
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


# ------------------------------------------------------------------- machines


@api.get("/machines")
def list_machines(db: Database = Depends(get_db)) -> list[dict[str, Any]]:
    return [m.to_dict() for m in db.list_machines()]


@api.post("/machines", status_code=201)
def create_machine(payload: MachineIn, db: Database = Depends(get_db)) -> dict[str, Any]:
    if payload.overlap_m >= payload.working_width_m:
        raise HTTPException(
            422,
            f"overlap ({payload.overlap_m} m) must be smaller than the working "
            f"width ({payload.working_width_m} m), or the swath spacing would be "
            "zero or negative.",
        )
    if payload.monitor_key and payload.monitor_key not in catalog_module.MONITORS:
        raise HTTPException(422, f"unknown monitor {payload.monitor_key!r}")
    try:
        category = MachineCategory(payload.category)
    except ValueError:
        raise HTTPException(
            422,
            f"unknown category {payload.category!r}. Options: "
            + ", ".join(c.value for c in MachineCategory),
        ) from None

    data = payload.model_dump()
    data["category"] = category.value
    if not data.get("id"):
        data.pop("id", None)
    machine = Machine.from_dict(data)
    db.save_machine(machine)
    return machine.to_dict()


@api.delete("/machines/{machine_id}", status_code=204)
def delete_machine(machine_id: str, db: Database = Depends(get_db)) -> Response:
    if not db.delete_machine(machine_id):
        raise HTTPException(404, f"no machine with id {machine_id!r}")
    return Response(status_code=204)


# --------------------------------------------------------------------- fields


@api.get("/fields")
def list_fields(db: Database = Depends(get_db)) -> list[dict[str, Any]]:
    return [f.to_dict() for f in db.list_fields()]


@api.post("/fields", status_code=201)
def create_field(payload: FieldIn, db: Database = Depends(get_db)) -> dict[str, Any]:
    boundary = [_latlon_list(ring) for ring in payload.boundary]
    for ring in boundary:
        if len(ring) < 3:
            raise HTTPException(422, "a boundary ring needs at least 3 points")
    field = FieldRecord(
        id=payload.id or FieldRecord().id,
        name=payload.name,
        farm=payload.farm,
        grower=payload.grower,
        boundary=boundary,
        notes=payload.notes,
    )
    db.save_field(field)
    return field.to_dict()


@api.get("/fields/{field_id}")
def get_field(field_id: str, db: Database = Depends(get_db)) -> dict[str, Any]:
    return _require_field(db, field_id).to_dict()


@api.delete("/fields/{field_id}", status_code=204)
def delete_field(field_id: str, db: Database = Depends(get_db)) -> Response:
    if not db.delete_field(field_id):
        raise HTTPException(404, f"no field with id {field_id!r}")
    return Response(status_code=204)


# ---------------------------------------------------------------------- lines


@api.get("/lines")
def list_lines(
    field_id: str | None = None,
    machine_id: str | None = None,
    db: Database = Depends(get_db),
) -> list[dict[str, Any]]:
    return [
        line.to_dict()
        for line in db.list_lines(field_id=field_id, machine_id=machine_id)
    ]


@api.post("/lines", status_code=201)
def create_line(payload: LineIn, db: Database = Depends(get_db)) -> dict[str, Any]:
    field = _require_field(db, payload.field_id)
    machine = db.get_machine(payload.machine_id) if payload.machine_id else None

    width = payload.swath_width_m
    if width is None:
        if machine is None:
            raise HTTPException(
                422,
                "give a swath width, or pick a machine to take the width from.",
            )
        width = machine.effective_width_m
    if width <= 0:
        raise HTTPException(422, "swath width must be positive")

    points = _latlon_list(payload.points)
    kwargs = dict(
        width_m=width,
        field_id=field.id,
        machine_id=machine.id if machine else "",
        source=LineSource.MANUAL,
    )

    try:
        if payload.pattern == "AB":
            if len(points) != 2:
                raise HTTPException(422, "an AB line needs exactly two points")
            line = make_ab_line(points[0], points[1], name=payload.name or "AB line", **kwargs)
        elif payload.pattern == "A_PLUS":
            if len(points) != 1 or payload.heading_deg is None:
                raise HTTPException(422, "an A+ line needs one point and a heading")
            line = make_a_plus_line(
                points[0], payload.heading_deg, name=payload.name or "A+ line", **kwargs
            )
        elif payload.pattern == "CURVE":
            if len(points) < 2:
                raise HTTPException(422, "a curve needs at least two points")
            line = make_curve_line(points, name=payload.name or "Curve", **kwargs)
        else:  # PIVOT
            if len(points) != 1 or not payload.radius_m:
                raise HTTPException(422, "a pivot needs one centre point and a radius")
            line = make_pivot_line(
                points[0], payload.radius_m, name=payload.name or "Pivot", **kwargs
            )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    problems = line.validate()
    if problems:
        raise HTTPException(422, "; ".join(problems))

    db.save_line(line, published=payload.publish)
    return line.to_dict()


@api.post("/lines/from-boundary", status_code=201)
def create_from_boundary(
    payload: FromBoundaryIn, db: Database = Depends(get_db)
) -> dict[str, Any]:
    field = _require_field(db, payload.field_id)
    machine = _require_machine(db, payload.machine_id)
    if not field.has_boundary:
        raise HTTPException(
            422,
            f"field {field.name!r} has no boundary, so there is nothing to "
            "optimise against. Import or draw a boundary first.",
        )

    try:
        line, choice = line_from_boundary(
            field, machine, strategy=payload.strategy, name=payload.name
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    db.save_line(line, published=payload.publish)
    created = [line.to_dict()]

    if payload.headland_passes > 0:
        try:
            headland = make_headland(
                field,
                width_m=machine.effective_width_m,
                passes=payload.headland_passes,
                name=f"{field.name or 'Field'} headland",
                machine_id=machine.id,
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        db.save_line(headland, published=payload.publish)
        created.append(headland.to_dict())

    return {
        "lines": created,
        "heading": {
            "heading_deg": round(choice.heading_deg, 4),
            "pass_count": choice.pass_count,
            "segment_count": choice.segment_count,
            "total_length_m": round(choice.total_length_m, 1),
            "strategy": choice.strategy,
            "headings_considered": choice.considered,
        },
    }


@api.get("/fields/{field_id}/heading")
def suggest_heading(
    field_id: str,
    machine_id: str,
    strategy: Literal["min_passes", "longest_edge"] = "min_passes",
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    """Score a heading without saving anything -- for the 'what if' control."""
    field = _require_field(db, field_id)
    machine = _require_machine(db, machine_id)
    try:
        choice = optimize_heading(field, machine.effective_width_m, strategy=strategy)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {
        "heading_deg": round(choice.heading_deg, 4),
        "pass_count": choice.pass_count,
        "segment_count": choice.segment_count,
        "total_length_m": round(choice.total_length_m, 1),
        "strategy": choice.strategy,
        "headings_considered": choice.considered,
        "width_m": machine.effective_width_m,
    }


@api.get("/lines/{line_id}/preview")
def preview_line(
    line_id: str, max_swaths: int = 400, db: Database = Depends(get_db)
) -> dict[str, Any]:
    line = db.get_line(line_id)
    if line is None:
        raise HTTPException(404, f"no line with id {line_id!r}")
    field = db.get_field(line.field_id) if line.field_id else None
    machine = db.get_machine(line.machine_id) if line.machine_id else None
    try:
        swaths = expand_swaths(line, field, machine=machine, max_swaths=max_swaths)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {
        "line": line.to_dict(),
        "field": field.to_dict() if field else None,
        "swaths": swaths.to_dict(),
    }


@api.post("/lines/{line_id}/publish")
def publish_line(
    line_id: str, published: bool = True, db: Database = Depends(get_db)
) -> dict[str, Any]:
    if not db.set_published(line_id, published):
        raise HTTPException(404, f"no line with id {line_id!r}")
    return {"line_id": line_id, "published": published}


@api.delete("/lines/{line_id}", status_code=204)
def delete_line(line_id: str, db: Database = Depends(get_db)) -> Response:
    if not db.delete_line(line_id):
        raise HTTPException(404, f"no line with id {line_id!r}")
    return Response(status_code=204)


# --------------------------------------------------------------------- import


@api.post("/import")
async def import_file(
    file: UploadFile = File(...),
    persist: bool = Form(False),
    machine_id: str = Form(""),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    """Read any supported file. Set ``persist`` to also save what came back."""
    data = await file.read()
    if not data:
        raise HTTPException(422, "the uploaded file is empty")
    try:
        result = read_any(file.filename or "upload", data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    machine = db.get_machine(machine_id) if machine_id else None
    saved = {"fields": 0, "lines": 0}

    if persist:
        # A line imported from a format that does not record swath width comes
        # back as zero, which would export as an unusable file. The selected
        # machine fills that gap.
        for field in result.fields:
            db.save_field(field)
            saved["fields"] += 1
        default_field = result.fields[0] if result.fields else None
        for line in result.lines:
            if not line.swath_width_m and machine:
                line.swath_width_m = machine.effective_width_m
                line.source_detail = (
                    f"{line.source_detail}; width taken from {machine.name}"
                ).strip("; ")
            if machine:
                line.machine_id = machine.id
            if not line.field_id and default_field:
                line.field_id = default_field.id
            if not line.field_id:
                result.warnings.append(
                    f"line {line.name!r} was not saved: the file carried no "
                    "field for it to belong to."
                )
                continue
            if not line.swath_width_m:
                result.warnings.append(
                    f"line {line.name!r} was not saved: no swath width in the "
                    "file and no machine selected to take one from."
                )
                continue
            db.save_line(line)
            saved["lines"] += 1

    payload = result.to_dict()
    payload["persisted"] = saved if persist else None
    return payload


@api.post("/fit")
async def fit_from_track(
    file: UploadFile = File(...),
    machine_id: str = Form(""),
    field_id: str = Form(""),
    name: str = Form("Fitted line"),
    force_pattern: str = Form(""),
    persist: bool = Form(False),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    """Fit a guidance line to a recorded machine track."""
    data = await file.read()
    if not data:
        raise HTTPException(422, "the uploaded file is empty")
    try:
        result = read_any(file.filename or "upload", data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    if not result.track:
        raise HTTPException(
            422,
            f"{file.filename}: no track points found. Fitting needs a log with "
            "a row per recorded position (latitude and longitude columns).",
        )

    machine = db.get_machine(machine_id) if machine_id else None
    try:
        fit = fit_guidance_from_track(
            result.track,
            name=name,
            field_id=field_id,
            machine_id=machine.id if machine else "",
            declared_width_m=machine.effective_width_m if machine else None,
            force_pattern=force_pattern or None,
            source_detail=f"fitted from {file.filename}",
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    payload = fit.to_dict()
    payload["read_warnings"] = result.warnings
    payload["persisted"] = False

    if persist:
        if not field_id:
            raise HTTPException(422, "pick a field to save the fitted line into")
        _require_field(db, field_id)
        db.save_line(fit.line)
        payload["persisted"] = True
    return payload


# ------------------------------------------------------------------- download


@api.post("/download")
def download(payload: DownloadIn, db: Database = Depends(get_db)) -> Response:
    lines = [db.get_line(line_id) for line_id in payload.line_ids]
    missing = [
        line_id for line_id, line in zip(payload.line_ids, lines) if line is None
    ]
    if missing:
        raise HTTPException(404, f"no line with id {', '.join(missing)}")
    resolved: list[GuidanceLine] = [line for line in lines if line is not None]
    if not resolved:
        raise HTTPException(422, "select at least one line")

    field_ids = {line.field_id for line in resolved}
    if len(field_ids) > 1:
        raise HTTPException(
            422,
            "all selected lines must belong to one field -- a download is built "
            "around a single field. Download them as separate files.",
        )
    field = _require_field(db, resolved[0].field_id)

    machine_id = payload.machine_id or resolved[0].machine_id
    machine = db.get_machine(machine_id) if machine_id else None

    try:
        result = build_download(
            payload.monitor_key,
            field,
            resolved,
            machine=machine,
            format_key=payload.format_key,
            include_fallbacks=payload.include_fallbacks,
        )
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    return Response(
        content=result.data,
        media_type=result.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
            # The producer UI shows these so a two-step import is never a
            # surprise discovered after the download.
            "X-Abline-Notes": " | ".join(result.notes)[:900],
        },
    )


# ------------------------------------------------------------------- producer


producer = APIRouter(prefix="/api/producer")


@producer.get("/catalog")
def producer_catalog(db: Database = Depends(get_db)) -> dict[str, Any]:
    """Everything the producer tab needs, in one request.

    Each machine is joined to its monitor profile here rather than in the
    browser, so the tab can render support level, format and instructions
    without a second round trip.
    """
    entries = db.producer_catalog()
    for entry in entries:
        key = entry.get("monitor_key") or ""
        monitor = catalog_module.MONITORS.get(key)
        entry["monitor"] = monitor.to_dict() if monitor else None
        if monitor is None:
            entry["monitor_warning"] = (
                "No display has been set for this machine, so we cannot pick a "
                "file format. Contact the office."
                if not key
                else f"Unknown display {key!r}."
            )
    return {"machines": entries}


@producer.get("/machines/{machine_id}/instructions")
def producer_instructions(machine_id: str, db: Database = Depends(get_db)) -> dict[str, Any]:
    machine = _require_machine(db, machine_id)
    monitor = catalog_module.MONITORS.get(machine.monitor_key)
    if monitor is None:
        raise HTTPException(
            404,
            f"machine {machine.name!r} has no display set, so there are no "
            "import instructions to give.",
        )
    return {"machine": machine.to_dict(), "monitor": monitor.to_dict()}


def create_app() -> FastAPI:
    app = FastAPI(
        title="CWSI AB Line Platform",
        version="1.0",
        description=(
            "Build guidance lines from machine data, field boundaries or your "
            "own AB parameters, and hand them to producers in the file format "
            "their display actually reads."
        ),
    )
    app.include_router(api)
    app.include_router(producer)

    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

        @app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
