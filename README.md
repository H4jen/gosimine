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

## Initial scope

- Maintain a searchable miner watchlist.
- Store current company details locally in SQLite.
- Build timestamped research history and source tracking next.
