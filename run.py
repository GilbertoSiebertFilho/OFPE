#!/usr/bin/env python3
"""Start the AB Line Platform.

    python3 run.py                      # http://127.0.0.1:8000
    python3 run.py --host 0.0.0.0       # reachable from the office network
    python3 run.py --seed               # add a demo machine, field and line

The database defaults to ``platform/data/abline.sqlite3``; override it with
``--db`` or the ``ABLINE_DB`` environment variable.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def seed(db_path: str) -> None:
    """Put one of everything in the database so the UI has something to show."""
    from abline.db import Database
    from abline.generate import line_from_boundary, make_headland
    from abline.geo import LatLon
    from abline.models import FieldRecord, Machine, MachineCategory

    db = Database(db_path)

    combine = Machine(
        name="S780 combine",
        brand="John Deere",
        model="S780",
        category=MachineCategory.COMBINE,
        working_width_m=12.2,
        overlap_m=0.2,
        monitor_key="john_deere.gen4",
        notes="40 ft draper header",
    )
    sprayer = Machine(
        name="Patriot 4440 sprayer",
        brand="Case IH",
        model="Patriot 4440",
        category=MachineCategory.SPRAYER,
        working_width_m=36.0,
        section_count=9,
        monitor_key="case_ih.afs_pro_700",
    )
    seeder = Machine(
        name="Rapid 600C drill",
        brand="Väderstad",
        model="Rapid 600C",
        category=MachineCategory.SEEDER,
        working_width_m=6.0,
        monitor_key="generic.isobus",
    )
    for machine in (combine, sprayer, seeder):
        db.save_machine(machine)

    # A rectangle a little over 100 ha, somewhere in Rio Grande do Sul.
    field = FieldRecord(
        name="Talhao Norte",
        farm="Fazenda Sao Jose",
        grower="Demo grower",
        boundary=[[
            LatLon(-27.8400, -54.4850),
            LatLon(-27.8400, -54.4700),
            LatLon(-27.8490, -54.4700),
            LatLon(-27.8490, -54.4850),
        ]],
    )
    db.save_field(field)

    for machine in (combine, sprayer, seeder):
        line, choice = line_from_boundary(field, machine)
        line.name = f"{machine.name} AB"
        db.save_line(line)
        print(
            f"  {machine.name}: heading {choice.heading_deg:.2f}deg, "
            f"{choice.pass_count} passes at {machine.effective_width_m:g} m"
        )

    headland = make_headland(
        field, width_m=combine.effective_width_m, passes=2,
        name="Headland (combine)", machine_id=combine.id,
    )
    db.save_line(headland)

    stats = db.stats()
    print(
        f"Seeded: {stats['machines']} machines, {stats['fields']} fields, "
        f"{stats['lines']} lines."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", default=os.environ.get("ABLINE_DB", ""))
    parser.add_argument("--seed", action="store_true", help="load demo data and exit")
    parser.add_argument("--reload", action="store_true", help="restart on code changes")
    args = parser.parse_args()

    if args.db:
        os.environ["ABLINE_DB"] = args.db

    if args.seed:
        from abline.db import DEFAULT_DB_PATH

        seed(args.db or str(DEFAULT_DB_PATH))
        return 0

    import uvicorn

    print(f"AB Line Platform -> http://{args.host}:{args.port}")
    uvicorn.run(
        "abline.web.app:app", host=args.host, port=args.port, reload=args.reload
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
