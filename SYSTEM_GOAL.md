# Gosimine System Goal

## Purpose

Gosimine is a local-first desktop workspace for retaining, reviewing, and evolving investment research on mining stocks. Its first responsibility is to act as a reliable external memory: a place where the investor can return to any miner and understand the current case, the evidence behind it, what changed, and what must happen next.

The system is not initially a trading platform, broker terminal, or generic portfolio tracker. It is an instrument-centred research and scenario-analysis system. Portfolio tracking, broker connections, automatic data updates, and document ingestion are planned layers that must not distort the initial design.

## Core Principle: A Miner Is a Durable Dossier

One Gosimine miner record represents one tradeable stock listing. The Yahoo Finance ticker, including its exchange suffix where required, is its identifier. Examples include `GSVR.TO`, `VZLA`, and `FM.TO`.

A company can have multiple listings. The initial version treats each selected listing as a miner record; the model can later introduce a company entity that groups those listings.

The miner dossier is durable. It must preserve prior facts, estimates, sources, and opinions rather than overwrite them. The system should make it possible to answer:

- What did I believe at a given time?
- What evidence supported that belief?
- What changed afterward?
- Did the change strengthen, weaken, or leave the thesis unchanged?

## Initial Miner Information

Each miner begins with identity, classification, and a structured parameter set.

### Identity and Classification

- Company name
- Yahoo Finance ticker
- Exchange and trading currency
- Primary commodity and other revenue-relevant commodities
- Lifecycle status

Lifecycle status describes where the miner is in its operating cycle. The dashboard shows the current status and preserves dated status history. The initial controlled values are:

1. Explorer
2. Developer / permitting
3. Construction
4. Commissioning / ramp-up
5. Producer
6. Expansion
7. Care and maintenance
8. Suspended / distressed
9. Closed / reclaimed

### Investment Parameters

The first analysis parameters reflect the investor's existing comparison framework:

- Metal per share, expressed in ounces
- All-in sustaining cost (AISC) per ounce, in USD
- Annual production or sales volume, in ounces
- Shares outstanding
- Reported AISC per ounce, in USD

These values are not timeless company attributes. Every changing parameter needs an as-of date and source. A value can be entered manually, calculated, or imported, but its origin must remain clear.

### Research Memory

A miner dossier also retains:

- Dated notes and observations
- Source links and references
- Company news, reports, and releases
- Thesis changes
- Catalysts and risks
- Open questions

Research entries form a chronological evidence trail. They should not be replaced merely because newer information exists.

## Dashboard: The Current Investment Picture

Selecting an owned miner opens its dashboard. The dashboard is a decision surface, not a raw database view. It should make the essential current information immediately visible:

- What the company is and what it produces
- The current parameter set and investment case
- Expected value per share and upside
- The current thesis and why the miner is owned
- Recent changes, new evidence, and unresolved questions
- Key risks and upcoming triggers

The timeline remains available as the supporting record behind the dashboard's current view.

The dashboard must allow the investor to add a research note without leaving the miner context. The note can capture its date, source, thesis impact, catalyst, and open question.

### Base Currency and Cases

The user selects a base currency in application settings. It defaults to `SEK`. The dashboard shows calculated operating results in the selected base currency.

Original instrument, source, and commodity currencies remain preserved. Expected value per share and prices are converted into the selected base currency using dated foreign-exchange data, so historical analysis remains traceable.

The dashboard presents two operating cases side by side:

- Current case: the latest stored parameters, current market and foreign-exchange data, and current commodity prices.
- Scenario case: the same model recalculated from the active commodity-price slider assumptions.

Both cases show operating margin and the operating-margin proxy per share in the selected base currency, together with the difference between them.

### V0.1 Operating Scenario

V0.1 assesses a producer through an operating scenario, not through analyst target prices. It uses the reported AISC for the primary metal, or reported silver-equivalent values when the company states both price and AISC on the same silver-equivalent basis.

$$
	ext{Margin per ounce} = \text{Metal price} - \text{AISC per ounce}
$$

$$
	ext{Operating margin proxy} = \text{Production or sales ounces} \times \text{Margin per ounce}
$$

$$
	ext{Operating margin proxy per share} =
\frac{\text{Operating margin proxy}}{\text{Shares outstanding}}
$$

The current case uses the latest metal price. The scenario case replaces that price with the active slider value and may temporarily override AISC. Unsaved changes are discarded when leaving the miner; saving an AISC value creates a dated manual snapshot.

This proxy is not reported net income or EPS. Taxes, interest, general and administrative costs, depreciation, working capital, and other items remain outside the v0.1 calculation. Reported and adjusted EPS from company filings may be stored and displayed separately as sourced historical facts.

