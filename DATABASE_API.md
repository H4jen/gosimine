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

The miner catalog is a shared, curated list of available mining-stock listings. It is imported into SQLite from a versioned seed catalog on a new installation. A separate explicit re-population operation imports an updated seed into an existing database.

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

The Yahoo ticker is normalized to uppercase and unique. Trading currency belongs to the listing, not to the application setting. For example, separate `VZLA` and `VZLA.TO` records may use `USD` and `CAD` respectively.

Lifecycle status is a controlled, historical value with an as-of date and source. The current lifecycle status is the newest status snapshot. The initial values are: explorer, developer/permitting, construction, commissioning/ramp-up, producer, expansion, care and maintenance, suspended/distressed, and closed/reclaimed.

### Common Data

Common data is sourced information about the listing or company:

- Company-reported operating and financial values
- Market-data snapshots
- Company releases, reports, and website material
- Commodity and foreign-exchange reference data

Each common record states its source, as-of date, retrieval date when imported, and unit/currency where applicable. Foreign-exchange snapshots record explicit `from_currency` and `to_currency` pairs; `SEK` is not a special persistence currency. Market refresh derives required pairs from the miner's trading currency and the application display preference.

Market data is refreshed only for selected miners through `yfinance`. Each successful refresh appends a market snapshot. Failed refreshes do not remove or replace the latest valid snapshot.

### Milestones

Milestones record dated company events, expected windows, and status changes such as funding, permits, construction, production, or debt maturity. Each record has a category, title, target date or period, status, detail, and source. New information appends a new milestone rather than replacing the prior expectation.

### Personal Data

Personal data is the user's research and interpretation:

- Notes
- Thesis changes
- Catalysts, risks, and open questions
- Personal assumptions
- Saved analysis scenarios
- Later: holdings, entry price, and transactions

Common data never overwrites personal data. The dashboard combines both layers while keeping their origins visible.

Saved analysis scenarios are personal miner records. They preserve a name, commodity-price overrides, development-risk factor, and creation time. They do not alter sourced facts or market snapshots.

### Project Models

A project model is a dated personal or explicitly temporary analytical decomposition of one miner
into attributable projects. Each component records its name, ownership basis, payable-metal
volumes, annual equivalent-metal production, AISC, mine life, and optional compatible resource
and NPV values. The model stores its complete component set and source together as an append-only
snapshot.

The analysis layer may consolidate a project model by summing annual payable volumes and annual
equivalent ounces; using lifetime-production-weighted AISC and mine life; and summing resources or
NPV only when every included project supplies a compatible value. Corporate cash, debt, shares,
and dilution remain separate miner-level inputs. A consolidated result must retain the project
model's source and never be presented as a company-reported value unless the issuer reported it.

### Application Settings

Application settings are personal, global preferences rather than miner data. A setting change appends a snapshot with its timestamp and source. The current setting is the newest snapshot for its registered key. The initial `base_currency` display preference defaults to `SEK` when no user snapshot exists; it does not alter a miner's trading currency.

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
    ticker: str
    primary_commodity: str
    stage: str
    trading_currency: str


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
    price: Decimal
    currency: str
    market_timestamp: datetime | None
    retrieved_at: datetime
    source: str


@dataclass(frozen=True)
class CommodityPriceSnapshot:
    id: int
    commodity: str
    price: Decimal
    currency: str
    unit: str
    market_timestamp: datetime | None
    retrieved_at: datetime
    source: str


@dataclass(frozen=True)
class ExchangeRateSnapshot:
    id: int
    from_currency: str
    to_currency: str
    rate: Decimal
    retrieved_at: datetime
    source: str


@dataclass(frozen=True)
class ApplicationSettingSnapshot:
    id: int
    setting: str
    value: str
    changed_at: datetime
    source: str


@dataclass(frozen=True)
class AnalysisScenario:
    id: int
    miner_id: int
    name: str
    metal_prices_usd: dict[str, Decimal]
    development_risk_factor: Decimal
    created_at: datetime
