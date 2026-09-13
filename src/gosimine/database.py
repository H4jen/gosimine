from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class Miner:
    id: int
    name: str
    ticker: str
    primary_commodity: str
    stage: str
    trading_currency: str


@dataclass(frozen=True)
class CatalogMiner:
    id: int
    name: str
    ticker: str
    primary_commodity: str
    stage: str
    trading_currency: str


@dataclass(frozen=True)
class ResearchEntry:
    id: int
    miner_id: int
    entry_date: str
    note: str
    source: str
    thesis_change: str
    catalyst: str
    open_question: str


@dataclass(frozen=True)
class ParameterSnapshot:
    id: int
    miner_id: int
    parameter: str
    value: float
    unit: str
    as_of_date: str
    source: str


@dataclass(frozen=True)
class LifecycleStatusSnapshot:
    id: int
    miner_id: int
    status: str
    as_of_date: str
    source: str


@dataclass(frozen=True)
class Milestone:
    id: int
    miner_id: int
    category: str
    title: str
    target_date: str
    status: str
    detail: str
    source: str


@dataclass(frozen=True)
class MarketSnapshot:
    id: int
    miner_id: int
    price: float
    currency: str
    market_timestamp: str
    retrieved_at: str
    source: str


@dataclass(frozen=True)
class ExchangeRateSnapshot:
    id: int
    from_currency: str
    to_currency: str
    rate: float
    retrieved_at: str
    source: str


@dataclass(frozen=True)
class CommodityPriceSnapshot:
    id: int
    commodity: str
    price: float
    currency: str
    unit: str
    market_timestamp: str
    retrieved_at: str
    source: str


@dataclass(frozen=True)
class ApplicationSettingSnapshot:
    id: int
    setting: str
    value: str
    changed_at: str
    source: str


