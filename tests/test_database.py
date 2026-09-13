from pathlib import Path

import pytest

from gosimine.database import Database
from gosimine.seed import initialize_database, populate_database


def test_add_and_list_miners(tmp_path: Path) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")

    added = database.add_miner("Aurora Gold", "aug", "Gold", "Producer")

    assert database.list_miners() == [
        type(added)(added.id, "Aurora Gold", "AUG", "Gold", "Producer", "USD")
    ]
    database.close()


def test_add_miner_rejects_duplicate_ticker(tmp_path: Path) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    database.add_miner("Aurora Gold", "aug", "Gold", "Producer")

    with pytest.raises(ValueError, match="AUG"):
        database.add_miner("Aurora Gold Duplicate", "AUG", "Gold", "Producer")

    database.close()


def test_catalog_search_and_selection_preserve_personal_dossiers(tmp_path: Path) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    existing = database.add_miner("Aurora Gold", "AUG", "Gold", "Producer")
    database.add_research_entry(
        existing.id, "2026-09-12", "Keep this note", "Manual", "", "", ""
    )
    database.import_catalog(
        [
            {
                "name": "Vizsla Silver",
                "ticker": "VZLA",
                "primary_commodity": "Silver",
                "stage": "Developer / permitting",
                "trading_currency": "USD",
            },
            {
                "name": "Frontier Mining",
                "ticker": "FMT.TO",
                "primary_commodity": "Gold",
                "stage": "Explorer",
                "trading_currency": "CAD",
            },
        ]
    )

    assert [record.ticker for record in database.list_catalog_miners("silver")] == ["VZLA"]
    assert database.get_catalog_miner_by_ticker("vzla") is not None
    selected = database.select_catalog_miner("vzla")

    assert selected.ticker == "VZLA"
    assert database.select_catalog_miner("VZLA") == selected
    assert database.list_research_entries(existing.id)[0].note == "Keep this note"
    assert [miner.ticker for miner in database.list_miners()] == ["AUG", "VZLA"]
    database.close()


def test_add_and_list_research_entries_newest_first(tmp_path: Path) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Aurora Gold", "aug", "Gold", "Producer")

    first = database.add_research_entry(
        miner.id,
        "2026-09-01",
        "Drill results extended mineralization.",
        "https://example.com/news-release",
        "Higher confidence in resource growth.",
        "Updated resource estimate.",
        "What is the expected grade profile?",
    )
    second = database.add_research_entry(
        miner.id,
        "2026-09-10",
        "Management increased exploration budget.",
        "Investor presentation",
        "",
        "Winter drilling program.",
        "Will dilution be needed?",
    )

    assert database.list_research_entries(miner.id) == [second, first]
    database.close()


def test_import_miner_seed_is_idempotent(tmp_path: Path) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    record = {
        "name": "Vizsla Silver",
        "ticker": "vzla",
        "primary_commodity": "Silver",
        "stage": "Developer / permitting",
        "lifecycle_status": {
            "value": "Developer / permitting",
            "as_of_date": "2025-11-12",
            "source": "https://example.com/vzla-feasibility-study",
        },
        "parameters": [
            {
                "name": "annual_production_ounces",
                "value": 17383000,
                "unit": "AgEq oz/year",
                "as_of_date": "2025-11-12",
                "source": "https://example.com/vzla-feasibility-study",
            },
            {
                "name": "aisc_per_ounce",
                "value": 10.61,
                "unit": "USD/AgEq oz",
                "as_of_date": "2025-11-12",
                "source": "https://example.com/vzla-feasibility-study",
            },
        ],
    }

    miner = database.import_miner_seed(record)
    database.import_miner_seed(record)

    assert database.list_miners() == [
        type(miner)(
            miner.id, "Vizsla Silver", "VZLA", "Silver", "Developer / permitting", "USD"
        )
    ]
    assert len(database.list_parameter_history(miner.id)) == 2
    assert len(database.list_lifecycle_status_history(miner.id)) == 1
    database.close()


