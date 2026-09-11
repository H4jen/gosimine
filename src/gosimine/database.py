from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Miner:
    id: int
    name: str
    ticker: str
    primary_commodity: str
    stage: str


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS miners (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                ticker TEXT NOT NULL,
                primary_commodity TEXT NOT NULL,
                stage TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def list_miners(self) -> list[Miner]:
        rows = self.connection.execute(
            "SELECT id, name, ticker, primary_commodity, stage "
            "FROM miners ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [Miner(**dict(row)) for row in rows]

    def add_miner(
        self, name: str, ticker: str, primary_commodity: str, stage: str
    ) -> Miner:
        cursor = self.connection.execute(
            "INSERT INTO miners (name, ticker, primary_commodity, stage) "
            "VALUES (?, ?, ?, ?)",
            (name.strip(), ticker.strip().upper(), primary_commodity.strip(), stage.strip()),
        )
        self.connection.commit()
        return Miner(cursor.lastrowid, name.strip(), ticker.strip().upper(), primary_commodity.strip(), stage.strip())

    def close(self) -> None:
        self.connection.close()
