from __future__ import annotations

import json
from pathlib import Path

from gosimine.database import Database


def load_seed_records(seed_path: Path) -> list[dict[str, object]]:
    if seed_path.is_file():
        records = json.loads(seed_path.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise ValueError(f"Seed file must contain a JSON array: {seed_path}")
        return records
    if not seed_path.is_dir():
        raise FileNotFoundError(f"Seed path does not exist: {seed_path}")

    records = []
    for record_path in sorted(seed_path.glob("*.json")):
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            raise ValueError(f"Miner seed must contain a JSON object: {record_path}")
        records.append(record)
    return records


def populate_database(database_path: Path, seed_path: Path) -> None:
    records = load_seed_records(seed_path)
    database = Database(database_path)
    try:
        database.import_catalog(records)
    finally:
        database.close()


def initialize_database(database_path: Path, seed_path: Path) -> None:
    if not database_path.exists():
        populate_database(database_path, seed_path)