def test_list_current_parameters_keeps_latest_snapshot_per_parameter(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Aurora Gold", "aug", "Gold", "Producer")

    database.add_parameter_snapshot(
        miner.id, "aisc_per_ounce", 1200, "USD/oz", "2026-01-01", "Old report"
    )
    latest_aisc = database.add_parameter_snapshot(
        miner.id, "aisc_per_ounce", 1100, "USD/oz", "2026-03-01", "New report"
    )
    annual_production = database.add_parameter_snapshot(
        miner.id,
        "annual_production_ounces",
        100000,
        "oz/year",
        "2026-02-01",
        "Guidance",
    )

    assert database.list_current_parameters(miner.id) == [latest_aisc, annual_production]
    database.close()


def test_list_lifecycle_status_history_is_newest_first(tmp_path: Path) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Aurora Gold", "aug", "Gold", "Explorer")

    first = database.add_lifecycle_status_snapshot(
        miner.id, "Explorer", "2025-01-01", "Technical report"
    )
    second = database.add_lifecycle_status_snapshot(
        miner.id, "Developer / permitting", "2026-01-01", "Permit application"
    )

    assert database.list_lifecycle_status_history(miner.id) == [second, first]
    database.close()


def test_parameter_snapshot_requires_existing_miner(tmp_path: Path) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")

    with pytest.raises(__import__("sqlite3").IntegrityError):
        database.add_parameter_snapshot(
            999,
            "aisc_per_ounce",
            10.61,
            "USD/AgEq oz",
            "2025-11-12",
            "Feasibility study",
        )

    database.close()


def test_initialize_database_imports_vzla_seed_idempotently(tmp_path: Path) -> None:
    database_path = tmp_path / "gosimine.sqlite3"
    seed_path = Path(__file__).parents[1] / "seed" / "miners.json"

    initialize_database(database_path, seed_path)
    initialize_database(database_path, seed_path)

    database = Database(database_path)
    catalog_miner = database.list_catalog_miners("VZLA")[0]

    assert catalog_miner.name == "Vizsla Silver"
    assert catalog_miner.trading_currency == "USD"
    assert database.list_miners() == []
    miner = database.select_catalog_miner("VZLA")
    parameters = {
        snapshot.parameter: snapshot
        for snapshot in database.list_current_parameters(miner.id)
    }
    assert parameters["study_metal_price_silver_usd_per_ounce"].value == 35.5
    assert parameters["study_metal_price_gold_usd_per_ounce"].value == 3100
    assert parameters["study_discount_rate_percent"].value == 5
    assert "vizslasilvercorp.com" in parameters["after_tax_npv_usd"].source
    database.close()


def test_milestones_are_sorted_by_target_date_and_id(tmp_path: Path) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Aurora Gold", "AUG", "Gold", "Developer")
    later = database.add_milestone(
        miner.id, "Production", "First gold", "2027-H1", "Planned", "", "Company release"
    )
    earlier = database.add_milestone(
        miner.id, "Permitting", "Permit decision", "2026-H2", "Planned", "", "Company release"
    )

    assert database.list_milestones(miner.id) == [earlier, later]
    database.close()


def test_initialize_database_preserves_an_existing_database(tmp_path: Path) -> None:
    database_path = tmp_path / "gosimine.sqlite3"
    seed_path = Path(__file__).parents[1] / "seed" / "miners.json"
    database = Database(database_path)
    database.add_miner("Aurora Gold", "AUG", "Gold", "Producer")
    database.close()

    initialize_database(database_path, seed_path)

    database = Database(database_path)
    assert [miner.ticker for miner in database.list_miners()] == ["AUG"]
    database.close()


def test_populate_database_adds_seed_without_removing_existing_research(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "gosimine.sqlite3"
    seed_path = Path(__file__).parents[1] / "seed" / "miners.json"
    database = Database(database_path)
    miner = database.add_miner("Aurora Gold", "AUG", "Gold", "Producer")
    database.add_research_entry(
        miner.id, "2026-09-11", "Keep this note", "Manual", "", "", ""
    )
    database.close()

    populate_database(database_path, seed_path)

    database = Database(database_path)
    assert [miner.ticker for miner in database.list_miners()] == ["AUG"]
    assert [miner.ticker for miner in database.list_catalog_miners()] == ["VZLA"]
    assert len(database.list_research_entries(miner.id)) == 1
    database.close()


def test_store_and_get_latest_market_and_exchange_rate_snapshots(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Vizsla Silver", "VZLA", "Silver", "Developer")

    first_price = database.add_market_snapshot(
        miner.id,
        3.97,
        "USD",
        "2026-09-11T20:00:00+00:00",
        "2026-09-12T10:00:00+00:00",
        "Yahoo Finance",
    )
    latest_price = database.add_market_snapshot(
        miner.id,
        4.10,
        "USD",
        "2026-09-12T20:00:00+00:00",
        "2026-09-12T21:00:00+00:00",
        "Yahoo Finance",
    )
    exchange_rate = database.add_exchange_rate_snapshot(
        "USD", "SEK", 10.45, "2026-09-12T21:00:00+00:00", "Yahoo Finance"
    )

    assert database.get_latest_market_snapshot(miner.id) == latest_price
    assert first_price != latest_price
    assert database.get_latest_exchange_rate("USD", "SEK") == exchange_rate
    database.close()


def test_application_settings_keep_current_value_and_history(tmp_path: Path) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")

    first = database.set_application_setting("base_currency", "SEK")
    latest = database.set_application_setting("base_currency", "USD")

    assert database.get_current_application_setting("base_currency") == latest
    assert database.list_application_setting_history("base_currency") == [latest, first]
    database.close()


def test_analysis_scenario_preserves_personal_assumptions(tmp_path: Path) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Aurora Gold", "AUG", "Gold", "Developer")

    scenario = database.add_analysis_scenario(
        miner.id, "Higher metals", {"gold": 4_500, "silver": 70}, 0.8
    )

    assert database.get_analysis_scenario(scenario.id) == scenario
    assert database.list_analysis_scenarios(miner.id) == [scenario]
    database.close()