Analyst-consensus target-price upside is deferred until a reliable and permitted data source is agreed.

## Triggers and Time

The system tracks the events and conditions that could change the investment case.

A trigger can be:

- A dated event, such as earnings, production results, drill results, resource updates, permits, financing, debt maturities, or operational milestones
- An expected time window, such as `Q4 2026`, `H1 2027`, or a calendar year
- A conditional event, such as a commodity price, AISC, production, dilution, or financing threshold
- A planned review date for reconsidering a parameter or thesis

A trigger stores its expected outcome. After it occurs, the actual outcome and its impact on the thesis are recorded. This turns future expectations into a reviewable investment record.

## Commodity-Price Scenario Analysis

Miner value depends on commodity prices. The dashboard therefore supports interactive commodity-price assumptions.

For each revenue-relevant commodity, the dashboard provides:

- A price slider for rapid scenario testing
- A numeric input for precise values
- A currency and unit
- Reference, base, bull, and bear assumptions

A silver-zinc miner, for example, has both silver and zinc controls. Changing a control updates that commodity's contribution to the analysis, then recalculates total expected value per share and upside.

Moving a slider is temporary scenario exploration. Saving an assumption creates a dated scenario that can be revisited later. Manual assumptions are distinct from historical market data and externally fetched market snapshots.

## Data Sources

Manual entry is the initial foundation. It keeps the system useful without network access and supports values that cannot be reliably fetched.

### Miner Catalog

Gosimine provides a curated catalog of available mining-stock listings so the user can select a miner rather than create every record from scratch. The catalog is built outside the desktop application by a repeatable maintenance script, using exchange listing directories and other verifiable mining-industry sources.

The script is run once to create the initial catalog and again when a catalog update is needed. It produces a reviewable, versioned seed catalog that new installations import into their local database. The desktop application does not automatically build or update the catalog in the initial version.

Catalog updates add or correct listings without deleting a user's miner dossier, research, assumptions, or history. Inactive and delisted listings are retained with their status recorded rather than removed.

Yahoo Finance, through the Python `yfinance` module, is the market-data adapter for selected miners. It validates and enriches a known Yahoo ticker; it does not build the miner catalog.

Each refresh creates dated market and foreign-exchange snapshots containing the value, currency pair where applicable, market timestamp, retrieval timestamp, and source attribution. The dashboard uses the latest valid snapshots. A failed refresh preserves the last valid snapshot and makes its age visible. Initial updates are started manually from the application; scheduled updates are deferred.

`yfinance` is an unofficial Yahoo interface. The system must tolerate unavailable fields, ticker changes, rate limits, and failed requests.

Imported data remains attributed to its source and timestamp. It must not silently overwrite manual research or past analysis assumptions.

## Future Expansion

The system is designed to grow around the miner dossier without redesigning its core purpose.

### Portfolio and Broker Data

A later portfolio layer will add accounts, transactions, positions, entry prices, cash movements, and cost basis. Broker integration should initially be read-only: it imports or reconciles transaction data. Gosimine remains able to function through manual records when broker APIs are unavailable.

### Automated Updates and Ingestion

Later capabilities may include:

- Scheduled market-data updates
- Company newsletter or email ingestion
- Website release and report collection
- News and document storage
- Extracted facts linked to the original source

### Analysis Outputs

Later analysis can compare miners, calculate portfolio exposure, rank scenarios, and surface upcoming triggers. These outputs must remain traceable to the parameters, assumptions, and sources that produced them.

## Design Constraints

- Local-first: the core dossier and manual workflow work without a network connection.
- Historical: changing facts and opinions retain their dates and sources.
- Classified: lifecycle status is a controlled, dated, sourced value.
- Traceable: derived outputs identify the assumptions and data behind them.
- Honest calculation: derived outputs are unavailable when required inputs are missing and display their source data, units, currencies, and dates.
- Resilient updates: failed external refreshes preserve the most recent valid data.
- Incremental: external integrations add capability without becoming prerequisites.
- Focused: the first version prioritizes capturing and reviewing miner knowledge over broad portfolio or automation features.

## First Implementation

The first implementation is a complete vertical slice for one manually selected miner. It proves the dossier, data history, manual refresh, and dashboard calculation before catalog selection or multiple-miner support are generalized.

It includes the miner's identity, lifecycle status, AISC, annual production, shares outstanding, sources, dated research history, and manual `yfinance` refresh for share price, primary-metal price, and foreign exchange. The dashboard shows current and slider-based operating scenarios.
