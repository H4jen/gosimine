# Gosimine Database API

## Purpose

The database is Gosimine's durable source of truth. It stores miner records, sourced facts, personal research, and saved assumptions independently of the PySide6 application.

The user interface does not execute SQL or decide how records are stored. It requests typed records from the database and submits validated user intent back to it.

```text
PySide6 UI -> application logic -> Database -> SQLite
SQLite -> Database -> typed records -> application logic -> PySide6 UI
```

Derived analysis is outside the database. It uses database records as inputs and returns calculated results to the dashboard.

## Data Ownership

All data belongs to one miner, identified by a Yahoo Finance ticker.

### Miner Catalog

The miner catalog is a shared, curated list of available mining-stock listings. It is imported into SQLite from a versioned seed catalog on a new installation.

Catalog records store the listing's identity and classification: name, Yahoo ticker, exchange, trading currency, commodities, status, source, and catalog version. Catalog data is maintained outside the desktop application by a repeatable script and is reviewed before publication.

The catalog is distinct from personal miner memory. Selecting a catalog listing creates or links a personal dossier. Catalog updates add or correct listings without deleting personal research or removing a previously selected miner.

### Miner

A miner represents one tradeable stock listing, not necessarily the underlying company. The Yahoo ticker is its canonical identifier and includes its exchange suffix where required, such as `GSVR.TO`.

A miner stores stable identity and classification:

- Name
- Yahoo ticker
- Exchange
- Trading currency
- Primary commodity
- Lifecycle status

The Yahoo ticker is normalized to uppercase and unique.

Lifecycle status is a controlled, historical value with an as-of date and source. The current lifecycle status is the newest status snapshot. The initial values are: explorer, developer/permitting, construction, commissioning/ramp-up, producer, expansion, care and maintenance, suspended/distressed, and closed/reclaimed.

### Common Data

Common data is sourced information about the listing or company:

- Company-reported operating and financial values
- Market-data snapshots
- Company releases, reports, and website material
- Commodity and foreign-exchange reference data

Each common record states its source, as-of date, retrieval date when imported, and unit/currency where applicable.

Market data is refreshed only for selected miners through `yfinance`. Each successful refresh appends a market snapshot. Failed refreshes do not remove or replace the latest valid snapshot.

### Personal Data

Personal data is the user's research and interpretation:

- Notes
- Thesis changes
- Catalysts, risks, and open questions
- Personal assumptions
- Saved analysis scenarios
- Later: holdings, entry price, and transactions

Common data never overwrites personal data. The dashboard combines both layers while keeping their origins visible.

### Derived Data

Derived data is calculated, not source truth:

- Expected value per share
- Operating margin proxy per share in the selected base currency
- Commodity-price sensitivity
- Difference between current and scenario cases

Calculation code reads stored inputs and returns a result. It does not silently modify source records. A user may explicitly save an analysis scenario or result as a dated personal record.

## Initial Records

```python
@dataclass(frozen=True)
class Miner:
    id: int
    name: str
    yahoo_ticker: str
    primary_commodity: str
    status: str


@dataclass(frozen=True)
class ParameterSnapshot:
    id: int
    miner_id: int
    parameter: str
    value: Decimal
    unit: str
    as_of_date: date
    source: str


@dataclass(frozen=True)
class ResearchEntry:
    id: int
    miner_id: int
    entry_date: date
    note: str
    source: str
    thesis_change: str
    catalyst: str
    open_question: str


@dataclass(frozen=True)
class MarketSnapshot:
    id: int
    miner_id: int
    price: Decimal
    currency: str
    market_timestamp: datetime | None
    retrieved_at: datetime
    source: str
```

The first controlled parameter names are:

- `annual_production_ounces`
- `aisc_per_ounce`
- `shares_outstanding`
- `tax_rate`
- `lifecycle_status`

The parameter list may grow only through an intentional schema and API decision. Free-form notes belong in research entries rather than arbitrary parameter names.

## Public API

The initial API maps directly to the first user workflows.

```python
class Database:
    def close(self) -> None: ...

    # Curated miner catalog
    def import_catalog(self, catalog: Catalog) -> CatalogImportResult: ...
    def list_catalog_miners(
        self, query: str | None = None
    ) -> list[CatalogMiner]: ...
    def get_catalog_miner_by_ticker(
        self, yahoo_ticker: str
    ) -> CatalogMiner | None: ...

    # Miner identity
    def add_miner(...) -> Miner: ...
    def get_miner(self, miner_id: int) -> Miner | None: ...
    def get_miner_by_ticker(self, yahoo_ticker: str) -> Miner | None: ...
    def list_miners(self) -> list[Miner]: ...

    # Historical parameter values
    def add_parameter_snapshot(...) -> ParameterSnapshot: ...
    def list_parameter_history(
        self, miner_id: int, parameter: str | None = None
    ) -> list[ParameterSnapshot]: ...
    def list_current_parameters(self, miner_id: int) -> list[ParameterSnapshot]: ...

    # Personal research memory
    def add_research_entry(...) -> ResearchEntry: ...
    def list_research_entries(self, miner_id: int) -> list[ResearchEntry]: ...

    # Selected-miner market data
    def add_market_snapshot(...) -> MarketSnapshot: ...
    def get_latest_market_snapshot(
        self, miner_id: int
    ) -> MarketSnapshot | None: ...

    def add_exchange_rate_snapshot(...) -> ExchangeRateSnapshot: ...
    def get_latest_exchange_rate(
        self, from_currency: str, to_currency: str
    ) -> ExchangeRateSnapshot | None: ...
```

The names express intent. The UI asks for the current parameter set or research history; it does not assemble SQL queries or interpret database rows.

## Historical Rules

- Miner identity may be corrected through an explicit update API when needed.
- Changing parameter values append new snapshots; they do not overwrite prior values.
- Research entries append to history. Corrections should be represented deliberately rather than silently replacing past thinking.
- Current parameters are the newest snapshot for each parameter, ordered by as-of date and then record ID.
- Research entries list newest first, ordered by entry date and then record ID.
- Every parameter snapshot requires a value, unit, as-of date, and non-empty source.
- Every record linked to a miner requires that miner to exist.
- Market snapshots append on successful refresh and include source, currency, market timestamp, and retrieval timestamp.

## Persistence Requirements

- Use SQLite with foreign keys enabled.
- Use parameterized queries exclusively.
- Commit each successful write explicitly.
- Return typed dataclasses from public methods, never SQLite rows or cursors.
- Keep schema changes backward-compatible with existing local databases.
- Catalog import is additive and corrective. It never deletes a personal miner dossier or its linked records.
- Preserve inactive or delisted catalog listings and record their status.
- Use temporary SQLite databases for tests. Never use `data/gosimine.sqlite3` during tests.
- Keep database code free of PySide6 imports, widget state, network calls, and calculation rules.

## Dashboard Read Model

The dashboard requests separate records, then combines them outside the database:

```text
Miner
+ current common parameters
+ personal research entries
+ market and FX snapshots
+ later: personal assumptions and scenarios
= dashboard inputs
```

Analysis code converts those inputs into current and scenario cases. The dashboard renders the result and labels common, personal, and derived information clearly.

## Deferred API

These APIs are intentionally deferred until their user workflows are agreed:

- Settings and base currency
- Triggers and trigger outcomes
- Commodity-price scenarios
- Documents and website/news ingestion
- Portfolio, broker, and transaction records
