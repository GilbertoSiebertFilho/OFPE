#!/usr/bin/env python3
"""Start the OFPE Field Data Platform.

    python3 run.py                      # http://127.0.0.1:8000
    python3 run.py --host 0.0.0.0       # reachable from the office network
    python3 run.py --seed               # add a demo machine, field and line

The database defaults to ``platform/data/ofpe.sqlite3``; override it with
``--db`` or the ``OFPE_DB`` environment variable.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def seed(db_path: str) -> None:
    """Put one of everything in the database so the UI has something to show."""
    from ofpe.db import Database
    from ofpe.generate import line_from_boundary, make_headland
    from ofpe.geo import LatLon
    from ofpe.models import FieldRecord, Machine, MachineCategory

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


def _port_in_use(host: str, port: int) -> bool:
    """Whether something is already listening there."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        # Without SO_REUSEADDR a port left in TIME_WAIT by a just-stopped
        # server would look occupied, and restarting the app would wrongly
        # report a conflict for a minute after every Ctrl+C.
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1" if host == "0.0.0.0" else host, port))
        except OSError:
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", default=os.environ.get("OFPE_DB", ""))
    parser.add_argument("--seed", action="store_true", help="load demo data and exit")
    parser.add_argument("--reload", action="store_true", help="restart on code changes")
    parser.add_argument(
        "--open", action="store_true", help="open a browser once the server is up"
    )
    parser.add_argument(
        "--no-seed", action="store_true", help="start empty, skip the demo data"
    )
    args = parser.parse_args()

    if args.db:
        os.environ["OFPE_DB"] = args.db

    from ofpe.db import DEFAULT_DB_PATH, Database

    db_path = args.db or str(DEFAULT_DB_PATH)

    if args.seed:
        seed(db_path)
        return 0

    # Seed on a first run so the app has something to show. Guarded on the
    # database being completely empty, which is only ever true before anyone
    # has used it -- adding demo machines to a working library would be a
    # genuinely bad surprise.
    if not args.no_seed:
        database = Database(db_path)
        empty = all(v == 0 for v in database.stats().values())
        database.close()
        if empty:
            print("First run: loading demo machines, a field and some lines.\n")
            seed(db_path)
            print()

    import uvicorn

    # Check the port before uvicorn does, because uvicorn's failure is a raw
    # errno traceback. Someone who started the app by double-clicking an icon
    # has almost always just left the first window open.
    if _port_in_use(args.host, args.port):
        print()
        print(f"  Port {args.port} is already being used by something else.")
        print()
        print("  The usual cause is that the app is already running — look for")
        print("  another window like this one, or just open the address below:")
        print(f"      http://127.0.0.1:{args.port}")
        print()
        print("  If something else needs that port, start on a different one:")
        print(f"      run.py --port {args.port + 1}")
        print()
        return 1

    url = f"http://{'127.0.0.1' if args.host == '0.0.0.0' else args.host}:{args.port}"
    if args.open:
        # uvicorn.run blocks, so the browser has to be opened from a timer.
        # A second is enough for the port to be listening; if it is not, the
        # browser shows a refusal and a reload fixes it.
        import threading
        import webbrowser

        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    print("=" * 62)
    print("  OFPE Field Data Platform")
    print(f"  Open:  {url}")
    print("  Stop:  press Ctrl+C in this window")
    print("=" * 62)
    print()
    uvicorn.run(
        "ofpe.web.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="warning",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
