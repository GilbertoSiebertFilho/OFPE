"""SQLite persistence.

Geometry is stored as JSON in a text column rather than in a spatial extension.
That is a deliberate trade: this platform never queries *by* geometry (no "which
fields intersect this polygon"), it only ever loads a field whole, so a spatial
index would buy nothing and would cost the ability to run on a bare Python
install. If spatial queries ever become a requirement, the same schema moves to
PostGIS with the geometry columns rebuilt from the JSON.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .geo import LatLon
from .models import FieldRecord, GuidanceLine, Machine

__all__ = ["Database", "DEFAULT_DB_PATH"]

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "abline.sqlite3"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS machines (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    brand         TEXT NOT NULL DEFAULT '',
    model         TEXT NOT NULL DEFAULT '',
    category      TEXT NOT NULL DEFAULT 'other',
    working_width_m REAL NOT NULL DEFAULT 0,
    overlap_m     REAL NOT NULL DEFAULT 0,
    section_count INTEGER NOT NULL DEFAULT 1,
    lateral_offset_m REAL NOT NULL DEFAULT 0,
    inline_offset_m  REAL NOT NULL DEFAULT 0,
    monitor_key   TEXT NOT NULL DEFAULT '',
    notes         TEXT NOT NULL DEFAULT '',
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fields (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    farm       TEXT NOT NULL DEFAULT '',
    grower     TEXT NOT NULL DEFAULT '',
    boundary   TEXT NOT NULL DEFAULT '[]',
    notes      TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lines (
    id            TEXT PRIMARY KEY,
    field_id      TEXT NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    machine_id    TEXT NOT NULL DEFAULT '',
    name          TEXT NOT NULL,
    pattern       TEXT NOT NULL,
    points        TEXT NOT NULL DEFAULT '[]',
    ring_sizes    TEXT NOT NULL DEFAULT '[]',
    heading_deg   REAL,
    radius_m      REAL,
    swath_width_m REAL NOT NULL DEFAULT 0,
    propagation   TEXT NOT NULL DEFAULT 'both',
    extension     TEXT NOT NULL DEFAULT 'both',
    swaths_left   INTEGER,
    swaths_right  INTEGER,
    source        TEXT NOT NULL DEFAULT 'manual',
    source_detail TEXT NOT NULL DEFAULT '',
    confidence    TEXT NOT NULL DEFAULT 'ok',
    published     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lines_field ON lines(field_id);
CREATE INDEX IF NOT EXISTS idx_lines_machine ON lines(machine_id);
CREATE INDEX IF NOT EXISTS idx_machines_monitor ON machines(monitor_key);
"""


