from __future__ import annotations

from pathlib import Path

from gosimine.seed import populate_database


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data" / "gosimine.sqlite3"
SEED_PATH = PROJECT_ROOT / "seed" / "miners.json"


def main() -> None:
    populate_database(DATABASE_PATH, SEED_PATH)


if __name__ == "__main__":
    main()