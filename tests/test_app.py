import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QLabel,
    QPushButton,
    QTableWidget,
    QTabWidget,
)

from gosimine.app import HistoryDialog, MainWindow, MinerDashboard, SettingsDialog
from gosimine.database import Database
from gosimine.seed import initialize_database


def select_seeded_vzla(database: Database):
    return database.select_catalog_miner("VZLA")


def test_main_window_selects_a_catalog_miner(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "gosimine.sqlite3"
    seed_path = Path(__file__).parents[1] / "seed" / "miners.json"
    initialize_database(database_path, seed_path)
    database = Database(database_path)

    class AcceptedCatalogDialog:
        selected_ticker = "VZLA"

        def __init__(self, supplied_database, parent) -> None:
            assert supplied_database is database

        def exec(self) -> QDialog.DialogCode:
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr("gosimine.app.CatalogDialog", AcceptedCatalogDialog)
    application = QApplication.instance() or QApplication([])
    window = MainWindow(database)
    window.select_catalog_miner()
    application.processEvents()

    assert database.get_miner_by_ticker("VZLA") is not None
    assert window.table.rowCount() == 1
    assert window.table.columnCount() == 1
    assert window.table.item(0, 0).text() == "VZLA: Vizsla Silver"
    assert window.table.verticalHeader().isHidden()
    window.close()
    database.close()


def test_main_window_shows_dashboard_when_a_miner_is_selected(tmp_path: Path) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Vizsla Silver", "VZLA", "Silver", "Developer")
    application = QApplication.instance() or QApplication([])
    window = MainWindow(database)
    window.show()
    application.processEvents()

    assert isinstance(window.detail, MinerDashboard)
    assert window.table.currentRow() == 0
    assert window.width() == 1280
    assert window.height() == 800
    detail_pane = window.splitter.widget(1)
    assert detail_pane is window.detail_scroll
    assert detail_pane.minimumWidth() == 480
    assert window.table.maximumWidth() == 240
    window.close()
    database.close()


def test_miner_dashboard_displays_seeded_vzla_data(tmp_path: Path) -> None:
    database_path = tmp_path / "gosimine.sqlite3"
    seed_path = Path(__file__).parents[1] / "seed" / "miners.json"
    initialize_database(database_path, seed_path)
    database = Database(database_path)
    miner = select_seeded_vzla(database)
    database.add_market_snapshot(
        miner.id,
        4.10,
        "USD",
        "2026-09-12T20:00:00+00:00",
        "2026-09-12T21:00:00+00:00",
        "Yahoo Finance",
    )
    database.add_parameter_snapshot(
        miner.id,
        "basic_shares_outstanding",
        355_056_872,
        "shares",
        "2026-09-12",
        "Yahoo Finance",
    )
    database.add_commodity_price_snapshot(
        "silver",
        64.55,
        "USD",
        "USD/oz",
        "2026-09-12T20:00:00+00:00",
        "2026-09-12T21:00:00+00:00",
        "Yahoo Finance",
    )
    database.add_commodity_price_snapshot(
        "gold",
        4_366.20,
        "USD",
        "USD/oz",
        "2026-09-12T20:00:00+00:00",
        "2026-09-12T21:00:00+00:00",
        "Yahoo Finance",
    )
    database.add_exchange_rate_snapshot(
        "USD", "SEK", 10.45, "2026-09-12T21:00:00+00:00", "Yahoo Finance"
    )

    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)
    dashboard.show()
    application.processEvents()
    text = "\n".join(label.text() for label in dashboard.findChildren(QLabel))

    assert "Vizsla Silver" in text
    assert "VZLA" in text
    assert "Developer / permitting" in text
    assert "Key milestones" in text
    assert "Fully financed (company-reported)" in text
    assert "First silver production" in text
    assert "4.10" in text
    assert "Share price ($)" in text
    assert "AgEq price ($/AgEq oz)" in text
    assert "AISC ($/AgEq oz)" in text
    assert "10.61 $" in text
    assert "58.46 $" in text
    assert "0.0490" in text
    assert "0.4602" in text
    assert "1.0170" in text
    assert "Annual margin / share" in text
    assert "Lifetime margin / SP" in text
    assert "Resource AgEq oz / share" in text
    assert "Resource margin / SP" in text
    assert "NPV / SP" in text
    npv_label = next(
        label
        for label in dashboard.findChildren(QLabel)
        if label.text() == "After-tax NPV / share ($)"
    )
    assert "feasibility-study NPV" in npv_label.toolTip()
    assert "5.08 $" in text
    assert "3.88 $" in text
    assert "5.54 $" in text
    assert "0.95x" in text
    assert "1.35x" in text
    assert "1.24x" in text
    assert [
        label.text()
        for label in dashboard.findChildren(QLabel)
        if label.objectName() == "metric-marker"
    ] == ["‡", "§", "§", "*", "*", "*", "*", "*", "*", "†", "#", "#", "#"]
    assert "* Silver $35.50/oz, Gold $3,100.00/oz; 5% discount rate; FS: https://vizslasilvercorp.com/" in text
    assert "† AISC source: https://vizslasilvercorp.com/" in text
    assert "# Resource screening uses total measured, indicated, and inferred in-situ resources" in text
    assert "‡ AgEq metal prices: Silver 64.55 $/oz, Gold 4,366.20 $/oz." in text
    assert "§ Annual AgEq oz / share sources: production: https://vizslasilvercorp.com/" in text
    assert "As of 2025-11-12." in text
    assert "NAV / share" in text
    assert "Future case" in text
    assert "Future annual margin / share" in text
    tabs = dashboard.findChild(QTabWidget)
    assert tabs is not None
    assert [tabs.tabText(index) for index in range(tabs.count())] == [
        "Overview",
        "Analysis",
        "Research",
        "Model inputs",
    ]
    assert "No research entries yet." in text
    assert any(
        button.text() == "Refresh market data"
        for button in dashboard.findChildren(QPushButton)
    )
    assert any(
        button.text() == "Add research note"
        for button in dashboard.findChildren(QPushButton)
    )
    assert any(
        button.text() == "Add milestone"
        for button in dashboard.findChildren(QPushButton)
    )
    assert any(
        button.text() == "Show model inputs"
        for button in dashboard.findChildren(QPushButton)
    )
    assert any(
        button.text() == "Add model input"
        for button in dashboard.findChildren(QPushButton)
    )
    assert any(
        button.text() == "Update lifecycle status"
        for button in dashboard.findChildren(QPushButton)
    )

    model_inputs_button = next(
        button
        for button in dashboard.findChildren(QPushButton)
        if button.text() == "Show model inputs"
    )
    model_inputs_button.click()
    application.processEvents()
    expanded_text = "\n".join(label.text() for label in dashboard.findChildren(QLabel))
    assert "17,383,000 AgEq oz/year" in expanded_text
    assert "10.61 USD/AgEq oz" in expanded_text
    assert "4.1 USD" in expanded_text
    assert "1 USD = 10.45 SEK" in expanded_text

    dashboard.close()
    database.close()


