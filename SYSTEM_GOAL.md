
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
- Share price in the listing's trading currency, lifecycle stage, and primary commodity
- The investment case as per-share values, ratios, and multiples
- Key risks, funding status, and upcoming triggers
- The current thesis, recent evidence, and unresolved questions

The timeline remains available as the supporting record behind the dashboard's current view.

The dashboard must allow the investor to add a research note without leaving the miner context. The note can capture its date, source, thesis impact, catalyst, and open question.

### Dashboard Detail and Model Inputs

The default dashboard is deliberately simple. It shows decision outputs rather than every underlying input. For a developer such as VZLA, the primary results are:

- Current share price
- Lifecycle stage
- Annual and lifetime equivalent-metal ounces per share
- Margin per equivalent-metal ounce
- Annual margin per share
- Lifetime undiscounted margin per share and its factor relative to the share price
- Total resource ounces per share and a separately labelled speculative resource-margin factor
- Project NPV per share and price-to-NPV
- Risked NPV per share and price-to-risked-NPV when a risk assumption exists
- Funding gap, expected dilution, first-production target, and principal risk when available

Inputs remain accessible through a collapsed `Model inputs` panel. It is closed by default and groups values into:

- Market inputs: share price, commodity prices, FX, and share count
- Study or operating inputs: production, mine life, AISC, CAPEX, NPV, and discount rate
- Scenario inputs: commodity-price and risk assumptions

Every input row displays its value, unit, as-of date, and source. An investor can expand this panel to verify any result, and an input control opens the relevant dated snapshot for review or manual replacement. Derived results do not silently change source data.

Every analysis metric provides an in-app explanation of its calculation, scope, and limitations. A study-derived NPV also retains the disclosed study metal-price and discount-rate assumptions as separate sourced snapshots. Current-price operating scenarios remain distinct from these study assumptions.

The dashboard supports manual entry of controlled model inputs. A manual entry requires a parameter name, numeric value, unit, as-of date, and source, then appends a dated snapshot rather than replacing an existing fact. Supported names include the standard model parameters and the generic `annual_payable_<metal>_ounces` pattern.

The dashboard also supports a controlled lifecycle-status update. It uses the defined lifecycle values and appends a dated snapshot with its source, preserving prior stages for later review.

### General Calculation Engine

Gosimine uses one calculation engine for every miner. The engine does not contain company-specific logic, hard-coded tickers, or embedded research values. It accepts a miner's stored inputs, including attributable payable metal volumes, equivalent-ounce basis, AISC, mine life, share count, market prices, and study values, then returns the same standard per-share results and ratios.

Each miner differs through its dated, sourced input parameters only. A silver-gold developer, a multi-metal producer, and a gold explorer may have different available inputs and therefore different applicable outputs, but they use the same calculation contract. An output remains unavailable when its required inputs are missing.

### Currency Scopes and Cases

Currency has four explicit scopes:

- **Listing trading currency:** A sourced property of each miner listing. Share price and per-share valuation outputs display in this currency. For example, `VZLA.TO` uses `CAD`; NYSE American `VZLA` uses `USD`.
- **Application display currency:** A personal setting, initially `SEK`, for future portfolio totals and cross-miner comparisons. It may be changed without changing a miner's listing currency or any sourced fact.
- **Source currency:** The currency in which a company, market, or commodity source reported a fact. Model Inputs always retain this original currency.
- **FX pair currency:** Each FX snapshot is an explicit `from_currency` and `to_currency` pair. No currency, including `SEK`, is a permanent system bridge.

Ratios such as price-to-NAV are currency-neutral when both values use the same listing currency. A required conversion uses dated FX snapshots; if no valid path exists, the converted output remains unavailable rather than implying a rate.

Market refresh derives its FX pairs from the selected listing and the application display currency. For example, a `CAD` listing with `AUD` selected stores `USD/CAD` for USD-native study values and `CAD/AUD` for later cross-listing display. Changing the application display currency changes the required refresh pair; it never redefines a miner's listing currency.

Application settings are personal preferences, separate from sourced miner facts and analysis scenarios. Each change appends a dated setting snapshot, so the current value and its history remain available. The initial setting is `base_currency`; additional settings require a registered key, default, type, and allowed values.

V0.1 analysis remains USD-native for study inputs. It converts a listing quote to USD before calculating ratios and converts USD-derived per-share values to the miner's listing trading currency for presentation.

### Dilution Cases

V0.1 keeps the basic-share case as the primary valuation view. A temporary dilution scenario may add investor-entered shares to show the resulting equity NAV and risked NAV per share. Where a sourced convertible instrument provides a potential conversion-share count, the dashboard also shows an illustrative full-conversion denominator. It retains the basic-case debt treatment and excludes capped-call or settlement effects unless their economics are explicitly modelled.

The dashboard presents two operating cases side by side:

- Current case: the latest stored parameters, current market and foreign-exchange data, and current commodity prices.
- Scenario case: the same model recalculated from the active commodity-price slider assumptions.

Both cases show operating margin in its source currency and per-share values in the listing trading currency, together with the difference between them.

### V0.1 Operating Scenario

