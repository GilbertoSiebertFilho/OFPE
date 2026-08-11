"""Shared fixtures.

The demo field is a rectangle in southern Brazil roughly 1.48 km east-west by
1.00 km north-south -- about 148 ha, big enough that pass counts are meaningful
and small enough that the numbers can be checked by hand.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ofpe.db import Database  # noqa: E402
from ofpe.geo import LatLon  # noqa: E402
from ofpe.models import FieldRecord, Machine, MachineCategory  # noqa: E402


@pytest.fixture
def rectangle_field() -> FieldRecord:
    return FieldRecord(
        name="Test Rectangle",
        farm="Test Farm",
        grower="Test Grower",
        boundary=[[
            LatLon(-27.8400, -54.4850),
            LatLon(-27.8400, -54.4700),
            LatLon(-27.8490, -54.4700),
            LatLon(-27.8490, -54.4850),
        ]],
    )


@pytest.fixture
def combine() -> Machine:
    return Machine(
        name="Test combine",
        brand="John Deere",
        category=MachineCategory.COMBINE,
        working_width_m=12.0,
        monitor_key="john_deere.gen4",
    )


@pytest.fixture
def isobus_machine() -> Machine:
    return Machine(
        name="Test drill",
        brand="Generic",
        category=MachineCategory.SEEDER,
        working_width_m=6.0,
        monitor_key="generic.isobus",
    )


@pytest.fixture
def db() -> Database:
    database = Database(":memory:")
    yield database
    database.close()


@pytest.fixture
def client(db):
    from fastapi.testclient import TestClient

    from ofpe.web.app import create_app, get_db

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