def test_miner_dashboard_recalculates_a_temporary_metal_price_scenario(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "gosimine.sqlite3"
    seed_path = Path(__file__).parents[1] / "seed" / "miners.json"
    initialize_database(database_path, seed_path)
    database = Database(database_path)
    miner = select_seeded_vzla(database)
    database.add_market_snapshot(
        miner.id, 4.10, "USD", "2026-09-12T20:00:00+00:00", "2026-09-12T21:00:00+00:00", "Yahoo Finance"
    )
    database.add_parameter_snapshot(
        miner.id, "basic_shares_outstanding", 355_056_872, "shares", "2026-09-12", "Yahoo Finance"
    )
    for commodity, price in {"silver": 64.55, "gold": 4_366.20}.items():
        database.add_commodity_price_snapshot(
            commodity, price, "USD", "USD/oz", "2026-09-12T20:00:00+00:00", "2026-09-12T21:00:00+00:00", "Yahoo Finance"
        )
    database.add_exchange_rate_snapshot(
        "USD", "SEK", 10.45, "2026-09-12T21:00:00+00:00", "Yahoo Finance"
    )

    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)
    silver_input = dashboard.findChild(QDoubleSpinBox, "scenario-price-silver")
    gold_input = dashboard.findChild(QDoubleSpinBox, "scenario-price-gold")
    assert silver_input is not None
    assert gold_input is not None
    assert silver_input.decimals() == 0
    assert gold_input.decimals() == 0
    assert silver_input.singleStep() == 10.0
    assert gold_input.singleStep() == 100.0
    silver_input.setValue(70)
    silver_input.editingFinished.emit()
    application.processEvents()

    text = "\n".join(label.text() for label in dashboard.findChildren(QLabel))
    assert "Future case" in text
    assert "Future AgEq price ($/AgEq oz)" in text
    assert "Future resource margin / SP" in text
    assert "61.64 $" in text
    assert "12.66x" in text
    reset_button = dashboard.findChild(QPushButton, "scenario-reset-silver")
    assert reset_button is not None
    reset_button.click()
    application.processEvents()
    assert dashboard.scenario_prices["silver"] == 64.55
    assert database.get_latest_commodity_price("silver").price == 64.55
    dashboard.close()
    database.close()


