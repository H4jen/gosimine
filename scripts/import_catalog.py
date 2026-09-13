from __future__ import annotations

import argparse
from pathlib import Path

from gosimine.seed import populate_database


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the curated Gosimine miner catalog.")
    parser.add_argument("--database", type=Path, default=Path("data") / "gosimine.sqlite3")
    parser.add_argument("--seed", type=Path, default=Path("seed") / "miners.json")
    arguments = parser.parse_args()
    populate_database(arguments.database, arguments.seed)


if __name__ == "__main__":
    main()