V0.1 assesses a producer through an operating scenario, not through analyst target prices. It uses the reported AISC for the primary metal, or reported silver-equivalent values when the company states both price and AISC on the same silver-equivalent basis.

$$
	ext{Margin per ounce} = \text{Metal price} - \text{AISC per ounce}
$$

$$
	ext{Operating margin} = \text{Production or sales ounces} \times \text{Margin per ounce}
$$

$$
	ext{Operating margin per share} =
\frac{\text{Operating margin}}{\text{Shares outstanding}}
$$

The current case uses the latest metal price. The scenario case replaces that price with the active slider value and may temporarily override AISC. Unsaved changes are discarded when leaving the miner; saving an AISC value creates a dated manual snapshot.

This calculation is not reported net income or EPS. Taxes, interest, general and administrative costs, depreciation, working capital, and other items remain outside the v0.1 calculation. Reported and adjusted EPS from company filings may be stored and displayed separately as sourced historical facts.

Analyst-consensus target-price upside is deferred until a reliable and permitted data source is agreed.

## Triggers and Time

The system tracks the events and conditions that could change the investment case.

A trigger can be:

- A dated event, such as earnings, production results, drill results, resource updates, permits, financing, debt maturities, or operational milestones
- An expected time window, such as `Q4 2026`, `H1 2027`, or a calendar year
- A conditional event, such as a commodity price, AISC, production, dilution, or financing threshold
- A planned review date for reconsidering a parameter or thesis

A trigger stores its expected outcome. After it occurs, the actual outcome and its impact on the thesis are recorded. This turns future expectations into a reviewable investment record.

V0.1 stores these as dated milestones with a category, title, target date or period, status, detail, and source. The dashboard shows the current milestone list, including company-reported funding status and planned construction or production targets. Later updates append a new milestone; they do not erase the original expectation.

## Commodity-Price Scenario Analysis

Miner value depends on commodity prices. The dashboard therefore supports interactive commodity-price assumptions.

For each revenue-relevant commodity, the dashboard provides:

- A price slider for rapid scenario testing
- A numeric input for precise values
- A currency and unit
- Reference, base, bull, and bear assumptions

A silver-zinc miner, for example, has both silver and zinc controls. Changing a control updates that commodity's contribution to the analysis, then recalculates total expected value per share and upside.

Moving a slider is temporary scenario exploration. Saving an assumption creates a dated scenario that can be revisited later. Manual assumptions are distinct from historical market data and externally fetched market snapshots.

V0.1 saved scenarios belong to one miner and store a user-supplied name, payable-metal prices in USD, and the development-risk factor. Loading a scenario restores those temporary controls; it never changes sourced parameters, market snapshots, or company facts.

## Data Sources

Manual entry is the initial foundation. It keeps the system useful without network access and supports values that cannot be reliably fetched.

### Miner Catalog

Gosimine provides a curated catalog of available mining-stock listings so the user can select a miner rather than create every record from scratch. The catalog is built outside the desktop application by a repeatable maintenance script, using exchange listing directories and other verifiable mining-industry sources.

On first launch, the desktop application imports the seed catalog only when it creates a new local database. The main window provides a searchable catalog browser; opening a listing creates a personal dossier while leaving the catalog independent. The `scripts/import_catalog.py` maintenance script explicitly re-imports the seed catalog into an existing database when catalog data has been updated. The desktop application does not automatically refresh the catalog after first launch in the initial version.

Catalog updates add or correct listings without deleting a user's miner dossier, research, assumptions, or history. Inactive and delisted listings are retained with their status recorded rather than removed.

Yahoo Finance, through the Python `yfinance` module, is the market-data adapter for selected miners. It validates and enriches a known Yahoo ticker; it does not build the miner catalog.

Each refresh gathers all required quotes before it writes dated market and foreign-exchange snapshots containing the value, currency pair where applicable, market timestamp, retrieval timestamp, and source attribution. Completed refreshes are persisted atomically. The dashboard uses the latest valid snapshots. A failed refresh preserves the last valid snapshot and makes its age visible. Initial updates are started manually from the application; scheduled updates are deferred.

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

### AI-Assisted Miner Refresh

AI-assisted refresh is a later ingestion layer. The investor refreshes a selected miner through one clear dashboard action. Once a preferred AI provider is connected, it fetches the latest miner-specific news, company disclosures, and material information. Source gathering, ticker-scoped context construction, fact extraction, validation, and snapshot storage happen behind that action while the application reports the resulting updates and any exceptions.

The workflow must be seamless and low-friction: the investor does not assemble prompts, copy data between tools, or manage database records. The selected miner alone determines the context, which contains relevant company disclosures, recent news and material events, current stored inputs, and unresolved questions.

The AI returns structured candidate updates rather than SQL or unstructured database writes. Each candidate includes the parameter name, value, unit, as-of date, source URL, supporting source quote, confidence, and reason for change. The application validates the candidate's type, units, dates, and source before it is accepted.

Accepted updates append dated snapshots to SQLite. They never silently overwrite existing facts, personal research, or prior analysis. The dashboard continues to calculate only from stored records, so AI-extracted data and manually entered data share the same traceable persistence model.

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