def test_usd_listing_does_not_require_an_fx_rate(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "gosimine.sqlite3"
    seed_path = Path(__file__).parents[1] / "seed" / "miners.json"
    initialize_database(database_path, seed_path)
    database = Database(database_path)
    miner = select_seeded_vzla(database)
    database.add_market_snapshot(
        miner.id, 4.10, "USD", "2026-09-12T20:00:00+00:00", "2026-09-12T21:00:00+00:00", "Yahoo Finance"
    )
    database.add_parameter_snapshot(
        miner.id, "basic_shares_outstanding", 355_056_872, "shares", "2026-09-12", "Yahoo Finance"
    )
    for commodity, price in {"silver": 64.55, "gold": 4_366.20}.items():
        database.add_commodity_price_snapshot(
            commodity, price, "USD", "USD/oz", "2026-09-12T20:00:00+00:00", "2026-09-12T21:00:00+00:00", "Yahoo Finance"
        )

    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)
    text = "\n".join(label.text() for label in dashboard.findChildren(QLabel))

    assert "Currency conversion unavailable" not in text
    assert "Future case" in text
    dashboard.close()
    database.close()


def test_miner_dashboard_converts_per_share_values_to_trading_currency(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Vizsla Silver", "VZLA.TO", "Silver", "Developer", "CAD")
    database.add_market_snapshot(
        miner.id, 5.00, "CAD", "2026-09-12T20:00:00+00:00", "2026-09-12T21:00:00+00:00", "Yahoo Finance"
    )
    for parameter, value in {
        "annual_payable_silver_ounces": 10_130_000,
        "annual_payable_gold_ounces": 83_000,
        "annual_production_ounces": 17_383_000,
        "aisc_per_ounce": 10.61,
        "mine_life_years": 9.4,
        "basic_shares_outstanding": 355_056_872,
    }.items():
        database.add_parameter_snapshot(
            miner.id, parameter, value, "test", "2026-09-12", "Test"
        )
    for commodity, price in {"silver": 64.55, "gold": 4_366.20}.items():
        database.add_commodity_price_snapshot(
            commodity, price, "USD", "USD/oz", "2026-09-12T20:00:00+00:00", "2026-09-12T21:00:00+00:00", "Test"
        )
    database.add_exchange_rate_snapshot("USD", "CAD", 1.36, "2026-09-12T21:00:00+00:00", "Test")

    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)
    application.processEvents()
    text = "\n".join(label.text() for label in dashboard.findChildren(QLabel))

    assert "5.00" in text
    assert "Share price (C$)" in text
    assert "3.19" in text
    assert "Annual margin / share (C$)" in text
    dashboard.close()
    database.close()


def test_miner_dashboard_refresh_button_updates_market_data(
    tmp_path: Path, monkeypatch
) -> None:
    database_path = tmp_path / "gosimine.sqlite3"
    seed_path = Path(__file__).parents[1] / "seed" / "miners.json"
    initialize_database(database_path, seed_path)
    database = Database(database_path)
    miner = select_seeded_vzla(database)

    def fake_refresh(database: Database, miner) -> None:
        database.add_market_snapshot(
            miner.id,
            4.10,
            "USD",
            "2026-09-12T20:00:00+00:00",
            "2026-09-12T21:00:00+00:00",
            "Yahoo Finance",
        )

    monkeypatch.setattr("gosimine.app.refresh_market_data", fake_refresh)
    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)
    refresh_button = next(
        button
        for button in dashboard.findChildren(QPushButton)
        if button.text() == "Refresh market data"
    )

    refresh_button.click()
    application.processEvents()

    text = "\n".join(label.text() for label in dashboard.findChildren(QLabel))
    assert "Analysis unavailable" in text
    model_inputs_button = next(
        button
        for button in dashboard.findChildren(QPushButton)
        if button.text() == "Show model inputs"
    )
    model_inputs_button.click()
    application.processEvents()
    expanded_text = "\n".join(label.text() for label in dashboard.findChildren(QLabel))
    assert "4.1 USD" in expanded_text
    dashboard.close()
    database.close()