```

```python
@dataclass(frozen=True)
class AiResearchSnapshot:
    id: int
    miner_id: int
    question: str
    response: str
    citations: tuple[dict[str, object], ...]
    search_queries: tuple[str, ...]
    created_at: datetime
```

The first controlled parameter names are:

- `annual_production_ounces`
- `annual_payable_<metal>_ounces`
- `annual_payable_<metal>_pounds`
- `aisc_per_ounce`
- `mine_life_years`
- `after_tax_npv_usd`
- `after_tax_npv_<currency>`
- `study_metal_price_<metal>_usd_per_ounce`
- `study_discount_rate_percent`
- `cash_usd`
- `cash_<currency>`
- `total_debt_usd`
- `total_debt_<currency>`
- `potential_conversion_shares`
- `potential_dilution_shares`
- `basic_shares_outstanding`

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
    def select_catalog_miner(self, yahoo_ticker: str) -> Miner: ...

    # Miner identity
    def add_miner(...) -> Miner: ...
    def get_miner(self, miner_id: int) -> Miner | None: ...
    def get_miner_by_ticker(self, yahoo_ticker: str) -> Miner | None: ...
    def list_miners(self) -> list[Miner]: ...

    # Personal application preferences
    def set_application_setting(...) -> ApplicationSettingSnapshot: ...
    def get_current_application_setting(
        self, setting: str
    ) -> ApplicationSettingSnapshot | None: ...
    def list_application_setting_history(
        self, setting: str
    ) -> list[ApplicationSettingSnapshot]: ...

    # Historical parameter values
    def add_parameter_snapshot(...) -> ParameterSnapshot: ...
    def list_parameter_history(
        self, miner_id: int, parameter: str | None = None
    ) -> list[ParameterSnapshot]: ...
    def list_current_parameters(self, miner_id: int) -> list[ParameterSnapshot]: ...

    # Personal saved analysis assumptions
    def add_analysis_scenario(...) -> AnalysisScenario: ...
    def get_analysis_scenario(self, scenario_id: int) -> AnalysisScenario | None: ...
    def list_analysis_scenarios(self, miner_id: int) -> list[AnalysisScenario]: ...

    # Dated multi-project analysis inputs
    def add_project_model_snapshot(...) -> ProjectModelSnapshot: ...
    def get_latest_project_model_snapshot(
        self, miner_id: int
    ) -> ProjectModelSnapshot | None: ...

    # Dated company milestones and targets
    def add_milestone(...) -> Milestone: ...
    def list_milestones(self, miner_id: int) -> list[Milestone]: ...

    # Personal research memory
    def add_research_entry(...) -> ResearchEntry: ...
    def list_research_entries(self, miner_id: int) -> list[ResearchEntry]: ...

    # Saved Gemini research; prompt, response, citations, and search queries only
    def add_ai_research_snapshot(...) -> AiResearchSnapshot: ...
    def get_ai_research_snapshot(
        self, snapshot_id: int
    ) -> AiResearchSnapshot | None: ...
    def list_ai_research_snapshots(
        self, miner_id: int
    ) -> list[AiResearchSnapshot]: ...

    # Selected-miner market data
    def add_market_snapshot(...) -> MarketSnapshot: ...
    def record_market_refresh(...) -> None: ...
    def get_latest_market_snapshot(
        self, miner_id: int
    ) -> MarketSnapshot | None: ...

    # Commodity market data shared across miners
    def add_commodity_price_snapshot(...) -> CommodityPriceSnapshot: ...
    def get_latest_commodity_price(
        self, commodity: str
    ) -> CommodityPriceSnapshot | None: ...

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
- Manual parameter entry accepts only controlled parameter names, including the generic `annual_payable_<metal>_ounces` pattern.
- Every record linked to a miner requires that miner to exist.
- Market snapshots append on successful refresh and include source, currency, market timestamp, and retrieval timestamp.
- Commodity-price snapshots append on successful refresh and include the commodity, unit, source, market timestamp, and retrieval timestamp.

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

- Triggers and trigger outcomes
- Commodity-price scenarios
- Documents and website/news ingestion
- Portfolio, broker, and transaction records
