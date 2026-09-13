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

The curated catalog is imported on first launch. Use `python scripts/import_catalog.py` to
explicitly refresh catalog listings in an existing database; it does not remove personal dossiers.

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