def test_miner_dashboard_adds_research_note(tmp_path: Path, monkeypatch) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Vizsla Silver", "VZLA", "Silver", "Developer")

    class AcceptedResearchDialog:
        def __init__(self, parent) -> None:
            pass

        def exec(self) -> QDialog.DialogCode:
            return QDialog.DialogCode.Accepted

        def values(self) -> tuple[str, str, str, str, str, str]:
            return (
                "2026-09-12",
                "Reviewed the feasibility study.",
                "https://example.com/vzla-fs",
                "No change.",
                "Permit decision.",
                "When is construction expected to start?",
            )

    monkeypatch.setattr("gosimine.app.AddResearchEntryDialog", AcceptedResearchDialog)
    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)

    dashboard.add_research_note()
    application.processEvents()

    entries = database.list_research_entries(miner.id)
    assert len(entries) == 1
    assert entries[0].note == "Reviewed the feasibility study."
    text = "\n".join(label.text() for label in dashboard.findChildren(QLabel))
    assert "2026-09-12: Reviewed the feasibility study." in text
    dashboard.close()
    database.close()


def test_miner_dashboard_adds_milestone(tmp_path: Path, monkeypatch) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Vizsla Silver", "VZLA", "Silver", "Developer")

    class AcceptedMilestoneDialog:
        def __init__(self, parent) -> None:
            pass

        def exec(self) -> QDialog.DialogCode:
            return QDialog.DialogCode.Accepted

        def values(self) -> tuple[str, str, str, str, str, str]:
            return (
                "Permitting",
                "MIA permit decision",
                "2026-H2",
                "Planned",
                "Awaiting regulatory approval.",
                "Manual",
            )

    monkeypatch.setattr("gosimine.app.AddMilestoneDialog", AcceptedMilestoneDialog)
    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)

    dashboard.add_milestone()
    application.processEvents()

    milestones = database.list_milestones(miner.id)
    assert len(milestones) == 1
    assert milestones[0].title == "MIA permit decision"
    text = "\n".join(label.text() for label in dashboard.findChildren(QLabel))
    assert "Awaiting regulatory approval." in text
    dashboard.close()
    database.close()


def test_miner_dashboard_records_milestone_outcome(tmp_path: Path, monkeypatch) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Vizsla Silver", "VZLA", "Silver", "Developer")

    class AcceptedMilestoneOutcomeDialog:
        def __init__(self, category, title, parent) -> None:
            assert (category, title) == ("Permitting", "MIA permit decision")

        def exec(self) -> QDialog.DialogCode:
            return QDialog.DialogCode.Accepted

        def values(self) -> tuple[str, str, str, str, str, str]:
            return (
                "Permitting",
                "MIA permit decision",
                "2026-09-12",
                "Completed",
                "Actual outcome: Permit received.\nThesis impact: De-risks construction.",
                "Company release",
            )

    monkeypatch.setattr("gosimine.app.UpdateMilestoneDialog", AcceptedMilestoneOutcomeDialog)
    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)
    dashboard.update_milestone("Permitting", "MIA permit decision")
    application.processEvents()

    milestone = database.list_milestones(miner.id)[0]
    assert milestone.status == "Completed"
    assert "Thesis impact: De-risks construction." in milestone.detail
    dashboard.close()
    database.close()


def test_history_dialog_displays_prior_dossier_entries(tmp_path: Path) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Vizsla Silver", "VZLA", "Silver", "Developer")
    database.add_parameter_snapshot(
        miner.id, "aisc_per_ounce", 11.0, "USD/AgEq oz", "2026-09-01", "Study"
    )
    database.add_lifecycle_status_snapshot(
        miner.id, "Developer / permitting", "2026-09-01", "Company release"
    )
    database.add_research_entry(
        miner.id, "2026-09-01", "Permit review underway.", "Company release", "", "", ""
    )
    application = QApplication.instance() or QApplication([])
    dialog = HistoryDialog(database, miner)
    application.processEvents()

    text = "\n".join(
        table.item(row, column).text()
        for table in dialog.findChildren(QTableWidget)
        for row in range(table.rowCount())
        for column in range(table.columnCount())
        if table.item(row, column) is not None
    )
    assert "aisc_per_ounce" in text
    assert "Developer / permitting" in text
    assert "Permit review underway." in text
    dialog.close()
    database.close()


