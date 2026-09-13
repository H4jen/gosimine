from __future__ import annotations

import json
from pathlib import Path

from gosimine.database import Database


def populate_database(database_path: Path, seed_path: Path) -> None:
    records = json.loads(seed_path.read_text(encoding="utf-8"))
    database = Database(database_path)
    try:
        database.import_catalog(records)
    finally:
        database.close()


def initialize_database(database_path: Path, seed_path: Path) -> None:
    if not database_path.exists():
        populate_database(database_path, seed_path)