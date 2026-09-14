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

overwriting their researched data. Market and commodity prices are refreshed separately at runtime.
`seed/miners/*.json` is the canonical, reviewed miner-seed format. It supports complete dossier
sources and dated multi-project models, which cannot be represented faithfully in a single CSV
row. Add or revise miner dossiers directly in JSON and validate their structure and behaviour with
the test suite.

`seed/miner_intake.csv` and `scripts/build_seed.py` are obsolete legacy intake tools retained for
historical reference. Do not use them for new or updated dossiers. A future export may generate a
human-readable CSV or Markdown review artifact from the canonical JSON seeds.

Refresh the catalog in an existing local database:

```powershell
python scripts/import_catalog.py
```

The app reads the reviewed `seed/miners/` directory. It never processes `miner_intake.csv` at
launch.

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