class Database:
    """A thin, explicit data layer.

    One connection per thread: SQLite connections are not safe to share across
    threads, and the web layer runs handlers on a thread pool.
    """

    def __init__(self, path: str | Path = DEFAULT_DB_PATH):
        self.path = Path(path)
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        # An in-memory database lives only as long as its connection, so a
        # per-thread connection would give each thread its own empty database.
        self._shared = self._connect() if str(self.path) == ":memory:" else None
        with self.connection() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    @property
    def _conn(self) -> sqlite3.Connection:
        if self._shared is not None:
            return self._shared
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = self._connect()
            self._local.conn = conn
        return conn

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = self._conn
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def close(self) -> None:
        if self._shared is not None:
            self._shared.close()
            self._shared = None
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None

    # ---------------------------------------------------------------- machines

    def save_machine(self, machine: Machine) -> Machine:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO machines (id, name, brand, model, category,
                    working_width_m, overlap_m, section_count, lateral_offset_m,
                    inline_offset_m, monitor_key, notes, created_at)
                VALUES (:id, :name, :brand, :model, :category, :working_width_m,
                    :overlap_m, :section_count, :lateral_offset_m,
                    :inline_offset_m, :monitor_key, :notes, :created_at)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name, brand=excluded.brand,
                    model=excluded.model, category=excluded.category,
                    working_width_m=excluded.working_width_m,
                    overlap_m=excluded.overlap_m,
                    section_count=excluded.section_count,
                    lateral_offset_m=excluded.lateral_offset_m,
                    inline_offset_m=excluded.inline_offset_m,
                    monitor_key=excluded.monitor_key, notes=excluded.notes
                """,
                {
                    "id": machine.id,
                    "name": machine.name,
                    "brand": machine.brand,
                    "model": machine.model,
                    "category": machine.category.value,
                    "working_width_m": machine.working_width_m,
                    "overlap_m": machine.overlap_m,
                    "section_count": machine.section_count,
                    "lateral_offset_m": machine.lateral_offset_m,
                    "inline_offset_m": machine.inline_offset_m,
                    "monitor_key": machine.monitor_key,
                    "notes": machine.notes,
                    "created_at": machine.created_at,
                },
            )
        return machine

    def get_machine(self, machine_id: str) -> Machine | None:
        row = self._conn.execute(
            "SELECT * FROM machines WHERE id = ?", (machine_id,)
        ).fetchone()
        return _machine_from_row(row) if row else None

    def list_machines(self) -> list[Machine]:
        rows = self._conn.execute(
            "SELECT * FROM machines ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [_machine_from_row(r) for r in rows]

    def delete_machine(self, machine_id: str) -> bool:
        with self.connection() as conn:
            cursor = conn.execute("DELETE FROM machines WHERE id = ?", (machine_id,))
            # Lines outlive the machine that made them: the geometry is still
            # valid, it just loses its machine label.
            conn.execute(
                "UPDATE lines SET machine_id = '' WHERE machine_id = ?", (machine_id,)
            )
        return cursor.rowcount > 0

    # ------------------------------------------------------------------ fields

    def save_field(self, field: FieldRecord) -> FieldRecord:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO fields (id, name, farm, grower, boundary, notes, created_at)
                VALUES (:id, :name, :farm, :grower, :boundary, :notes, :created_at)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name, farm=excluded.farm,
                    grower=excluded.grower, boundary=excluded.boundary,
                    notes=excluded.notes
                """,
                {
                    "id": field.id,
                    "name": field.name,
                    "farm": field.farm,
                    "grower": field.grower,
                    "boundary": json.dumps(
                        [[[p.lat, p.lon] for p in ring] for ring in field.boundary]
                    ),
                    "notes": field.notes,
                    "created_at": field.created_at,
                },
            )
        return field

    def get_field(self, field_id: str) -> FieldRecord | None:
        row = self._conn.execute(
            "SELECT * FROM fields WHERE id = ?", (field_id,)
        ).fetchone()
        return _field_from_row(row) if row else None

    def list_fields(self) -> list[FieldRecord]:
        rows = self._conn.execute(
            "SELECT * FROM fields ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [_field_from_row(r) for r in rows]

    def delete_field(self, field_id: str) -> bool:
        with self.connection() as conn:
            cursor = conn.execute("DELETE FROM fields WHERE id = ?", (field_id,))
        return cursor.rowcount > 0

    # ------------------------------------------------------------------- lines

    def save_line(self, line: GuidanceLine, *, published: bool = True) -> GuidanceLine:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO lines (id, field_id, machine_id, name, pattern, points,
                    ring_sizes, heading_deg, radius_m, swath_width_m, propagation,
                    extension, swaths_left, swaths_right, source, source_detail,
                    confidence, published, created_at)
                VALUES (:id, :field_id, :machine_id, :name, :pattern, :points,
                    :ring_sizes, :heading_deg, :radius_m, :swath_width_m,
                    :propagation, :extension, :swaths_left, :swaths_right,
                    :source, :source_detail, :confidence, :published, :created_at)
                ON CONFLICT(id) DO UPDATE SET
                    field_id=excluded.field_id, machine_id=excluded.machine_id,
                    name=excluded.name, pattern=excluded.pattern,
                    points=excluded.points, ring_sizes=excluded.ring_sizes,
                    heading_deg=excluded.heading_deg, radius_m=excluded.radius_m,
                    swath_width_m=excluded.swath_width_m,
                    propagation=excluded.propagation, extension=excluded.extension,
                    swaths_left=excluded.swaths_left,
                    swaths_right=excluded.swaths_right, source=excluded.source,
                    source_detail=excluded.source_detail,
                    confidence=excluded.confidence, published=excluded.published
                """,
                {
                    "id": line.id,
                    "field_id": line.field_id,
                    "machine_id": line.machine_id,
                    "name": line.name,
                    "pattern": line.pattern.value,
                    "points": json.dumps([[p.lat, p.lon] for p in line.points]),
                    "ring_sizes": json.dumps(line.ring_sizes),
                    "heading_deg": line.heading_deg,
                    "radius_m": line.radius_m,
                    "swath_width_m": line.swath_width_m,
                    "propagation": line.propagation.value,
                    "extension": line.extension.value,
                    "swaths_left": line.swaths_left,
                    "swaths_right": line.swaths_right,
                    "source": line.source.value,
                    "source_detail": line.source_detail,
                    "confidence": line.confidence,
                    "published": 1 if published else 0,
                    "created_at": line.created_at,
                },
            )
        return line

    def get_line(self, line_id: str) -> GuidanceLine | None:
        row = self._conn.execute(
            "SELECT * FROM lines WHERE id = ?", (line_id,)
        ).fetchone()
        return _line_from_row(row) if row else None

    def list_lines(
        self,
        *,
        field_id: str | None = None,
        machine_id: str | None = None,
        published_only: bool = False,
    ) -> list[GuidanceLine]:
        clauses: list[str] = []
        params: list[Any] = []
        if field_id:
            clauses.append("field_id = ?")
            params.append(field_id)
        if machine_id:
            clauses.append("machine_id = ?")
            params.append(machine_id)
        if published_only:
            clauses.append("published = 1")
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"SELECT * FROM lines{where} ORDER BY created_at DESC", params
        ).fetchall()
        return [_line_from_row(r) for r in rows]

    def delete_line(self, line_id: str) -> bool:
        with self.connection() as conn:
            cursor = conn.execute("DELETE FROM lines WHERE id = ?", (line_id,))
        return cursor.rowcount > 0

    def set_published(self, line_id: str, published: bool) -> bool:
        with self.connection() as conn:
            cursor = conn.execute(
                "UPDATE lines SET published = ? WHERE id = ?",
                (1 if published else 0, line_id),
            )
        return cursor.rowcount > 0

    # ------------------------------------------------------------- convenience

    def producer_catalog(self) -> list[dict[str, Any]]:
        """What the producer tab lists: machines that have published lines.

        Built as one query plus a grouping rather than a query per machine,
        because this is the request every producer makes first.
        """
        rows = self._conn.execute(
            """
            SELECT m.id AS machine_id, m.name AS machine_name, m.brand,
                   m.category, m.working_width_m, m.monitor_key,
                   l.id AS line_id, l.name AS line_name, l.pattern,
                   l.swath_width_m, l.source, l.confidence,
                   f.id AS field_id, f.name AS field_name, f.farm, f.grower
            FROM machines m
            JOIN lines l ON l.machine_id = m.id AND l.published = 1
            JOIN fields f ON f.id = l.field_id
            ORDER BY m.name COLLATE NOCASE, f.name COLLATE NOCASE, l.created_at DESC
            """
        ).fetchall()

        catalog: dict[str, dict[str, Any]] = {}
        for row in rows:
            machine = catalog.setdefault(
                row["machine_id"],
                {
                    "machine_id": row["machine_id"],
                    "machine_name": row["machine_name"],
                    "brand": row["brand"],
                    "category": row["category"],
                    "working_width_m": row["working_width_m"],
                    "monitor_key": row["monitor_key"],
                    "fields": {},
                },
            )
            field = machine["fields"].setdefault(
                row["field_id"],
                {
                    "field_id": row["field_id"],
                    "field_name": row["field_name"],
                    "farm": row["farm"],
                    "grower": row["grower"],
                    "lines": [],
                },
            )
            field["lines"].append(
                {
                    "line_id": row["line_id"],
                    "name": row["line_name"],
                    "pattern": row["pattern"],
                    "swath_width_m": row["swath_width_m"],
                    "source": row["source"],
                    "confidence": row["confidence"],
                }
            )

        return [
            {**machine, "fields": list(machine["fields"].values())}
            for machine in catalog.values()
        ]

    def stats(self) -> dict[str, int]:
        def count(table: str) -> int:
            return self._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

        return {
            "machines": count("machines"),
            "fields": count("fields"),
            "lines": count("lines"),
            "published_lines": self._conn.execute(
                "SELECT COUNT(*) FROM lines WHERE published = 1"
            ).fetchone()[0],
        }


def _machine_from_row(row: sqlite3.Row) -> Machine:
    return Machine.from_dict(dict(row))


def _field_from_row(row: sqlite3.Row) -> FieldRecord:
    data = dict(row)
    data["boundary"] = [
        [LatLon(lat, lon) for lat, lon in ring]
        for ring in json.loads(data.get("boundary") or "[]")
    ]
    return FieldRecord.from_dict(data)


def _line_from_row(row: sqlite3.Row) -> GuidanceLine:
    data = dict(row)
    data["points"] = [
        LatLon(lat, lon) for lat, lon in json.loads(data.get("points") or "[]")
    ]
    data["ring_sizes"] = json.loads(data.get("ring_sizes") or "[]")
    return GuidanceLine.from_dict(data)