def test_miner_dashboard_adds_a_model_input(tmp_path: Path, monkeypatch) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Vizsla Silver", "VZLA", "Silver", "Developer")

    class AcceptedModelInputDialog:
        def __init__(self, parent) -> None:
            pass

        def exec(self) -> QDialog.DialogCode:
            return QDialog.DialogCode.Accepted

        def values(self) -> tuple[str, float, str, str, str]:
            return ("mine_life_years", 10.0, "years", "2026-09-12", "Manual")

    monkeypatch.setattr("gosimine.app.AddModelInputDialog", AcceptedModelInputDialog)
    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)

    dashboard.add_model_input()
    application.processEvents()

    parameters = database.list_current_parameters(miner.id)
    assert len(parameters) == 1
    assert parameters[0].parameter == "mine_life_years"
    assert parameters[0].value == 10.0
    dashboard.close()
    database.close()


def test_miner_dashboard_updates_lifecycle_status(tmp_path: Path, monkeypatch) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Vizsla Silver", "VZLA", "Silver", "Developer")
    database.add_lifecycle_status_snapshot(
        miner.id, "Developer / permitting", "2026-09-01", "Company release"
    )

    class AcceptedLifecycleStatusDialog:
        def __init__(self, current_status, parent) -> None:
            assert current_status == "Developer / permitting"

        def exec(self) -> QDialog.DialogCode:
            return QDialog.DialogCode.Accepted

        def values(self) -> tuple[str, str, str]:
            return ("Construction", "2026-09-12", "Company release")

    monkeypatch.setattr(
        "gosimine.app.UpdateLifecycleStatusDialog", AcceptedLifecycleStatusDialog
    )
    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)

    dashboard.update_lifecycle_status("Developer / permitting")
    application.processEvents()

    statuses = database.list_lifecycle_status_history(miner.id)
    assert statuses[0].status == "Construction"
    text = "\n".join(label.text() for label in dashboard.findChildren(QLabel))
    assert "Construction\nAs of 2026-09-12" in text
    dashboard.close()
    database.close()


def test_miner_dashboard_saves_and_loads_a_scenario(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "gosimine.sqlite3"
    seed_path = Path(__file__).parents[1] / "seed" / "miners.json"
    initialize_database(database_path, seed_path)
    database = Database(database_path)
    miner = select_seeded_vzla(database)
    database.add_market_snapshot(
        miner.id, 4.10, "USD", "2026-09-12T20:00:00+00:00", "2026-09-12T21:00:00+00:00", "Test"
    )
    database.add_parameter_snapshot(
        miner.id, "basic_shares_outstanding", 355_056_872, "shares", "2026-09-12", "Test"
    )
    for commodity, price in {"silver": 64.55, "gold": 4_366.20}.items():
        database.add_commodity_price_snapshot(
            commodity, price, "USD", "USD/oz", "2026-09-12T20:00:00+00:00", "2026-09-12T21:00:00+00:00", "Test"
        )

    class AcceptedSaveScenarioDialog:
        def __init__(self, parent) -> None:
            pass

        def exec(self) -> QDialog.DialogCode:
            return QDialog.DialogCode.Accepted

        def value(self) -> str:
            return "Higher silver"

    monkeypatch.setattr("gosimine.app.SaveScenarioDialog", AcceptedSaveScenarioDialog)
    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)
    dashboard.set_scenario_price("silver", 70)
    dashboard.set_development_risk_factor(0.8)
    dashboard.save_analysis_scenario()
    application.processEvents()

    scenario = database.list_analysis_scenarios(miner.id)[0]
    assert scenario.name == "Higher silver"
    assert scenario.metal_prices_usd["silver"] == 70
    assert scenario.development_risk_factor == 0.8
    dashboard.set_scenario_price("silver", 60)
    dashboard.load_analysis_scenario(scenario.id)
    assert dashboard.scenario_prices["silver"] == 70
    assert dashboard.development_risk_factor == 0.8
    dashboard.close()
    database.close()


def test_settings_dialog_persists_the_base_currency(tmp_path: Path) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    application = QApplication.instance() or QApplication([])
    dialog = SettingsDialog(database)

    currency_input = dialog.findChild(QComboBox)
    assert currency_input is not None
    assert currency_input.currentText() == "SEK"
    currency_input.setCurrentText("USD")
    dialog.accept()
    application.processEvents()

    setting = database.get_current_application_setting("base_currency")
    assert setting is not None
    assert setting.value == "USD"
    dialog.close()
    database.close()