@dataclass(frozen=True)
class AnalysisScenario:
    id: int
    miner_id: int
    name: str
    metal_prices_usd: dict[str, float]
    development_risk_factor: float
    created_at: str


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._initialize()

    def _initialize(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS miners (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                ticker TEXT NOT NULL,
                primary_commodity TEXT NOT NULL,
                stage TEXT NOT NULL,
                trading_currency TEXT NOT NULL DEFAULT 'USD'
            )
            """
        )
        miner_columns = {
            row["name"] for row in self.connection.execute("PRAGMA table_info(miners)")
        }
        if "trading_currency" not in miner_columns:
            self.connection.execute(
                "ALTER TABLE miners ADD COLUMN trading_currency TEXT NOT NULL DEFAULT 'USD'"
            )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS catalog_miners (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                ticker TEXT NOT NULL UNIQUE,
                primary_commodity TEXT NOT NULL,
                stage TEXT NOT NULL,
                trading_currency TEXT NOT NULL,
                seed_record TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        catalog_columns = {
            row["name"] for row in self.connection.execute("PRAGMA table_info(catalog_miners)")
        }
        if "seed_record" not in catalog_columns:
            self.connection.execute(
                "ALTER TABLE catalog_miners ADD COLUMN seed_record TEXT NOT NULL DEFAULT '{}'"
            )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS research_entries (
                id INTEGER PRIMARY KEY,
                miner_id INTEGER NOT NULL REFERENCES miners(id),
                entry_date TEXT NOT NULL,
                note TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT '',
                thesis_change TEXT NOT NULL DEFAULT '',
                catalyst TEXT NOT NULL DEFAULT '',
                open_question TEXT NOT NULL DEFAULT ''
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS parameter_snapshots (
                id INTEGER PRIMARY KEY,
                miner_id INTEGER NOT NULL REFERENCES miners(id),
                parameter TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                as_of_date TEXT NOT NULL,
                source TEXT NOT NULL,
                UNIQUE (miner_id, parameter, value, unit, as_of_date, source)
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS lifecycle_status_snapshots (
                id INTEGER PRIMARY KEY,
                miner_id INTEGER NOT NULL REFERENCES miners(id),
                status TEXT NOT NULL,
                as_of_date TEXT NOT NULL,
                source TEXT NOT NULL,
                UNIQUE (miner_id, status, as_of_date, source)
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS milestones (
                id INTEGER PRIMARY KEY,
                miner_id INTEGER NOT NULL REFERENCES miners(id),
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                target_date TEXT NOT NULL,
                status TEXT NOT NULL,
                detail TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL,
                UNIQUE (miner_id, category, title, target_date, status, detail, source)
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS market_snapshots (
                id INTEGER PRIMARY KEY,
                miner_id INTEGER NOT NULL REFERENCES miners(id),
                price REAL NOT NULL,
                currency TEXT NOT NULL,
                market_timestamp TEXT NOT NULL,
                retrieved_at TEXT NOT NULL,
                source TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS exchange_rate_snapshots (
                id INTEGER PRIMARY KEY,
                from_currency TEXT NOT NULL,
                to_currency TEXT NOT NULL,
                rate REAL NOT NULL,
                retrieved_at TEXT NOT NULL,
                source TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS commodity_price_snapshots (
                id INTEGER PRIMARY KEY,
                commodity TEXT NOT NULL,
                price REAL NOT NULL,
                currency TEXT NOT NULL,
                unit TEXT NOT NULL,
                market_timestamp TEXT NOT NULL,
                retrieved_at TEXT NOT NULL,
                source TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS application_setting_snapshots (
                id INTEGER PRIMARY KEY,
                setting TEXT NOT NULL,
                value TEXT NOT NULL,
                changed_at TEXT NOT NULL,
                source TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_scenarios (
                id INTEGER PRIMARY KEY,
                miner_id INTEGER NOT NULL REFERENCES miners(id),
                name TEXT NOT NULL,
                metal_prices_usd TEXT NOT NULL,
                development_risk_factor REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def list_miners(self) -> list[Miner]:
        rows = self.connection.execute(
            "SELECT id, name, ticker, primary_commodity, stage, trading_currency "
            "FROM miners ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [Miner(**dict(row)) for row in rows]

    def import_catalog(self, records: list[dict[str, object]]) -> None:
        for record in records:
            values = (
                str(record["name"]).strip(),
                str(record["ticker"]).strip().upper(),
                str(record["primary_commodity"]).strip(),
                str(record["stage"]).strip(),
                str(record.get("trading_currency", "USD")).strip().upper(),
                json.dumps(record, sort_keys=True),
            )
            self.connection.execute(
                "INSERT INTO catalog_miners "
                "(name, ticker, primary_commodity, stage, trading_currency, seed_record) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(ticker) DO UPDATE SET "
                "name = excluded.name, primary_commodity = excluded.primary_commodity, "
                "stage = excluded.stage, trading_currency = excluded.trading_currency, "
                "seed_record = excluded.seed_record",
                values,
            )
        self.connection.commit()

    def list_catalog_miners(self, query: str = "") -> list[CatalogMiner]:
        search = f"%{query.strip()}%"
        rows = self.connection.execute(
            "SELECT id, name, ticker, primary_commodity, stage, trading_currency "
            "FROM catalog_miners "
            "WHERE name LIKE ? COLLATE NOCASE OR ticker LIKE ? COLLATE NOCASE "
            "OR primary_commodity LIKE ? COLLATE NOCASE "
            "ORDER BY name COLLATE NOCASE",
            (search, search, search),
        ).fetchall()
        return [CatalogMiner(**dict(row)) for row in rows]

    def get_catalog_miner_by_ticker(self, ticker: str) -> CatalogMiner | None:
        row = self.connection.execute(
            "SELECT id, name, ticker, primary_commodity, stage, trading_currency "
            "FROM catalog_miners WHERE ticker = ? COLLATE NOCASE",
            (ticker.strip().upper(),),
        ).fetchone()
        return CatalogMiner(**dict(row)) if row else None

    def select_catalog_miner(self, ticker: str) -> Miner:
        row = self.connection.execute(
            "SELECT seed_record FROM catalog_miners WHERE ticker = ? COLLATE NOCASE",
            (ticker.strip().upper(),),
        ).fetchone()
        if row is None:
            raise ValueError(f"Catalog ticker not found: {ticker.strip().upper()}")
        record = json.loads(row["seed_record"])
        if "lifecycle_status" in record and "parameters" in record:
            return self.import_miner_seed(record)
        existing_miner = self.get_miner_by_ticker(str(record["ticker"]))
        if existing_miner is not None:
            return existing_miner
        return self.add_miner(
            str(record["name"]),
            str(record["ticker"]),
            str(record["primary_commodity"]),
            str(record["stage"]),
            str(record.get("trading_currency", "USD")),
        )

    def add_miner(
        self,
        name: str,
        ticker: str,
        primary_commodity: str,
        stage: str,
        trading_currency: str = "USD",
    ) -> Miner:
        normalized_ticker = ticker.strip().upper()
        if self.get_miner_by_ticker(normalized_ticker) is not None:
            raise ValueError(f"Miner ticker already exists: {normalized_ticker}")
        cursor = self.connection.execute(
            "INSERT INTO miners (name, ticker, primary_commodity, stage, trading_currency) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                name.strip(),
                normalized_ticker,
                primary_commodity.strip(),
                stage.strip(),
                trading_currency.strip().upper(),
            ),
        )
        self.connection.commit()
        return Miner(
            cursor.lastrowid,
            name.strip(),
            normalized_ticker,
            primary_commodity.strip(),
            stage.strip(),
            trading_currency.strip().upper(),
        )

    def import_miner_seed(self, record: dict[str, object]) -> Miner:
        ticker = str(record["ticker"]).strip().upper()
        miner = self.get_miner_by_ticker(ticker)
        if miner is None:
            miner = self.add_miner(
                str(record["name"]),
                ticker,
                str(record["primary_commodity"]),
                str(record["stage"]),
                str(record.get("trading_currency", "USD")),
            )

        status = record["lifecycle_status"]
        self.add_lifecycle_status_snapshot(
            miner.id,
            str(status["value"]),
            str(status["as_of_date"]),
            str(status["source"]),
        )
        for parameter in record["parameters"]:
            self.add_parameter_snapshot(
                miner.id,
                str(parameter["name"]),
                float(parameter["value"]),
                str(parameter["unit"]),
                str(parameter["as_of_date"]),
                str(parameter["source"]),
            )
        for milestone in record.get("milestones", []):
            self.add_milestone(
                miner.id,
                str(milestone["category"]),
                str(milestone["title"]),
                str(milestone["target_date"]),
                str(milestone["status"]),
                str(milestone.get("detail", "")),
                str(milestone["source"]),
            )
        return miner

    def get_miner_by_ticker(self, ticker: str) -> Miner | None:
        row = self.connection.execute(
            "SELECT id, name, ticker, primary_commodity, stage, trading_currency "
            "FROM miners WHERE ticker = ? COLLATE NOCASE",
            (ticker.strip().upper(),),
        ).fetchone()
        return Miner(**dict(row)) if row else None

    def add_parameter_snapshot(
        self,
        miner_id: int,
        parameter: str,
        value: float,
        unit: str,
        as_of_date: str,
        source: str,
    ) -> ParameterSnapshot:
        values = (miner_id, parameter.strip(), value, unit.strip(), as_of_date.strip(), source.strip())
        cursor = self.connection.execute(
            "INSERT OR IGNORE INTO parameter_snapshots "
            "(miner_id, parameter, value, unit, as_of_date, source) VALUES (?, ?, ?, ?, ?, ?)",
            values,
        )
        self.connection.commit()
        row_id = cursor.lastrowid
        if row_id == 0:
            row_id = self.connection.execute(
                "SELECT id FROM parameter_snapshots WHERE miner_id = ? AND parameter = ? "
                "AND value = ? AND unit = ? AND as_of_date = ? AND source = ?",
                values,
            ).fetchone()["id"]
        return ParameterSnapshot(row_id, *values)

    def list_parameter_history(self, miner_id: int) -> list[ParameterSnapshot]:
        rows = self.connection.execute(
            "SELECT id, miner_id, parameter, value, unit, as_of_date, source "
            "FROM parameter_snapshots WHERE miner_id = ? ORDER BY as_of_date DESC, id DESC",
            (miner_id,),
        ).fetchall()
        return [ParameterSnapshot(**dict(row)) for row in rows]

    def list_current_parameters(self, miner_id: int) -> list[ParameterSnapshot]:
        current_parameters: dict[str, ParameterSnapshot] = {}
        for snapshot in self.list_parameter_history(miner_id):
            current_parameters.setdefault(snapshot.parameter, snapshot)
        return list(current_parameters.values())

    def add_lifecycle_status_snapshot(
        self, miner_id: int, status: str, as_of_date: str, source: str
    ) -> LifecycleStatusSnapshot:
        values = (miner_id, status.strip(), as_of_date.strip(), source.strip())
        cursor = self.connection.execute(
            "INSERT OR IGNORE INTO lifecycle_status_snapshots "
            "(miner_id, status, as_of_date, source) VALUES (?, ?, ?, ?)",
            values,
        )
        self.connection.commit()
        row_id = cursor.lastrowid
        if row_id == 0:
            row_id = self.connection.execute(
                "SELECT id FROM lifecycle_status_snapshots WHERE miner_id = ? AND status = ? "
                "AND as_of_date = ? AND source = ?",
                values,
            ).fetchone()["id"]
        return LifecycleStatusSnapshot(row_id, *values)

    def list_lifecycle_status_history(
        self, miner_id: int
    ) -> list[LifecycleStatusSnapshot]:
        rows = self.connection.execute(
            "SELECT id, miner_id, status, as_of_date, source "
            "FROM lifecycle_status_snapshots WHERE miner_id = ? ORDER BY as_of_date DESC, id DESC",
            (miner_id,),
        ).fetchall()
        return [LifecycleStatusSnapshot(**dict(row)) for row in rows]

    def add_milestone(
        self,
        miner_id: int,
        category: str,
        title: str,
        target_date: str,
        status: str,
        detail: str,
        source: str,
    ) -> Milestone:
        values = (
            miner_id,
            category.strip(),
            title.strip(),
            target_date.strip(),
            status.strip(),
            detail.strip(),
            source.strip(),
        )
        cursor = self.connection.execute(
            "INSERT OR IGNORE INTO milestones "
            "(miner_id, category, title, target_date, status, detail, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            values,
        )
        self.connection.commit()
        row_id = cursor.lastrowid
        if row_id == 0:
            row_id = self.connection.execute(
                "SELECT id FROM milestones WHERE miner_id = ? AND category = ? AND title = ? "
                "AND target_date = ? AND status = ? AND detail = ? AND source = ?",
                values,
            ).fetchone()["id"]
        return Milestone(row_id, *values)

    def list_milestones(self, miner_id: int) -> list[Milestone]:
        rows = self.connection.execute(
            "SELECT id, miner_id, category, title, target_date, status, detail, source "
            "FROM milestones WHERE miner_id = ? ORDER BY target_date, id",
            (miner_id,),
        ).fetchall()
        return [Milestone(**dict(row)) for row in rows]

    def add_market_snapshot(
        self,
        miner_id: int,
        price: float,
        currency: str,
        market_timestamp: str,
        retrieved_at: str,
        source: str,
    ) -> MarketSnapshot:
        values = (
            miner_id,
            price,
            currency.strip().upper(),
            market_timestamp.strip(),
            retrieved_at.strip(),
            source.strip(),
        )
        cursor = self.connection.execute(
            "INSERT INTO market_snapshots "
            "(miner_id, price, currency, market_timestamp, retrieved_at, source) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            values,
        )
        self.connection.commit()
        return MarketSnapshot(cursor.lastrowid, *values)

    def record_market_refresh(
        self,
        miner_id: int,
        share_price: float,
        share_currency: str,
        share_market_timestamp: str,
        shares_outstanding: float,
        commodity_prices: list[tuple[str, float, str, str]],
        exchange_rates: list[tuple[str, str, float]],
        retrieved_at: str,
        source: str,
    ) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO market_snapshots "
                "(miner_id, price, currency, market_timestamp, retrieved_at, source) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    miner_id,
                    share_price,
                    share_currency.strip().upper(),
                    share_market_timestamp.strip(),
                    retrieved_at.strip(),
                    source.strip(),
                ),
            )
            self.connection.execute(
                "INSERT OR IGNORE INTO parameter_snapshots "
                "(miner_id, parameter, value, unit, as_of_date, source) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    miner_id,
                    "basic_shares_outstanding",
                    shares_outstanding,
                    "shares",
                    share_market_timestamp[:10],
                    source.strip(),
                ),
            )
            self.connection.executemany(
                "INSERT INTO commodity_price_snapshots "
                "(commodity, price, currency, unit, market_timestamp, retrieved_at, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        commodity.strip().lower(),
                        price,
                        currency.strip().upper(),
                        "USD/oz",
                        market_timestamp.strip(),
                        retrieved_at.strip(),
                        source.strip(),
                    )
                    for commodity, price, currency, market_timestamp in commodity_prices
                ],
            )
            self.connection.executemany(
                "INSERT INTO exchange_rate_snapshots "
                "(from_currency, to_currency, rate, retrieved_at, source) VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        from_currency.strip().upper(),
                        to_currency.strip().upper(),
                        rate,
                        retrieved_at.strip(),
                        source.strip(),
                    )
                    for from_currency, to_currency, rate in exchange_rates
                ],
            )

    def get_latest_market_snapshot(self, miner_id: int) -> MarketSnapshot | None:
        row = self.connection.execute(
            "SELECT id, miner_id, price, currency, market_timestamp, retrieved_at, source "
            "FROM market_snapshots WHERE miner_id = ? "
            "ORDER BY market_timestamp DESC, id DESC LIMIT 1",
            (miner_id,),
        ).fetchone()
        return MarketSnapshot(**dict(row)) if row else None

    def add_exchange_rate_snapshot(
        self,
        from_currency: str,
        to_currency: str,
        rate: float,
        retrieved_at: str,
        source: str,
    ) -> ExchangeRateSnapshot:
        values = (
            from_currency.strip().upper(),
            to_currency.strip().upper(),
            rate,
            retrieved_at.strip(),
            source.strip(),
        )
        cursor = self.connection.execute(
            "INSERT INTO exchange_rate_snapshots "
            "(from_currency, to_currency, rate, retrieved_at, source) VALUES (?, ?, ?, ?, ?)",
            values,
        )
        self.connection.commit()
        return ExchangeRateSnapshot(cursor.lastrowid, *values)

    def get_latest_exchange_rate(
        self, from_currency: str, to_currency: str
    ) -> ExchangeRateSnapshot | None:
        row = self.connection.execute(
            "SELECT id, from_currency, to_currency, rate, retrieved_at, source "
            "FROM exchange_rate_snapshots WHERE from_currency = ? AND to_currency = ? "
            "ORDER BY retrieved_at DESC, id DESC LIMIT 1",
            (from_currency.strip().upper(), to_currency.strip().upper()),
        ).fetchone()
        return ExchangeRateSnapshot(**dict(row)) if row else None

    def add_commodity_price_snapshot(
        self,
        commodity: str,
        price: float,
        currency: str,
        unit: str,
        market_timestamp: str,
        retrieved_at: str,
        source: str,
    ) -> CommodityPriceSnapshot:
        values = (
            commodity.strip().lower(),
            price,
            currency.strip().upper(),
            unit.strip(),
            market_timestamp.strip(),
            retrieved_at.strip(),
            source.strip(),
        )
        cursor = self.connection.execute(
            "INSERT INTO commodity_price_snapshots "
            "(commodity, price, currency, unit, market_timestamp, retrieved_at, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            values,
        )
        self.connection.commit()
        return CommodityPriceSnapshot(cursor.lastrowid, *values)

    def get_latest_commodity_price(
        self, commodity: str
    ) -> CommodityPriceSnapshot | None:
        row = self.connection.execute(
            "SELECT id, commodity, price, currency, unit, market_timestamp, retrieved_at, source "
            "FROM commodity_price_snapshots WHERE commodity = ? "
            "ORDER BY market_timestamp DESC, id DESC LIMIT 1",
            (commodity.strip().lower(),),
        ).fetchone()
        return CommodityPriceSnapshot(**dict(row)) if row else None

    def set_application_setting(
        self, setting: str, value: str, source: str = "User"
    ) -> ApplicationSettingSnapshot:
        values = (
            setting.strip(),
            value.strip(),
            datetime.now(timezone.utc).isoformat(),
            source.strip(),
        )
        cursor = self.connection.execute(
            "INSERT INTO application_setting_snapshots "
            "(setting, value, changed_at, source) VALUES (?, ?, ?, ?)",
            values,
        )
        self.connection.commit()
        return ApplicationSettingSnapshot(cursor.lastrowid, *values)

    def get_current_application_setting(
        self, setting: str
    ) -> ApplicationSettingSnapshot | None:
        row = self.connection.execute(
            "SELECT id, setting, value, changed_at, source "
            "FROM application_setting_snapshots WHERE setting = ? "
            "ORDER BY changed_at DESC, id DESC LIMIT 1",
            (setting.strip(),),
        ).fetchone()
        return ApplicationSettingSnapshot(**dict(row)) if row else None

    def list_application_setting_history(
        self, setting: str
    ) -> list[ApplicationSettingSnapshot]:
        rows = self.connection.execute(
            "SELECT id, setting, value, changed_at, source "
            "FROM application_setting_snapshots WHERE setting = ? "
            "ORDER BY changed_at DESC, id DESC",
            (setting.strip(),),
        ).fetchall()
        return [ApplicationSettingSnapshot(**dict(row)) for row in rows]

    def add_analysis_scenario(
        self,
        miner_id: int,
        name: str,
        metal_prices_usd: dict[str, float],
        development_risk_factor: float,
    ) -> AnalysisScenario:
        if not name.strip():
            raise ValueError("Scenario name is required")
        if not 0 < development_risk_factor <= 1:
            raise ValueError("development_risk_factor must be greater than zero and at most one")
        normalized_prices = {
            commodity.strip().lower(): float(price)
            for commodity, price in metal_prices_usd.items()
        }
        if any(price <= 0 for price in normalized_prices.values()):
            raise ValueError("Scenario metal prices must be positive")
        values = (
            miner_id,
            name.strip(),
            json.dumps(normalized_prices, sort_keys=True),
            development_risk_factor,
            datetime.now(timezone.utc).isoformat(),
        )
        cursor = self.connection.execute(
            "INSERT INTO analysis_scenarios "
            "(miner_id, name, metal_prices_usd, development_risk_factor, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            values,
        )
        self.connection.commit()
        return AnalysisScenario(
            cursor.lastrowid,
            miner_id,
            name.strip(),
            normalized_prices,
            development_risk_factor,
            values[4],
        )

    def get_analysis_scenario(self, scenario_id: int) -> AnalysisScenario | None:
        row = self.connection.execute(
            "SELECT id, miner_id, name, metal_prices_usd, development_risk_factor, created_at "
            "FROM analysis_scenarios WHERE id = ?",
            (scenario_id,),
        ).fetchone()
        return self._analysis_scenario_from_row(row) if row else None

    def list_analysis_scenarios(self, miner_id: int) -> list[AnalysisScenario]:
        rows = self.connection.execute(
            "SELECT id, miner_id, name, metal_prices_usd, development_risk_factor, created_at "
            "FROM analysis_scenarios WHERE miner_id = ? ORDER BY created_at DESC, id DESC",
            (miner_id,),
        ).fetchall()
        return [self._analysis_scenario_from_row(row) for row in rows]

    @staticmethod
    def _analysis_scenario_from_row(row: sqlite3.Row) -> AnalysisScenario:
        return AnalysisScenario(
            id=row["id"],
            miner_id=row["miner_id"],
            name=row["name"],
            metal_prices_usd=json.loads(row["metal_prices_usd"]),
            development_risk_factor=row["development_risk_factor"],
            created_at=row["created_at"],
        )

    def list_research_entries(self, miner_id: int) -> list[ResearchEntry]:
        rows = self.connection.execute(
            "SELECT id, miner_id, entry_date, note, source, thesis_change, catalyst, open_question "
            "FROM research_entries WHERE miner_id = ? ORDER BY entry_date DESC, id DESC",
            (miner_id,),
        ).fetchall()
        return [ResearchEntry(**dict(row)) for row in rows]

    def add_research_entry(
        self,
        miner_id: int,
        entry_date: str,
        note: str,
        source: str,
        thesis_change: str,
        catalyst: str,
        open_question: str,
    ) -> ResearchEntry:
        values = (
            miner_id,
            entry_date.strip(),
            note.strip(),
            source.strip(),
            thesis_change.strip(),
            catalyst.strip(),
            open_question.strip(),
        )
        cursor = self.connection.execute(
            "INSERT INTO research_entries "
            "(miner_id, entry_date, note, source, thesis_change, catalyst, open_question) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            values,
        )
        self.connection.commit()
        return ResearchEntry(cursor.lastrowid, *values)

    def close(self) -> None:
        self.connection.close()
