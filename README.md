# Gosimine

A local-first Windows desktop workspace for remembering, reviewing, and evolving mining-company research.

## Setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
gosimine
```

Data is stored locally in `data/gosimine.sqlite3`.

The installed `pypdf` dependency supports local text extraction from company reports during
research; it does not modify the original PDF.

The curated catalog is imported on first launch. Use `python scripts/import_catalog.py` to
explicitly refresh catalog listings in an existing database; it does not remove personal dossiers.

## Adding Miners

Add one row per listing to `seed/miner_intake.csv`. It opens directly in Excel, LibreOffice, or
Google Sheets. Each row must contain the identity fields (`ticker`, `name`,
`trading_currency`, `primary_commodity`, and `stage`), lifecycle status with date and source,
and the minimum analysis inputs: `annual_production_ounces`, `aisc_per_ounce`,
`basic_shares_outstanding`, and at least one
`annual_payable_<metal>_ounces` column. It also requires
`mine_life_years`, resource values, NPV, study assumptions, cash, debt, and dilution values when
they are available. Blank optional values are omitted from the generated seed, allowing an
incomplete company disclosure to enter the catalog. Set the matching `_currency` field for each
NPV, cash, and debt value to the three-letter currency used in the company report; for example,
`cash_cad` is generated from `cash` with `cash_currency` set to `CAD`. Use
`potential_conversion_shares` only for a convertible instrument; use
`potential_dilution_shares` for warrants, options, and RSUs. Include study metal-price columns
for disclosed assumptions when available.
To avoid repeating URLs, provenance is grouped into five date/source pairs:
`project_study`, `resource`, `financial`, `dilution`, and `shares`. The builder stamps each
generated parameter with its group's source and `YYYY-MM-DD` as-of date. A blank source is
stored as `Source missing`; dates and values remain required, and values must be positive.
`project_study_as_of_date` and `dilution_as_of_date` are optional. When blank, they are stored
as `1900-01-01` so the required database date field remains valid.

Run the explicit builder to create one JSON seed file per miner and validate each listing against
live Yahoo Finance quote, currency, and share-count data:

```powershell
python scripts/build_seed.py --verify-yahoo
```

The command writes files such as `seed/miners/TSK_V.json`. It normalizes ticker and currency
codes, rejects incomplete, invalid, or duplicate rows, and skips existing miner files without
overwriting their researched data. Market and commodity prices are refreshed separately at runtime.
Then refresh the catalog in an existing local database:

```powershell
python scripts/import_catalog.py
```

The app reads the reviewed `seed/miners/` directory. It does not process `miner_intake.csv`
automatically at launch.

## Gemini Research Questions

Select a miner and use `Ask Gemini` or `Complete analysis` to submit research with Google Search
grounding. The request includes the selected listing's current sourced parameters, personal
research entries, and derived Gosimine analysis outputs. Gemini returns a report in a separate
window, and completed reports are saved as separate research snapshots without changing dossier
facts or personal research entries. Links in a report open in the system's default browser.

Gosimine obtains the API key in this order: the operating system credential vault, then
`GEMINI_API_KEY` only when a credential vault is unavailable, then a masked session-only prompt.
It never writes the key to SQLite or project files. Use a Gemini API key restricted to the Gemini
API. Install the updated project dependencies before using this feature.

## Investment Disclaimer

Gosimine is a research and scenario-analysis tool, not investment advice, a recommendation,
or a solicitation to buy or sell any security. Market data, company disclosures, and calculated
outputs may be incomplete, inaccurate, or outdated. You are solely responsible for your own
investment decisions and should obtain independent professional advice where appropriate.

## License

Gosimine is available under the MIT License. See [LICENSE](LICENSE).

## Initial scope

- Browse a curated miner catalog and retain selected listings as personal dossiers.
- Store dated, sourced company facts, market snapshots, research history, milestones, and scenarios.
- Compare current and commodity-price scenario values using the same generic model.
